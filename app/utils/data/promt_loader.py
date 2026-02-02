# app/utils/prompt_loader.py
import yaml
import json
from typing import List
from app.utils.data.jira_csv_loader import JiraTask
from app.config.settings import settings

class PromptLoader:
    """
    Класс для загрузки и форматирования промптов из файлов.
    """
    @staticmethod
    def _format_tasks_for_prompt(tasks: List[JiraTask]) -> str:
        """Преобразует список объектов JiraTask в единую строку для промпта."""
        task_strings = []
        for task in tasks:
            # Игнорируем описание, если оно пустое
            description = task.description if task.description else "Нет описания."
            task_str = (
                f"issue_key: {task.issue_key}\n"
                f"Заголовок: {task.summary}\n"
                f"Описание: {description}"
            )
            task_strings.append(task_str)
        # Разделяем задачи для лучшей читаемости моделью
        return "\n---\n".join(task_strings)

    @staticmethod
    def get_decomposition_prompt(
        tasks: List[JiraTask],
        rules_filepath: str = settings.RULES_FILEPATH,
        prompt_template_filepath: str = settings.DECOMPOSITION_PROMPT_FILEPATH
    ) -> str:
        """
        Собирает финальный промпт для декомпозиции задач.

        :param tasks: Список задач для анализа.
        :param rules_filepath: Путь к YAML-файлу с правилами.
        :param prompt_template_filepath: Путь к текстовому файлу с шаблоном промпта.
        :return: Готовый к отправке промпт в виде строки.
        """
        # 1. Загружаем шаблон промпта
        with open(prompt_template_filepath, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # 2. Загружаем правила из YAML
        with open(rules_filepath, 'r', encoding='utf-8') as f:
            rules_data = yaml.safe_load(f).get('decomposition_rules', [])

        # Преобразуем правила в JSON-строку, как того требует промпт
        rules_json_str = json.dumps(rules_data, ensure_ascii=False, indent=2)
        # 3. Форматируем задачи в строку
        tasks_str = PromptLoader._format_tasks_for_prompt(tasks)

        # 4. Вставляем все в шаблон
        final_prompt = prompt_template.replace('<rules_placeholder>', rules_json_str)
        final_prompt = final_prompt.replace('<tasks_placeholder>', tasks_str)

        return final_prompt

    @staticmethod
    def _format_tasks_with_decomposition(tasks: List[JiraTask]) -> str:
        """
        Преобразует список объектов JiraTask с декомпозицией в строку для промпта.
        Включает шаги декомпозиции для каждой задачи.
        """
        task_strings = []
        for task in tasks:
            description = task.description if task.description else "Нет описания."
            decomposition_str = ", ".join(task.decomposition) if task.decomposition else "Не определено"
            task_str = (
                f"issue_key: {task.issue_key}\n"
                f"Заголовок: {task.summary}\n"
                f"Описание: {description}\n"
                f"Шаги декомпозиции: {decomposition_str}"
            )
            task_strings.append(task_str)
        return "\n---\n".join(task_strings)

    @staticmethod
    def get_implementation_plan_prompt(
        tasks: List[JiraTask],
        rules_filepath: str = settings.RULES_FILEPATH,
        prompt_template_filepath: str = None
    ) -> str:
        """
        Собирает финальный промпт для генерации плана реализации задач.

        :param tasks: Список задач с уже определённой декомпозицией.
        :param rules_filepath: Путь к YAML-файлу с правилами (для справки).
        :param prompt_template_filepath: Путь к текстовому файлу с шаблоном промпта.
        :return: Готовый к отправке промпт в виде строки.
        """
        # Определяем путь к промпту по умолчанию
        if prompt_template_filepath is None:
            prompt_template_filepath = settings.DECOMPOSITION_PROMPT_FILEPATH.parent / "implementation_plan_prompt.txt"

        # 1. Загружаем шаблон промпта
        with open(prompt_template_filepath, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # 2. Загружаем правила из YAML (для справки модели)
        with open(rules_filepath, 'r', encoding='utf-8') as f:
            rules_data = yaml.safe_load(f).get('decomposition_rules', [])

        rules_json_str = json.dumps(rules_data, ensure_ascii=False, indent=2)

        # 3. Форматируем задачи с декомпозицией
        tasks_str = PromptLoader._format_tasks_with_decomposition(tasks)

        # 4. Вставляем все в шаблон
        final_prompt = prompt_template.replace('<rules_placeholder>', rules_json_str)
        final_prompt = final_prompt.replace('<tasks_placeholder>', tasks_str)

        return final_prompt