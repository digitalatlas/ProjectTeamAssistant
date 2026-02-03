# -*- coding: utf-8 -*-
"""
Сервис полного пайплайна обработки задач.
Выполняет: загрузку данных из CSV -> декомпозицию -> оценку выполнения -> создание дашборда.
"""

import os
import json
import subprocess
import webbrowser
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.utils.data.jira_csv_loader import JiraCsvLoader, JiraTask, CompletionEvaluation, StepEvaluation
from app.services.llm.llm_wrapper import LLMService
from app.services.completion.completion_service import CompletionService, ProjectCompletionReport
from app.services.dashboard.dashboard_service import DashboardService
from app.config.settings import settings


@dataclass
class PipelineResult:
    """Результат выполнения пайплайна."""
    success: bool
    tasks: List[JiraTask] = field(default_factory=list)
    project_report: Optional[ProjectCompletionReport] = None
    dashboard_data: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Статистика по этапам
    tasks_loaded: int = 0
    tasks_decomposed: int = 0
    tasks_with_plan: int = 0
    tasks_evaluated: int = 0


class PipelineService:
    """
    Сервис для выполнения полного пайплайна обработки задач.
    
    Пайплайн включает:
    1. Загрузка данных из CSV файла
    2. Декомпозиция задач с помощью LLM
    3. Генерация планов реализации
    4. Оценка процента выполнения
    5. Формирование данных для дашборда
    6. Запуск интерактивного дашборда (опционально)
    """
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        completion_service: Optional[CompletionService] = None,
        dashboard_service: Optional[DashboardService] = None
    ):
        """
        Инициализация сервиса пайплайна.
        
        :param llm_service: Сервис для работы с LLM (создаётся автоматически, если не передан).
        :param completion_service: Сервис для анализа выполнения.
        :param dashboard_service: Сервис для формирования дашборда.
        """
        self.llm_service = llm_service
        self.completion_service = completion_service or CompletionService()
        self.dashboard_service = dashboard_service or DashboardService()
        
        # Флаг ленивой инициализации LLM сервиса
        self._llm_initialized = llm_service is not None
    
    def _ensure_llm_service(self) -> LLMService:
        """Ленивая инициализация LLM сервиса."""
        if not self._llm_initialized:
            print("Инициализация LLM сервиса...")
            self.llm_service = LLMService()
            self._llm_initialized = True
        return self.llm_service
    
    def load_tasks_from_csv(self, csv_path: str) -> List[JiraTask]:
        """
        Загружает задачи из CSV файла.
        
        :param csv_path: Путь к CSV файлу.
        :return: Список загруженных задач.
        """
        print(f"\n{'='*60}")
        print("ЭТАП 1: Загрузка данных из CSV")
        print(f"{'='*60}")
        print(f"Файл: {csv_path}")
        
        loader = JiraCsvLoader(csv_path)
        tasks = loader.load_tasks()
        
        print(f"Загружено задач: {len(tasks)}")
        return tasks
    
    def load_tasks_from_json(self, json_path: str) -> List[JiraTask]:
        """
        Загружает задачи из JSON файла (результат предыдущего запуска пайплайна).
        
        :param json_path: Путь к JSON файлу.
        :return: Список загруженных задач с оценками выполнения.
        """
        print(f"\n{'='*60}")
        print("ЗАГРУЗКА ДАННЫХ ИЗ JSON")
        print(f"{'='*60}")
        print(f"Файл: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tasks = []
        for task_data in data:
            # Создаём объект JiraTask
            task = JiraTask(
                issue_key=task_data.get('issue_key', ''),
                issue_id=task_data.get('issue_id', 0),
                summary=task_data.get('summary', ''),
                status=task_data.get('status', ''),
                created=task_data.get('created', ''),
                updated=task_data.get('updated', ''),
                description=task_data.get('description'),
                assignee=task_data.get('assignee'),
                components=task_data.get('components', []),
                due_date=task_data.get('due_date'),
                decomposition=task_data.get('decomposition'),
                implementation_plan=task_data.get('implementation_plan')
            )
            
            # Восстанавливаем оценку выполнения, если есть
            if 'completion_evaluation' in task_data and task_data['completion_evaluation']:
                eval_data = task_data['completion_evaluation']
                steps = []
                for step_data in eval_data.get('steps_evaluation', []):
                    step = StepEvaluation(
                        step_number=step_data.get('step_number', 0),
                        step_description=step_data.get('step_description', ''),
                        is_completed=step_data.get('is_completed', False),
                        completion_percentage=float(step_data.get('completion_percentage', 0)),
                        weight=float(step_data.get('weight', 0)),
                        reasoning=step_data.get('reasoning', '')
                    )
                    steps.append(step)
                
                task.completion_evaluation = CompletionEvaluation(
                    overall_completion_percentage=float(eval_data.get('overall_completion_percentage', 0)),
                    status_factor=eval_data.get('status_factor', ''),
                    steps_evaluation=steps,
                    confidence=eval_data.get('confidence', 'medium'),
                    notes=eval_data.get('notes')
                )
            
            tasks.append(task)
        
        print(f"Загружено задач: {len(tasks)}")
        tasks_with_eval = sum(1 for t in tasks if t.completion_evaluation)
        print(f"Задач с оценкой выполнения: {tasks_with_eval}")
        
        return tasks
    
    def decompose_tasks(
        self,
        tasks: List[JiraTask],
        rules_path: Optional[str] = None,
        prompt_path: Optional[str] = None
    ) -> List[JiraTask]:
        """
        Выполняет декомпозицию задач.
        
        :param tasks: Список задач для декомпозиции.
        :param rules_path: Путь к файлу с правилами.
        :param prompt_path: Путь к файлу с промптом.
        :return: Список задач с заполненной декомпозицией.
        """
        print(f"\n{'='*60}")
        print("ЭТАП 2: Декомпозиция задач")
        print(f"{'='*60}")
        
        llm = self._ensure_llm_service()
        
        rules = rules_path or settings.RULES_FILEPATH
        prompt = prompt_path or settings.DECOMPOSITION_PROMPT_FILEPATH
        
        decomposition_result = llm.decompose_tasks(
            tasks=tasks,
            rules_path=str(rules),
            prompt_path=str(prompt)
        )
        
        # Применяем результаты к задачам
        for task in tasks:
            if task.issue_key in decomposition_result:
                task.decomposition = decomposition_result[task.issue_key]
        
        decomposed_count = sum(1 for t in tasks if t.decomposition)
        print(f"Задач с декомпозицией: {decomposed_count}/{len(tasks)}")
        
        return tasks
    
    def generate_implementation_plans(
        self,
        tasks: List[JiraTask],
        rules_path: Optional[str] = None
    ) -> List[JiraTask]:
        """
        Генерирует планы реализации для задач.
        
        :param tasks: Список задач с декомпозицией.
        :param rules_path: Путь к файлу с правилами.
        :return: Список задач с планами реализации.
        """
        print(f"\n{'='*60}")
        print("ЭТАП 3: Генерация планов реализации")
        print(f"{'='*60}")
        
        llm = self._ensure_llm_service()
        rules = rules_path or settings.RULES_FILEPATH
        
        plans_result = llm.generate_implementation_plans(
            tasks=tasks,
            rules_path=str(rules)
        )
        
        # Применяем планы к задачам
        for task in tasks:
            if task.issue_key in plans_result:
                task.implementation_plan = plans_result[task.issue_key]
        
        plans_count = sum(1 for t in tasks if t.implementation_plan)
        print(f"Задач с планом реализации: {plans_count}/{len(tasks)}")
        
        return tasks
    
    def evaluate_completion(
        self,
        tasks: List[JiraTask],
        rules_path: Optional[str] = None,
        batch_size: int = 5
    ) -> List[JiraTask]:
        """
        Оценивает процент выполнения задач.
        
        :param tasks: Список задач с планами реализации.
        :param rules_path: Путь к файлу с правилами.
        :param batch_size: Размер батча для обработки.
        :return: Список задач с оценками выполнения.
        """
        print(f"\n{'='*60}")
        print("ЭТАП 4: Оценка процента выполнения")
        print(f"{'='*60}")
        
        llm = self._ensure_llm_service()
        rules = rules_path or settings.RULES_FILEPATH
        
        completion_result = llm.evaluate_task_completion(
            tasks=tasks,
            rules_path=str(rules),
            batch_size=batch_size
        )
        
        # Применяем оценки к задачам
        for task in tasks:
            if task.issue_key in completion_result:
                task.completion_evaluation = completion_result[task.issue_key]
        
        evaluated_count = sum(1 for t in tasks if t.completion_evaluation)
        print(f"Задач с оценкой выполнения: {evaluated_count}/{len(tasks)}")
        
        return tasks
    
    def generate_dashboard_data(self, tasks: List[JiraTask]) -> Dict[str, Any]:
        """
        Формирует данные для дашборда.
        
        :param tasks: Список задач с оценками выполнения.
        :return: Словарь с данными для дашборда.
        """
        print(f"\n{'='*60}")
        print("ЭТАП 5: Формирование данных для дашборда")
        print(f"{'='*60}")
        
        # Получаем данные для таблицы
        table_data = self.dashboard_service.to_flat_table_data(tasks)
        
        # Получаем статистику
        stats = self.dashboard_service.get_summary_stats(tasks)
        
        # Генерируем отчёт о проекте
        project_report = self.completion_service.generate_project_report(tasks)
        
        print(f"Сформировано строк для таблицы: {len(table_data)}")
        print(f"Средний процент выполнения: {stats['avg_completion']}%")
        
        return {
            "table_data": table_data,
            "stats": stats,
            "project_report": project_report
        }
    
    def save_results_to_json(
        self,
        tasks: List[JiraTask],
        output_path: str
    ) -> str:
        """
        Сохраняет результаты пайплайна в JSON файл.
        
        :param tasks: Список обработанных задач.
        :param output_path: Путь для сохранения файла.
        :return: Путь к сохранённому файлу.
        """
        print(f"\nСохранение результатов в: {output_path}")
        
        results = []
        for task in tasks:
            task_data = {
                "issue_key": task.issue_key,
                "summary": task.summary,
                "status": task.status,
                "assignee": task.assignee,
                "components": task.components,
                "decomposition": task.decomposition,
                "implementation_plan": task.implementation_plan,
            }
            
            if task.completion_evaluation:
                eval_data = task.completion_evaluation
                task_data["completion_evaluation"] = {
                    "overall_completion_percentage": eval_data.overall_completion_percentage,
                    "status_factor": eval_data.status_factor,
                    "confidence": eval_data.confidence,
                    "notes": eval_data.notes,
                    "steps_evaluation": [
                        {
                            "step_number": step.step_number,
                            "step_description": step.step_description,
                            "is_completed": step.is_completed,
                            "completion_percentage": step.completion_percentage,
                            "weight": step.weight,
                            "reasoning": step.reasoning
                        }
                        for step in eval_data.steps_evaluation
                    ]
                }
            
            results.append(task_data)
        
        # Создаём директорию, если не существует
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"Результаты сохранены: {len(results)} задач")
        return output_path
    
    def launch_dashboard(self, port: int = 8501) -> None:
        """
        Запускает интерактивный дашборд Streamlit.
        
        :param port: Порт для запуска дашборда.
        """
        print(f"\n{'='*60}")
        print("ЭТАП 6: Запуск интерактивного дашборда")
        print(f"{'='*60}")
        
        dashboard_path = Path(__file__).parent.parent.parent / "dashboard_app.py"
        
        print(f"Запуск дашборда на порту {port}...")
        print(f"Откройте в браузере: http://localhost:{port}")
        
        # Открываем браузер
        webbrowser.open(f"http://localhost:{port}")
        
        # Запускаем Streamlit
        subprocess.run([
            "streamlit", "run",
            str(dashboard_path),
            "--server.port", str(port),
            "--server.headless", "true"
        ])
    
    def run_full_pipeline(
        self,
        csv_path: str,
        output_json_path: Optional[str] = None,
        launch_dashboard: bool = False,
        dashboard_port: int = 8501,
        rules_path: Optional[str] = None,
        prompt_path: Optional[str] = None,
        completion_batch_size: int = 5
    ) -> PipelineResult:
        """
        Выполняет полный пайплайн обработки задач.
        
        :param csv_path: Путь к CSV файлу с задачами.
        :param output_json_path: Путь для сохранения результатов в JSON (опционально).
        :param launch_dashboard: Запустить ли дашборд после обработки.
        :param dashboard_port: Порт для дашборда.
        :param rules_path: Путь к файлу с правилами.
        :param prompt_path: Путь к файлу с промптом декомпозиции.
        :param completion_batch_size: Размер батча для оценки выполнения.
        :return: Результат выполнения пайплайна.
        """
        start_time = datetime.now()
        result = PipelineResult(success=False)
        
        print("\n" + "="*60)
        print("ЗАПУСК ПОЛНОГО ПАЙПЛАЙНА ОБРАБОТКИ ЗАДАЧ")
        print("="*60)
        print(f"Время начала: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"CSV файл: {csv_path}")
        
        try:
            # Этап 1: Загрузка данных
            tasks = self.load_tasks_from_csv(csv_path)
            result.tasks_loaded = len(tasks)
            
            if not tasks:
                result.errors.append("Не удалось загрузить задачи из CSV файла")
                return result
            
            # Этап 2: Декомпозиция
            tasks = self.decompose_tasks(tasks, rules_path, prompt_path)
            result.tasks_decomposed = sum(1 for t in tasks if t.decomposition)
            
            # Этап 3: Генерация планов
            tasks = self.generate_implementation_plans(tasks, rules_path)
            result.tasks_with_plan = sum(1 for t in tasks if t.implementation_plan)
            
            # Этап 4: Оценка выполнения
            tasks = self.evaluate_completion(tasks, rules_path, completion_batch_size)
            result.tasks_evaluated = sum(1 for t in tasks if t.completion_evaluation)
            
            # Этап 5: Формирование данных для дашборда
            dashboard_data = self.generate_dashboard_data(tasks)
            result.dashboard_data = dashboard_data["table_data"]
            result.project_report = dashboard_data["project_report"]
            
            # Сохранение результатов
            if output_json_path:
                self.save_results_to_json(tasks, output_json_path)
            
            result.tasks = tasks
            result.success = True
            
            # Вывод итогов
            end_time = datetime.now()
            result.execution_time_seconds = (end_time - start_time).total_seconds()
            
            self._print_summary(result)
            
            # Этап 6: Запуск дашборда (опционально)
            if launch_dashboard:
                self.launch_dashboard(dashboard_port)
            
        except FileNotFoundError as e:
            result.errors.append(f"Файл не найден: {e}")
            print(f"\n❌ Ошибка: {e}")
        except ValueError as e:
            result.errors.append(f"Ошибка валидации: {e}")
            print(f"\n❌ Ошибка: {e}")
        except Exception as e:
            result.errors.append(f"Непредвиденная ошибка: {e}")
            print(f"\n❌ Непредвиденная ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def _print_summary(self, result: PipelineResult) -> None:
        """Выводит итоговую сводку выполнения пайплайна."""
        print("\n" + "="*60)
        print("ИТОГИ ВЫПОЛНЕНИЯ ПАЙПЛАЙНА")
        print("="*60)
        print(f"✅ Статус: {'Успешно' if result.success else 'С ошибками'}")
        print(f"⏱️  Время выполнения: {result.execution_time_seconds:.2f} сек")
        print()
        print("📊 Статистика по этапам:")
        print(f"   • Загружено задач: {result.tasks_loaded}")
        print(f"   • Декомпозировано: {result.tasks_decomposed}")
        print(f"   • С планом реализации: {result.tasks_with_plan}")
        print(f"   • С оценкой выполнения: {result.tasks_evaluated}")
        
        if result.project_report:
            report = result.project_report
            print()
            print("📈 Сводка по проекту:")
            print(f"   • Средний % выполнения: {report.average_completion}%")
            print(f"   • Медианный % выполнения: {report.median_completion}%")
            print(f"   • Завершённых задач: {len(report.completed_tasks)}")
            print(f"   • Задач с высоким риском: {len(report.high_risk_tasks)}")
        
        if result.errors:
            print()
            print("❌ Ошибки:")
            for error in result.errors:
                print(f"   • {error}")
        
        if result.warnings:
            print()
            print("⚠️  Предупреждения:")
            for warning in result.warnings:
                print(f"   • {warning}")
        
        print("="*60)
    
    def run_quick_analysis(
        self,
        csv_path: str,
        output_json_path: Optional[str] = None
    ) -> PipelineResult:
        """
        Выполняет быстрый анализ без запуска дашборда.
        Удобный метод для скриптов и автоматизации.
        
        :param csv_path: Путь к CSV файлу.
        :param output_json_path: Путь для сохранения результатов.
        :return: Результат выполнения.
        """
        return self.run_full_pipeline(
            csv_path=csv_path,
            output_json_path=output_json_path,
            launch_dashboard=False
        )
    
    def run_with_dashboard(
        self,
        csv_path: str,
        port: int = 8501
    ) -> PipelineResult:
        """
        Выполняет полный анализ и запускает дашборд.
        
        :param csv_path: Путь к CSV файлу.
        :param port: Порт для дашборда.
        :return: Результат выполнения.
        """
        return self.run_full_pipeline(
            csv_path=csv_path,
            launch_dashboard=True,
            dashboard_port=port
        )
    
    def run_dashboard_from_json(
        self,
        json_path: str,
        port: int = 8501
    ) -> PipelineResult:
        """
        Загружает данные из JSON и запускает дашборд.
        Не выполняет LLM-обработку, использует сохранённые результаты.
        
        :param json_path: Путь к JSON файлу с результатами пайплайна.
        :param port: Порт для дашборда.
        :return: Результат выполнения.
        """
        start_time = datetime.now()
        result = PipelineResult(success=False)
        
        print("\n" + "="*60)
        print("ЗАПУСК ДАШБОРДА ИЗ СОХРАНЁННЫХ ДАННЫХ")
        print("="*60)
        print(f"Время начала: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"JSON файл: {json_path}")
        
        try:
            # Загружаем задачи из JSON
            tasks = self.load_tasks_from_json(json_path)
            result.tasks_loaded = len(tasks)
            result.tasks_evaluated = sum(1 for t in tasks if t.completion_evaluation)
            
            if not tasks:
                result.errors.append("Не удалось загрузить задачи из JSON файла")
                return result
            
            # Формируем данные для дашборда
            dashboard_data = self.generate_dashboard_data(tasks)
            result.dashboard_data = dashboard_data["table_data"]
            result.project_report = dashboard_data["project_report"]
            
            result.tasks = tasks
            result.success = True
            
            # Вывод итогов
            end_time = datetime.now()
            result.execution_time_seconds = (end_time - start_time).total_seconds()
            
            self._print_summary(result)
            
            # Запускаем дашборд с передачей пути к JSON
            self._launch_dashboard_with_json(json_path, port)
            
        except FileNotFoundError as e:
            result.errors.append(f"Файл не найден: {e}")
            print(f"\n❌ Ошибка: {e}")
        except json.JSONDecodeError as e:
            result.errors.append(f"Ошибка парсинга JSON: {e}")
            print(f"\n❌ Ошибка: {e}")
        except Exception as e:
            result.errors.append(f"Непредвиденная ошибка: {e}")
            print(f"\n❌ Непредвиденная ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def _launch_dashboard_with_json(self, json_path: str, port: int = 8501) -> None:
        """
        Запускает дашборд с указанием JSON файла для загрузки данных.
        
        :param json_path: Путь к JSON файлу.
        :param port: Порт для дашборда.
        """
        print(f"\n{'='*60}")
        print("ЗАПУСК ИНТЕРАКТИВНОГО ДАШБОРДА")
        print(f"{'='*60}")
        
        dashboard_path = Path(__file__).parent.parent.parent / "dashboard_app.py"
        
        # Преобразуем путь в абсолютный
        abs_json_path = os.path.abspath(json_path)
        
        print(f"Запуск дашборда на порту {port}...")
        print(f"Данные из: {abs_json_path}")
        print(f"Откройте в браузере: http://localhost:{port}")
        
        # Открываем браузер
        webbrowser.open(f"http://localhost:{port}")
        
        # Запускаем Streamlit с переменной окружения для JSON пути
        env = os.environ.copy()
        env["PIPELINE_JSON_PATH"] = abs_json_path
        
        subprocess.run(
            [
                "streamlit", "run",
                str(dashboard_path),
                "--server.port", str(port),
                "--server.headless", "true"
            ],
            env=env
        )


# --- Пример использования ---
if __name__ == "__main__":
    # Создаём сервис пайплайна
    pipeline = PipelineService()
    
    # Запускаем полный пайплайн
    result = pipeline.run_full_pipeline(
        csv_path="data/jira_tasks/tasks.csv",
        output_json_path="data/output/pipeline_results.json",
        launch_dashboard=False
    )
    
    if result.success:
        print("\n✅ Пайплайн успешно завершён!")
        print(f"Обработано задач: {len(result.tasks)}")
    else:
        print("\n❌ Пайплайн завершился с ошибками")
        for error in result.errors:
            print(f"  - {error}")
