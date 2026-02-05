"""
Сервис для формирования данных дашборда по задачам.
Подготавливает иерархические данные для отображения в таблице с раскрывающимися строками.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from app.utils.data.jira_csv_loader import JiraTask, CompletionEvaluation


@dataclass
class DashboardRow:
    """Строка дашборда с данными о задаче."""
    estimate: str  # Смета (мок)
    epic: str  # Эпик (мок)
    project_role: str  # Проектная роль
    task_key: str  # Ключ задачи
    task_summary: str  # Название задачи
    status_details: str  # Подробности о статусе
    completion_percentage: float  # Процент выполнения
    remaining: str  # Ремейнинг из Jira (мок)
    steps: List[Dict[str, Any]] = field(default_factory=list)  # Детали шагов для раскрытия


class DashboardService:
    """
    Сервис для формирования данных дашборда.
    Преобразует задачи в формат, подходящий для отображения в иерархической таблице.
    
    TODO: Для подключения реальных данных:
    1. Добавить поля estimate, epic, remaining в JiraTask
    2. Обновить JiraCsvLoader.COLUMN_MAPPING для новых колонок
    3. Заменить вызовы _get_mock_* на task.estimate, task.epic, task.remaining
    """

    # Моковые значения-заглушки (одинаковые для всех задач)
    MOCK_ESTIMATE = "[MOCK] Смета не указана"
    MOCK_EPIC = "[MOCK] Эпик не указан"
    MOCK_REMAINING = "[MOCK] N/A"

    def __init__(self):
        """Инициализация сервиса."""
        pass

    def _get_estimate(self, task: JiraTask) -> str:
        """
        Возвращает смету для задачи.
        
        TODO: Заменить на реальные данные:
            return task.estimate if hasattr(task, 'estimate') and task.estimate else self.MOCK_ESTIMATE
        """
        # Проверяем, есть ли реальные данные в задаче
        if hasattr(task, 'estimate') and task.estimate:
            return task.estimate
        return self.MOCK_ESTIMATE

    def _get_epic(self, task: JiraTask) -> str:
        """
        Возвращает эпик для задачи.
        
        TODO: Заменить на реальные данные:
            return task.epic if hasattr(task, 'epic') and task.epic else self.MOCK_EPIC
        """
        # Проверяем, есть ли реальные данные в задаче
        if hasattr(task, 'epic') and task.epic:
            return task.epic
        return self.MOCK_EPIC

    def _get_remaining(self, task: JiraTask) -> str:
        """
        Возвращает ремейнинг для задачи.
        
        TODO: Заменить на реальные данные из Jira API:
            return task.remaining if hasattr(task, 'remaining') and task.remaining else self.MOCK_REMAINING
        """
        # Проверяем, есть ли реальные данные в задаче
        if hasattr(task, 'remaining') and task.remaining:
            return task.remaining
        return self.MOCK_REMAINING

    def _format_status_details(self, task: JiraTask) -> str:
        """
        Формирует подробное описание статуса задачи.
        """
        details = [f"Статус: {task.status}"]

        if task.completion_evaluation:
            eval_data = task.completion_evaluation
            
            # Добавляем информацию о шагах
            steps = eval_data.steps_evaluation
            if steps:
                completed_steps = sum(1 for s in steps if s.is_completed)
                total_steps = len(steps)
                details.append(f"Шаги: {completed_steps}/{total_steps}")
            
            # Добавляем уровень уверенности
            confidence_map = {
                "high": "Высокая",
                "medium": "Средняя",
                "low": "Низкая"
            }
            confidence = confidence_map.get(eval_data.confidence, eval_data.confidence)
            details.append(f"Уверенность: {confidence}")
            
            # Добавляем заметки, если есть
            if eval_data.notes:
                details.append(f"Примечание: {eval_data.notes[:50]}...")

        return " | ".join(details)

    def _extract_steps_details(self, task: JiraTask) -> List[Dict[str, Any]]:
        """
        Извлекает детали шагов для раскрывающейся части строки.
        """
        if not task.completion_evaluation:
            return []

        steps_details = []
        for step in task.completion_evaluation.steps_evaluation:
            steps_details.append({
                "step_number": step.step_number,
                "description": step.step_description,
                "is_completed": step.is_completed,
                "completion_percentage": step.completion_percentage,
                "weight": step.weight,
                "reasoning": step.reasoning
            })

        return steps_details

    def create_dashboard_row(self, task: JiraTask) -> DashboardRow:
        """
        Создаёт строку дашборда из задачи.
        
        :param task: Задача Jira.
        :return: Строка дашборда.
        """
        project_role = ", ".join(task.project_role) if task.project_role else "Не указана"
        
        completion = 0.0
        if task.completion_evaluation:
            completion = task.completion_evaluation.overall_completion_percentage

        return DashboardRow(
            estimate=self._get_estimate(task),
            epic=self._get_epic(task),
            project_role=project_role,
            task_key=task.issue_key,
            task_summary=task.summary,
            status_details=self._format_status_details(task),
            completion_percentage=completion,
            remaining=self._get_remaining(task),
            steps=self._extract_steps_details(task)
        )

    def create_dashboard_data(self, tasks: List[JiraTask]) -> List[DashboardRow]:
        """
        Создаёт данные дашборда из списка задач.
        
        :param tasks: Список задач Jira.
        :return: Список строк дашборда.
        """
        return [self.create_dashboard_row(task) for task in tasks]

    def get_hierarchical_data(self, tasks: List[JiraTask]) -> Dict[str, Any]:
        """
        Формирует иерархические данные для дашборда.
        Группирует задачи по смете -> эпику -> проектной роли.
        
        :param tasks: Список задач Jira.
        :return: Иерархическая структура данных.
        """
        rows = self.create_dashboard_data(tasks)
        
        hierarchy: Dict[str, Dict[str, Dict[str, List[DashboardRow]]]] = {}
        
        for row in rows:
            if row.estimate not in hierarchy:
                hierarchy[row.estimate] = {}
            
            if row.epic not in hierarchy[row.estimate]:
                hierarchy[row.estimate][row.epic] = {}
            
            if row.project_role not in hierarchy[row.estimate][row.epic]:
                hierarchy[row.estimate][row.epic][row.project_role] = []
            
            hierarchy[row.estimate][row.epic][row.project_role].append(row)
        
        return hierarchy

    def to_flat_table_data(self, tasks: List[JiraTask]) -> List[Dict[str, Any]]:
        """
        Преобразует задачи в плоский формат для таблицы.
        
        :param tasks: Список задач Jira.
        :return: Список словарей с данными для таблицы.
        """
        rows = self.create_dashboard_data(tasks)
        
        table_data = []
        for row in rows:
            table_data.append({
                "Смета": row.estimate,
                "Эпик": row.epic,
                "Проектная роль": row.project_role,
                "Задача": f"{row.task_key}: {row.task_summary}",
                "Статус": row.status_details,
                "Выполнение (%)": row.completion_percentage,
                "Ремейнинг": row.remaining,
                "_steps": row.steps,  # Скрытое поле для раскрытия
                "_task_key": row.task_key  # Для идентификации
            })
        
        return table_data

    def get_summary_stats(self, tasks: List[JiraTask]) -> Dict[str, Any]:
        """
        Возвращает сводную статистику для дашборда.
        
        :param tasks: Список задач Jira.
        :return: Словарь со статистикой.
        """
        rows = self.create_dashboard_data(tasks)
        
        if not rows:
            return {
                "total_tasks": 0,
                "avg_completion": 0,
                "completed_tasks": 0,
                "in_progress_tasks": 0,
                "not_started_tasks": 0
            }
        
        completions = [row.completion_percentage for row in rows]
        
        return {
            "total_tasks": len(rows),
            "avg_completion": round(sum(completions) / len(completions), 2),
            "completed_tasks": sum(1 for c in completions if c >= 100),
            "in_progress_tasks": sum(1 for c in completions if 0 < c < 100),
            "not_started_tasks": sum(1 for c in completions if c == 0)
        }
