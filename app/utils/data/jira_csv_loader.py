import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional, Any


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
    components: List[str] = field(default_factory=list)
    due_date: Optional[str] = None
    decomposition: Optional[List[str]] = None
    implementation_plan: Optional[List[str]] = None

    # Мы добавляем этот метод, чтобы дата-класс мог принимать 'сырые' данные из pandas,
    # где пустые значения могут быть None или NaN, и корректно их обрабатывать.
    def __post_init__(self):
        # Преобразуем компоненты из строки (если они есть) в список
        if self.components and isinstance(self.components, str):
            self.components = [comp.strip() for comp in self.components.split(',')]
        elif not self.components or pd.isna(self.components):
            self.components = []


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
        'Component/s': 'components',
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

            df = df[df['components'] == 'Dev Python']
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


# --- Пример использования ---
if __name__ == "__main__":
    # 1. Создаем экземпляр загрузчика
    loader = JiraCsvLoader(csv_filepath="../../../data/jira_tasks/tasks.csv")

    # 2. Загружаем задачи
    all_tasks = loader.load_tasks()

    # 3. Работаем с результатом
    if all_tasks:
        print("\n--- Первая загруженная задача ---")
        first_task = all_tasks[0]

        # Теперь вы можете легко обращаться к данным через атрибуты объекта
        print(f"Ключ: {first_task.issue_key}")
        print(f"Заголовок: {first_task.summary}")
        print(f"Описание: {first_task.description}")  # Будет полным
        print(f"Исполнитель: {first_task.assignee}")
        print(f"Статус: {first_task.status}")
        print(f"Компоненты (как список): {first_task.components}")  # -> ['Backend', 'Auth']

        print("\n--- Вторая загруженная задача---")
        second_task = all_tasks[1]
        print(f"Ключ: {second_task.issue_key}")
        print(f"Описание: {second_task.description}")  # Будет None
        print(f"Исполнитель: {second_task.assignee}")  # Будет None
