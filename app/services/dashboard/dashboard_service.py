"""
Сервис для формирования данных дашборда по задачам.
Подготавливает иерархические данные для отображения в таблице с раскрывающимися строками.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import random

from app.utils.data.jira_csv_loader import JiraTask, CompletionEvaluation


@dataclass
class DashboardRow:
    """Строка дашборда с данными о задаче."""
    estimate: str  # Смета (мок)
    epic: str  # Эпик (мок)
    component: str  # Роль/компонент
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
    """

    # Моковые данные для смет
    MOCK_ESTIMATES = [
        "Смета Q1-2026",
        "Смета Q2-2026",
        "Бюджет разработки",
        "Техническое обслуживание",
        "Инновационный проект"
    ]

    # Моковые данные для эпиков
    MOCK_EPICS = [
        "EPIC-001: Модернизация платформы",
        "EPIC-002: Интеграция с внешними системами",
        "EPIC-003: Улучшение UX",
        "EPIC-004: Оптимизация производительности",
        "EPIC-005: Безопасность и аудит"
    ]

    def __init__(self):
        """Инициализация сервиса."""
        self._estimate_cache: Dict[str, str] = {}
        self._epic_cache: Dict[str, str] = {}

    def _get_mock_estimate(self, task_key: str) -> str:
        """
        Возвращает моковую смету для задачи.
        Кэширует результат для консистентности.
        """
        if task_key not in self._estimate_cache:
            self._estimate_cache[task_key] = random.choice(self.MOCK_ESTIMATES)
        return self._estimate_cache[task_key]

    def _get_mock_epic(self, task_key: str) -> str:
        """
        Возвращает моковый эпик для задачи.
        Кэширует результат для консистентности.
        """
        if task_key not in self._epic_cache:
            self._epic_cache[task_key] = random.choice(self.MOCK_EPICS)
        return self._epic_cache[task_key]

    def _get_mock_remaining(self, task: JiraTask) -> str:
        """
        Возвращает моковый ремейнинг для задачи.
        В реальности будет получаться из Jira API.
        """
        if task.completion_evaluation:
            # Генерируем ремейнинг на основе процента выполнения
            completion = task.completion_evaluation.overall_completion_percentage
            if completion >= 100:
                return "0h"
            elif completion >= 75:
                return f"{random.randint(1, 4)}h"
            elif completion >= 50:
                return f"{random.randint(4, 8)}h"
            elif completion >= 25:
                return f"{random.randint(8, 16)}h"
            else:
                return f"{random.randint(16, 40)}h"
        return "N/A"

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
        component = ", ".join(task.components) if task.components else "Не указан"
        
        completion = 0.0
        if task.completion_evaluation:
            completion = task.completion_evaluation.overall_completion_percentage

        return DashboardRow(
            estimate=self._get_mock_estimate(task.issue_key),
            epic=self._get_mock_epic(task.issue_key),
            component=component,
            task_key=task.issue_key,
            task_summary=task.summary,
            status_details=self._format_status_details(task),
            completion_percentage=completion,
            remaining=self._get_mock_remaining(task),
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
        Группирует задачи по смете -> эпику -> компоненту.
        
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
            
            if row.component not in hierarchy[row.estimate][row.epic]:
                hierarchy[row.estimate][row.epic][row.component] = []
            
            hierarchy[row.estimate][row.epic][row.component].append(row)
        
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
                "Компонент": row.component,
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
