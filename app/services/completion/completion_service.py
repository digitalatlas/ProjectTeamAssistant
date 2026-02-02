"""
Сервис для расчёта и анализа процента выполнения задач.
Предоставляет методы для работы с оценками выполнения без прямого обращения к LLM.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.utils.data.jira_csv_loader import JiraTask, CompletionEvaluation, StepEvaluation


class CompletionStatus(Enum):
    """Статусы выполнения задачи."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ALMOST_DONE = "almost_done"
    COMPLETED = "completed"


@dataclass
class TaskCompletionReport:
    """Отчёт о выполнении одной задачи."""
    issue_key: str
    summary: str
    status: str
    completion_percentage: float
    completion_status: CompletionStatus
    steps_completed: int
    steps_total: int
    confidence: str
    bottleneck_steps: List[str]  # Шаги, которые блокируют прогресс
    notes: Optional[str] = None


@dataclass
class ProjectCompletionReport:
    """Сводный отчёт о выполнении проекта/спринта."""
    total_tasks: int
    evaluated_tasks: int
    average_completion: float
    median_completion: float
    tasks_by_status: Dict[CompletionStatus, int]
    completion_distribution: Dict[str, int]
    high_risk_tasks: List[str]  # Задачи с низким прогрессом
    on_track_tasks: List[str]  # Задачи с хорошим прогрессом
    completed_tasks: List[str]  # Завершённые задачи


class CompletionService:
    """
    Сервис для расчёта и анализа процента выполнения задач.
    """

    # Пороговые значения для определения статуса
    THRESHOLD_NOT_STARTED = 5
    THRESHOLD_ALMOST_DONE = 85
    THRESHOLD_COMPLETED = 100

    # Пороговые значения для определения риска
    RISK_THRESHOLD_LOW_PROGRESS = 25
    RISK_THRESHOLD_GOOD_PROGRESS = 60

    def __init__(self):
        """Инициализация сервиса."""
        pass

    def get_completion_status(self, percentage: float) -> CompletionStatus:
        """
        Определяет статус выполнения на основе процента.

        :param percentage: Процент выполнения (0-100).
        :return: Статус выполнения.
        """
        if percentage < self.THRESHOLD_NOT_STARTED:
            return CompletionStatus.NOT_STARTED
        elif percentage >= self.THRESHOLD_COMPLETED:
            return CompletionStatus.COMPLETED
        elif percentage >= self.THRESHOLD_ALMOST_DONE:
            return CompletionStatus.ALMOST_DONE
        else:
            return CompletionStatus.IN_PROGRESS

    def calculate_weighted_completion(self, steps: List[StepEvaluation]) -> float:
        """
        Рассчитывает взвешенный процент выполнения на основе шагов.

        :param steps: Список оценок шагов.
        :return: Взвешенный процент выполнения.
        """
        if not steps:
            return 0.0

        total_weight = sum(step.weight for step in steps)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(step.weighted_completion() for step in steps)
        # Нормализуем, если сумма весов не равна 100
        return (weighted_sum / total_weight) * 100

    def identify_bottleneck_steps(
            self,
            steps: List[StepEvaluation],
            threshold: float = 50.0
    ) -> List[str]:
        """
        Определяет шаги, которые блокируют прогресс (не завершены и имеют высокий вес).

        :param steps: Список оценок шагов.
        :param threshold: Порог процента выполнения для определения блокирующего шага.
        :return: Список описаний блокирующих шагов.
        """
        bottlenecks = []
        for step in steps:
            if step.completion_percentage < threshold and step.weight >= 15:
                bottlenecks.append(
                    f"Шаг {step.step_number}: {step.step_description} "
                    f"({step.completion_percentage}% выполнено, вес: {step.weight}%)"
                )
        return bottlenecks

    def generate_task_report(self, task: JiraTask) -> Optional[TaskCompletionReport]:
        """
        Генерирует отчёт о выполнении для одной задачи.

        :param task: Задача с оценкой выполнения.
        :return: Отчёт о выполнении или None, если оценка отсутствует.
        """
        if not task.completion_evaluation:
            return None

        eval_data = task.completion_evaluation
        steps = eval_data.steps_evaluation

        completion_percentage = eval_data.overall_completion_percentage
        completion_status = self.get_completion_status(completion_percentage)

        steps_completed = sum(1 for s in steps if s.is_completed)
        steps_total = len(steps)

        bottlenecks = self.identify_bottleneck_steps(steps)

        return TaskCompletionReport(
            issue_key=task.issue_key,
            summary=task.summary,
            status=task.status,
            completion_percentage=completion_percentage,
            completion_status=completion_status,
            steps_completed=steps_completed,
            steps_total=steps_total,
            confidence=eval_data.confidence,
            bottleneck_steps=bottlenecks,
            notes=eval_data.notes
        )

    def generate_project_report(self, tasks: List[JiraTask]) -> ProjectCompletionReport:
        """
        Генерирует сводный отчёт о выполнении для списка задач.

        :param tasks: Список задач с оценками выполнения.
        :return: Сводный отчёт о выполнении проекта.
        """
        tasks_with_eval = [t for t in tasks if t.completion_evaluation]

        if not tasks_with_eval:
            return ProjectCompletionReport(
                total_tasks=len(tasks),
                evaluated_tasks=0,
                average_completion=0.0,
                median_completion=0.0,
                tasks_by_status={status: 0 for status in CompletionStatus},
                completion_distribution={
                    "0-25%": 0, "25-50%": 0, "50-75%": 0, "75-100%": 0
                },
                high_risk_tasks=[],
                on_track_tasks=[],
                completed_tasks=[]
            )

        # Собираем проценты выполнения
        completions = [
            (t.issue_key, t.completion_evaluation.overall_completion_percentage)
            for t in tasks_with_eval
        ]
        percentages = [c[1] for c in completions]

        # Рассчитываем статистику
        avg_completion = sum(percentages) / len(percentages)
        sorted_percentages = sorted(percentages)
        median_idx = len(sorted_percentages) // 2
        median_completion = sorted_percentages[median_idx]

        # Группируем по статусам
        tasks_by_status = {status: 0 for status in CompletionStatus}
        for _, pct in completions:
            status = self.get_completion_status(pct)
            tasks_by_status[status] += 1

        # Распределение по диапазонам
        completion_distribution = {
            "0-25%": sum(1 for p in percentages if 0 <= p < 25),
            "25-50%": sum(1 for p in percentages if 25 <= p < 50),
            "50-75%": sum(1 for p in percentages if 50 <= p < 75),
            "75-100%": sum(1 for p in percentages if 75 <= p <= 100)
        }

        # Определяем задачи по категориям риска
        high_risk_tasks = [
            key for key, pct in completions
            if pct < self.RISK_THRESHOLD_LOW_PROGRESS
        ]
        on_track_tasks = [
            key for key, pct in completions
            if self.RISK_THRESHOLD_LOW_PROGRESS <= pct < self.THRESHOLD_COMPLETED
        ]
        completed_tasks = [
            key for key, pct in completions
            if pct >= self.THRESHOLD_COMPLETED
        ]

        return ProjectCompletionReport(
            total_tasks=len(tasks),
            evaluated_tasks=len(tasks_with_eval),
            average_completion=round(avg_completion, 2),
            median_completion=round(median_completion, 2),
            tasks_by_status=tasks_by_status,
            completion_distribution=completion_distribution,
            high_risk_tasks=high_risk_tasks,
            on_track_tasks=on_track_tasks,
            completed_tasks=completed_tasks
        )

    def get_priority_tasks(
            self,
            tasks: List[JiraTask],
            limit: int = 5
    ) -> List[Tuple[str, float, List[str]]]:
        """
        Возвращает задачи, требующие приоритетного внимания.
        Сортирует по низкому проценту выполнения и наличию блокирующих шагов.

        :param tasks: Список задач с оценками выполнения.
        :param limit: Максимальное количество задач для возврата.
        :return: Список кортежей (issue_key, completion_percentage, bottleneck_steps).
        """
        priority_tasks = []

        for task in tasks:
            if not task.completion_evaluation:
                continue

            eval_data = task.completion_evaluation
            bottlenecks = self.identify_bottleneck_steps(eval_data.steps_evaluation)

            # Приоритет = низкий процент выполнения + наличие блокирующих шагов
            priority_score = (100 - eval_data.overall_completion_percentage) + len(bottlenecks) * 10

            priority_tasks.append((
                task.issue_key,
                eval_data.overall_completion_percentage,
                bottlenecks,
                priority_score
            ))

        # Сортируем по приоритету (убывание)
        priority_tasks.sort(key=lambda x: x[3], reverse=True)

        # Возвращаем без score
        return [(t[0], t[1], t[2]) for t in priority_tasks[:limit]]

    def estimate_remaining_effort(
            self,
            task: JiraTask,
            hours_per_step: float = 2.0
    ) -> Optional[Dict]:
        """
        Оценивает оставшийся объём работы для задачи.

        :param task: Задача с оценкой выполнения.
        :param hours_per_step: Среднее количество часов на один шаг.
        :return: Словарь с оценкой оставшейся работы.
        """
        if not task.completion_evaluation:
            return None

        steps = task.completion_evaluation.steps_evaluation
        if not steps:
            return None

        remaining_work = []
        total_remaining_hours = 0.0

        for step in steps:
            if step.completion_percentage < 100:
                remaining_pct = 100 - step.completion_percentage
                # Оценка часов пропорционально весу и оставшемуся проценту
                estimated_hours = (step.weight / 100) * hours_per_step * (remaining_pct / 100)
                total_remaining_hours += estimated_hours

                remaining_work.append({
                    "step_number": step.step_number,
                    "step_description": step.step_description,
                    "remaining_percentage": remaining_pct,
                    "estimated_hours": round(estimated_hours, 1)
                })

        return {
            "issue_key": task.issue_key,
            "current_completion": task.completion_evaluation.overall_completion_percentage,
            "remaining_steps": remaining_work,
            "total_remaining_hours": round(total_remaining_hours, 1),
            "confidence": task.completion_evaluation.confidence
        }

    def format_report_as_text(self, report: ProjectCompletionReport) -> str:
        """
        Форматирует отчёт о проекте в текстовый вид.

        :param report: Отчёт о выполнении проекта.
        :return: Текстовое представление отчёта.
        """
        lines = [
            "=" * 60,
            "ОТЧЁТ О ВЫПОЛНЕНИИ ПРОЕКТА",
            "=" * 60,
            "",
            f"Всего задач: {report.total_tasks}",
            f"Оценено задач: {report.evaluated_tasks}",
            f"Средний процент выполнения: {report.average_completion}%",
            f"Медианный процент выполнения: {report.median_completion}%",
            "",
            "--- Распределение по статусам ---",
        ]

        for status, count in report.tasks_by_status.items():
            lines.append(f"  {status.value}: {count}")

        lines.extend([
            "",
            "--- Распределение по диапазонам ---",
        ])

        for range_name, count in report.completion_distribution.items():
            lines.append(f"  {range_name}: {count}")

        if report.high_risk_tasks:
            lines.extend([
                "",
                "--- Задачи с высоким риском (< 25%) ---",
            ])
            for task_key in report.high_risk_tasks:
                lines.append(f"  - {task_key}")

        if report.completed_tasks:
            lines.extend([
                "",
                "--- Завершённые задачи ---",
            ])
            for task_key in report.completed_tasks:
                lines.append(f"  - {task_key}")

        lines.append("=" * 60)

        return "\n".join(lines)
