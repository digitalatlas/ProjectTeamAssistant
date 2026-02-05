"""
Тестовый скрипт для проверки полного цикла:
1. Загрузка задач из CSV
2. Декомпозиция задач
3. Генерация плана реализации
4. Оценка процента выполнения
5. Генерация отчётов
"""

from typing import List

from app.utils.data.jira_csv_loader import JiraCsvLoader, JiraTask
from app.services.llm.llm_wrapper import LLMService
from app.services.completion.completion_service import CompletionService

from app.utils.db.db_manager import VectorDBManager

import pandas as pd


def print_separator(title: str = ""):
    """Печатает разделитель с заголовком."""
    print("\n" + "=" * 60)
    if title:
        print(title)
        print("=" * 60)


def print_task_details(task: JiraTask):
    """Выводит детальную информацию о задаче."""
    print_separator(f"ЗАДАЧА: {task.issue_key}")
    print(f"Заголовок: {task.summary}")
    print(f"Статус: {task.status}")
    print(f"Исполнитель: {task.assignee if task.assignee else 'Не назначен'}")
    print(f"\nОписание: {task.description}")
    
    print(f"\nШаги декомпозиции:")
    if task.decomposition:
        for step in task.decomposition:
            print(f"  - {step}")
    else:
        print("  (не определены)")
    
    print(f"\nПлан реализации:")
    if task.implementation_plan:
        for i, step in enumerate(task.implementation_plan, 1):
            print(f"  {i}. {step}")
    else:
        print("  (не сгенерирован)")
    
    # Выводим оценку выполнения
    if task.completion_evaluation:
        eval_data = task.completion_evaluation
        print(f"\n--- Оценка выполнения ---")
        print(f"Общий процент выполнения: {eval_data.overall_completion_percentage:.1f}%")
        print(f"Уверенность оценки: {eval_data.confidence}")
        print(f"Фактор статуса: {eval_data.status_factor}")
        
        if eval_data.steps_evaluation:
            print(f"\nОценка по шагам:")
            for step in eval_data.steps_evaluation:
                status = "✓" if step.is_completed else "○"
                print(f"  {status} Шаг {step.step_number}: {step.completion_percentage}% "
                      f"(вес: {step.weight}%) - {step.step_description[:50]}...")
                print(f"      Обоснование: {step.reasoning}")
        
        if eval_data.notes:
            print(f"\nЗаметки: {eval_data.notes}")
    else:
        print(f"\n--- Оценка выполнения ---")
        print("  (не выполнена)")


def main():
    """Основная функция тестирования."""
    
    # ========================================
    # ЭТАП 1: Загрузка задач из CSV
    # ========================================
    print_separator("ЭТАП 1: ЗАГРУЗКА ЗАДАЧ")
    
    csv_loader = JiraCsvLoader('data/jira_tasks/Jira 2026-02-02T18_16_40+0300.csv')
    tasks: List[JiraTask] = csv_loader.load_tasks()
    
    if not tasks:
        print("Не удалось загрузить задачи. Проверьте путь к файлу.")
        return
    
    print(f"Загружено задач: {len(tasks)}")
    
    # ========================================
    # ЭТАП 2-4: Полный анализ с LLM
    # ========================================
    print_separator("ЭТАП 2-4: ПОЛНЫЙ АНАЛИЗ (ДЕКОМПОЗИЦИЯ + ПЛАН + ОЦЕНКА)")
    
    llm = LLMService()
    
    # Используем новый метод для полного цикла: декомпозиция + план + оценка выполнения
    tasks = llm.full_analysis_with_completion(tasks)
    
    # ========================================
    # ЭТАП 5: Вывод результатов
    # ========================================
    print_separator("ЭТАП 5: РЕЗУЛЬТАТЫ АНАЛИЗА")
    
    # Выводим детали для каждой задачи
    for task in tasks:
        print_task_details(task)
    
    # ========================================
    # ЭТАП 6: Генерация отчётов
    # ========================================
    print_separator("ЭТАП 6: СВОДНЫЕ ОТЧЁТЫ")
    
    completion_service = CompletionService()
    
    # Генерируем сводный отчёт по проекту
    project_report = completion_service.generate_project_report(tasks)
    print(completion_service.format_report_as_text(project_report))
    
    # Выводим приоритетные задачи
    print("\n--- Приоритетные задачи (требуют внимания) ---")
    priority_tasks = completion_service.get_priority_tasks(tasks, limit=5)
    if priority_tasks:
        for issue_key, completion, bottlenecks in priority_tasks:
            print(f"\n  {issue_key}: {completion:.1f}% выполнено")
            if bottlenecks:
                print(f"    Блокирующие шаги:")
                for bottleneck in bottlenecks[:2]:  # Показываем первые 2
                    print(f"      - {bottleneck}")
    else:
        print("  Нет задач с оценкой выполнения")
    
    # Оценка оставшейся работы
    print("\n--- Оценка оставшейся работы ---")
    for task in tasks:
        effort = completion_service.estimate_remaining_effort(task, hours_per_step=3.0)
        if effort:
            print(f"  {effort['issue_key']}: ~{effort['total_remaining_hours']} часов осталось "
                  f"(текущий прогресс: {effort['current_completion']:.1f}%)")
    
    # ========================================
    # ЭТАП 7: Поиск по векторной БД (опционально)
    # ========================================
    print_separator("ЭТАП 7: ПОИСК ПО ВЕКТОРНОЙ БД")
    
    try:
        db_manager = VectorDBManager()
        retriever = db_manager.get_retriever(k=6)
        
        if tasks:
            first_task = tasks[0]
            # Формируем запрос с учётом плана реализации
            plan_str = "\n".join(first_task.implementation_plan) if first_task.implementation_plan else ""
            query = (f"summary={first_task.summary}\ndescription={first_task.description}\n"
                     f"project_role={first_task.project_role}\ndecomposition={first_task.decomposition}\n"
                     f"implementation_plan={plan_str}")
            
            print(f"Поиск для задачи: {first_task.issue_key}")
            search_results = retriever.invoke(query)
            
            for doc in search_results:
                print("\n--- НАЙДЕННЫЙ ФРАГМЕНТ ---")
                print(f"Источник: {doc.metadata.get('source', 'N/A')}")
                print(f"Содержимое: {doc.page_content[:200]}...")
    except Exception as e:
        print(f"Поиск по векторной БД пропущен: {e}")
    
    # ========================================
    # ИТОГОВАЯ СТАТИСТИКА
    # ========================================
    print_separator("ИТОГОВАЯ СТАТИСТИКА")
    
    summary = llm.get_completion_summary(tasks)
    print(f"Всего задач: {summary['total_tasks']}")
    print(f"Оценено задач: {summary['evaluated_tasks']}")
    print(f"Средний процент выполнения: {summary['average_completion']}%")
    print(f"Завершённых задач: {summary['completed_tasks']}")
    print(f"В процессе: {summary['in_progress_tasks']}")
    print(f"Не начатых: {summary['not_started_tasks']}")
    
    print("\nРаспределение по уверенности оценки:")
    for confidence, count in summary['by_confidence'].items():
        print(f"  {confidence}: {count}")
    
    if 'completion_distribution' in summary:
        print("\nРаспределение по диапазонам выполнения:")
        for range_name, count in summary['completion_distribution'].items():
            print(f"  {range_name}: {count}")
    
    print_separator("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")


if __name__ == "__main__":
    main()
