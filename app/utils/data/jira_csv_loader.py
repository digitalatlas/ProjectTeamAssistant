import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


@dataclass
class StepEvaluation:
    """Оценка выполнения одного шага плана реализации."""
    step_number: int
    step_description: str
    is_completed: bool
    completion_percentage: float  # 0-100
    weight: float  # Вес шага в общей задаче (сумма всех весов = 100)
    reasoning: str  # Обоснование оценки

    def weighted_completion(self) -> float:
        """Возвращает взвешенный вклад шага в общий процент выполнения."""
        return (self.completion_percentage * self.weight) / 100


@dataclass
class CompletionEvaluation:
    """Результат оценки выполнения задачи."""
    overall_completion_percentage: float  # Общий процент выполнения (0-100)
    status_factor: str  # Описание влияния статуса на оценку
    steps_evaluation: List[StepEvaluation] = field(default_factory=list)
    confidence: str = "medium"  # high, medium, low
    notes: Optional[str] = None  # Дополнительные заметки

    def __post_init__(self):
        """Пересчитываем overall_completion_percentage из шагов для надёжности."""
        self.overall_completion_percentage = self.calculate_completion_from_steps()

    def calculate_completion_from_steps(self) -> float:
        """Рассчитывает процент выполнения на основе оценки шагов."""
        if not self.steps_evaluation:
            return 0.0
        return sum(step.weighted_completion() for step in self.steps_evaluation)

    @classmethod
    def from_dict(cls, data: Dict) -> 'CompletionEvaluation':
        """Создаёт объект CompletionEvaluation из словаря (результата парсинга JSON)."""
        steps = []
        for step_data in data.get('steps_evaluation', []):
            step = StepEvaluation(
                step_number=step_data.get('step_number', 0),
                step_description=step_data.get('step_description', ''),
                is_completed=step_data.get('is_completed', False),
                completion_percentage=float(step_data.get('completion_percentage', 0)),
                weight=float(step_data.get('weight', 0)),
                reasoning=step_data.get('reasoning', '')
            )
            steps.append(step)

        return cls(
            overall_completion_percentage=float(data.get('overall_completion_percentage', 0)),
            status_factor=data.get('status_factor', ''),
            steps_evaluation=steps,
            confidence=data.get('confidence', 'medium'),
            notes=data.get('notes')
        )


# Для того чтобы сделать код более читабельным и удобным для IDE,
# мы определим дата-класс, который будет представлять одну задачу из Jira.
# Атрибуты названы в "змеином_регистре" (snake_case) для соответствия PEP 8.
@dataclass
class JiraTask:
    """Структурированное представление задачи из Jira."""
    issue_key: str
    issue_id: int
    summary: str
    status: str
    created: str
    updated: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    project_role: List[str] = field(default_factory=list)
    due_date: Optional[str] = None
    decomposition: Optional[List[str]] = None
    implementation_plan: Optional[List[str]] = None
    completion_evaluation: Optional[CompletionEvaluation] = None

    # Мы добавляем этот метод, чтобы дата-класс мог принимать 'сырые' данные из pandas,
    # где пустые значения могут быть None или NaN, и корректно их обрабатывать.
    def __post_init__(self):
        # Преобразуем проектные роли из строки (если они есть) в список
        if isinstance(self.project_role, str):
            self.project_role = [role.strip() for role in self.project_role.split(',')]
        elif isinstance(self.project_role, list):
            # Уже список, оставляем как есть
            pass
        elif self.project_role is None:
            self.project_role = []
        else:
            # Проверяем на NaN (для pandas)
            try:
                if pd.isna(self.project_role):
                    self.project_role = []
            except (ValueError, TypeError):
                # Если pd.isna не может обработать, оставляем пустой список
                self.project_role = []

    def get_completion_percentage(self) -> float:
        """Возвращает процент выполнения задачи."""
        if self.completion_evaluation:
            return self.completion_evaluation.overall_completion_percentage
        return 0.0

    def is_fully_completed(self) -> bool:
        """Проверяет, полностью ли выполнена задача."""
        return self.get_completion_percentage() >= 100.0


class JiraCsvLoader:
    """
    Класс для загрузки задач из CSV-файла, экспортированного из Jira.
    """
    # Словарь для переименования колонок из CSV в атрибуты нашего дата-класса
    COLUMN_MAPPING = {
        'Issue key': 'issue_key',
        'Issue id': 'issue_id',
        'Summary': 'summary',
        'Description': 'description',
        'Assignee': 'assignee',
        'Status': 'status',
        'Created': 'created',
        'Updated': 'updated',
        'Custom field (Проектная роль)': 'project_role',
        'Due Date': 'due_date'
    }

    def __init__(self, csv_filepath: str):
        """
        Инициализация загрузчика.
        :param csv_filepath: Путь к CSV-файлу с задачами.
        """
        if not csv_filepath.endswith('.csv'):
            raise ValueError("Файл должен иметь расширение .csv")
        self.filepath = csv_filepath
        print(f"Инициализирован загрузчик для файла: {self.filepath}")

    def load_tasks(self) -> List[JiraTask]:
        """
        Читает CSV-файл и возвращает список объектов JiraTask.

        :return: Список задач.
        """
        try:
            import os
            current_directory = os.getcwd()
            print(current_directory)
            # Читаем CSV с помощью pandas
            df = pd.read_csv(self.filepath)

            # Проверяем наличие всех необходимых колонок
            required_cols = self.COLUMN_MAPPING.keys()
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"В CSV файле отсутствуют необходимые колонки: {', '.join(missing_cols)}")

            # Выбираем только нужные колонки и переименовываем их
            df = df[list(self.COLUMN_MAPPING.keys())]
            df = df.rename(columns=self.COLUMN_MAPPING)

            df = df[df['project_role'] == 'Dev Python']
            # Заменяем 'NaN' (стандартное значение для пустых ячеек в pandas) на None
            # Это важно для корректной работы с Optional типами в дата-классе
            df = df.where(pd.notnull(df), None)

            # Преобразуем каждую строку DataFrame в объект JiraTask
            tasks = [JiraTask(**row) for row in df.to_dict(orient='records')]

            print(f"Успешно загружено {len(tasks)} задач.")
            return tasks

        except FileNotFoundError:
            print(f"Ошибка: Файл не найден по пути {self.filepath}")
            return []
        except Exception as e:
            print(f"Произошла ошибка при чтении или обработке файла: {e}")
            return []

