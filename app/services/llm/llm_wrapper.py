import os
import json
import re
from dotenv import load_dotenv
from typing import List, Dict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.exceptions import OutputParserException
from langchain_litellm import ChatLiteLLM

from app.utils.data.promt_loader import PromptLoader
from app.utils.data.jira_csv_loader import JiraTask, CompletionEvaluation, StepEvaluation


from app.config.settings import settings

load_dotenv()


class LLMService:
    """
    Универсальный сервис для взаимодействия с различными LLM.
    """

    def __init__(
            self,
            provider: str = settings.LLM_PROVIDER,
            model_name: str = settings.LITELLM_MODEL,
            temperature: float = settings.TEMPERATURE
    ):
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        print(f"Инициализация LLM Service с провайдером: '{provider}', модель: '{model_name}'")

        if self.provider == "litellm_proxy":
            if not settings.LITELLM_PROXY_URL:
                raise ValueError("Необходимо установить LITELLM_PROXY_URL в .env для провайдера 'litellm_proxy'")

            print(f"Подключение к LiteLLM прокси по адресу: {settings.LITELLM_PROXY_URL}")
            # Мы используем ChatOpenAI, но указываем ему адрес нашего прокси
            self.model = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                base_url=settings.LITELLM_PROXY_URL,  # Указываем URL нашего прокси
                api_key=settings.LLM_API_KEY  # Ключ для аутентификации на прокси
            )
        elif self.provider == "litellm":
            if not os.getenv("LLM_API_KEY"):  # Проверяем нужный ключ
                raise ValueError("Не найден LLM_API_KEY в переменных окружения.")
            self.model = ChatLiteLLM(model=model_name, temperature=temperature)
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")

    def generate_response(self, prompt: str) -> str:
        if not prompt: return "Ошибка: получен пустой промпт."
        print("\n--- Отправка запроса в LLM ---")
        try:
            messages = [HumanMessage(content=prompt)]
            response = self.model.invoke(messages)
            return response.content
        except Exception as e:
            print(f"Произошла ошибка при обращении к LLM: {e}")
            return f"Произошла ошибка API: {e}"



    def _sanitize_json_string(self, json_str: str) -> str:
        """
        Исправляет типичные ошибки форматирования JSON от LLM.
        """
        # Удаляем управляющие символы, которые могут сломать JSON
        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
        
        # Заменяем неэкранированные переносы строк внутри строк
        # Это сложная задача, поэтому используем построчную обработку
        lines = json_str.split('\n')
        cleaned_lines = []
        for line in lines:
            # Убираем trailing whitespace
            cleaned_lines.append(line.rstrip())
        json_str = '\n'.join(cleaned_lines)
        
        return json_str

    def _parse_json_response(self, response_str: str) -> Dict:
        """
        Извлекает и парсит JSON из ответа LLM.
        Поддерживает ответы в формате ```json ... ``` и чистый JSON.
        Включает механизмы восстановления при ошибках парсинга.
        """
        if not isinstance(response_str, str):
            print(f"Ошибка: LLM вернул не строку, а {type(response_str)}. Ответ: {response_str}")
            return {}

        json_part = ""
        try:
            # Сначала ищем начало JSON блока
            start_index = response_str.find('```json')
            if start_index != -1:
                # Если нашли, ищем конец блока после него
                end_index = response_str.find('```', start_index + 7)
                if end_index != -1:
                    json_part = response_str[start_index + 7: end_index].strip()
                else:
                    json_part = response_str[start_index + 7:].strip()
            else:
                # Если ```json не найден, ищем фигурные скобки
                start_brace = response_str.find('{')
                end_brace = response_str.rfind('}')
                if start_brace != -1 and end_brace != -1:
                    json_part = response_str[start_brace: end_brace + 1].strip()
                else:
                    json_part = response_str

            # Первая попытка - парсим как есть
            try:
                return json.loads(json_part)
            except json.JSONDecodeError:
                # Вторая попытка - очищаем и пробуем снова
                sanitized = self._sanitize_json_string(json_part)
                try:
                    return json.loads(sanitized)
                except json.JSONDecodeError:
                    # Третья попытка - парсим построчно, собирая валидные части
                    return self._parse_json_incrementally(json_part)

        except json.JSONDecodeError as e:
            print(f"Ошибка: не удалось распарсить JSON из ответа LLM. Ошибка: {e}")
            print(f"Текст, который пытались распарсить: \n---\n{json_part[:500]}...\n---")
            return {}
        except Exception as e:
            print(f"Произошла непредвиденная ошибка при парсинге: {e}")
            print(f"Полный ответ модели: \n{response_str[:500]}...")
            return {}

    def _parse_json_incrementally(self, json_str: str) -> Dict:
        """
        Пытается распарсить JSON инкрементально, обрабатывая каждый ключ отдельно.
        Это позволяет восстановить частичные результаты при ошибках.
        """
        result = {}
        
        # Ищем паттерн "ISSUE-KEY": [...]
        pattern = r'"([A-Z]+-\d+)":\s*\[(.*?)\](?=,\s*"[A-Z]+-\d+"|,?\s*})'
        matches = re.findall(pattern, json_str, re.DOTALL)
        
        for issue_key, array_content in matches:
            try:
                # Пытаемся распарсить массив
                array_str = f"[{array_content}]"
                # Очищаем от проблемных символов
                array_str = self._sanitize_json_string(array_str)
                parsed_array = json.loads(array_str)
                result[issue_key] = parsed_array
            except json.JSONDecodeError:
                # Если не получилось, пытаемся извлечь строки вручную
                strings = re.findall(r'"([^"]*(?:\\.[^"]*)*)"', array_content)
                if strings:
                    result[issue_key] = strings
                    
        if result:
            print(f"Частичный парсинг: успешно извлечено {len(result)} задач из {len(matches)} найденных.")
        
        return result

    def decompose_tasks(
            self,
            tasks: List[JiraTask],
            rules_path: str = settings.RULES_FILEPATH,
            prompt_path: str = settings.DECOMPOSITION_PROMPT_FILEPATH
    ) -> Dict[str, List[str]]:
        """
        Выполняет декомпозицию списка задач Jira с помощью LLM.
        """
        if not tasks:
            print("Список задач для декомпозиции пуст.")
            return {}

        print(f"\nНачало декомпозиции для {len(tasks)} задач...")

        final_prompt = PromptLoader.get_decomposition_prompt(
            tasks=tasks,
            rules_filepath=rules_path,
            prompt_template_filepath=prompt_path
        )

        response_str = self.generate_response(final_prompt)
        decomposed_data = self._parse_json_response(response_str)

        if decomposed_data:
            print("Декомпозиция успешно завершена и результат распарсен.")
        return decomposed_data

    def generate_implementation_plans(
            self,
            tasks: List[JiraTask],
            rules_path: str = settings.RULES_FILEPATH
    ) -> Dict[str, List[str]]:
        """
        Генерирует детальные планы реализации для задач с уже определённой декомпозицией.

        :param tasks: Список задач с заполненным полем decomposition.
        :param rules_path: Путь к YAML-файлу с правилами (для справки модели).
        :return: Словарь {issue_key: [список шагов плана]}.
        """
        # Фильтруем только задачи с декомпозицией
        tasks_with_decomposition = [t for t in tasks if t.decomposition]

        if not tasks_with_decomposition:
            print("Нет задач с декомпозицией для генерации плана реализации.")
            return {}

        print(f"\nГенерация планов реализации для {len(tasks_with_decomposition)} задач...")

        final_prompt = PromptLoader.get_implementation_plan_prompt(
            tasks=tasks_with_decomposition,
            rules_filepath=rules_path
        )

        response_str = self.generate_response(final_prompt)
        plans_data = self._parse_json_response(response_str)

        if plans_data:
            print("Планы реализации успешно сгенерированы и распарсены.")
        return plans_data

    def decompose_and_plan(
            self,
            tasks: List[JiraTask],
            rules_path: str = settings.RULES_FILEPATH,
            decomposition_prompt_path: str = settings.DECOMPOSITION_PROMPT_FILEPATH
    ) -> List[JiraTask]:
        """
        Выполняет полный цикл: декомпозиция задач + генерация планов реализации.

        :param tasks: Список задач для обработки.
        :param rules_path: Путь к YAML-файлу с правилами.
        :param decomposition_prompt_path: Путь к промпту декомпозиции.
        :return: Список задач с заполненными полями decomposition и implementation_plan.
        """
        if not tasks:
            print("Список задач пуст.")
            return tasks

        # Этап 1: Декомпозиция
        print("\n" + "=" * 50)
        print("ЭТАП 1: Декомпозиция задач")
        print("=" * 50)

        decomposition_result = self.decompose_tasks(
            tasks=tasks,
            rules_path=rules_path,
            prompt_path=decomposition_prompt_path
        )

        # Применяем результаты декомпозиции к задачам
        for task in tasks:
            if task.issue_key in decomposition_result:
                task.decomposition = decomposition_result[task.issue_key]

        # Этап 2: Генерация планов реализации
        print("\n" + "=" * 50)
        print("ЭТАП 2: Генерация планов реализации")
        print("=" * 50)

        plans_result = self.generate_implementation_plans(
            tasks=tasks,
            rules_path=rules_path
        )

        # Применяем планы к задачам
        for task in tasks:
            if task.issue_key in plans_result:
                task.implementation_plan = plans_result[task.issue_key]

        # Выводим итоговую статистику
        tasks_with_decomposition = sum(1 for t in tasks if t.decomposition)
        tasks_with_plans = sum(1 for t in tasks if t.implementation_plan)

        print("\n" + "=" * 50)
        print("ИТОГИ ОБРАБОТКИ")
        print("=" * 50)
        print(f"Всего задач: {len(tasks)}")
        print(f"Задач с декомпозицией: {tasks_with_decomposition}")
        print(f"Задач с планом реализации: {tasks_with_plans}")

        return tasks

    def evaluate_task_completion(
            self,
            tasks: List[JiraTask],
            rules_path: str = settings.RULES_FILEPATH,
            batch_size: int = 5
    ) -> Dict[str, CompletionEvaluation]:
        """
        Оценивает процент выполнения задач на основе декомпозиции, плана и атрибутов.
        Обрабатывает задачи батчами для лучшей надёжности.

        :param tasks: Список задач с декомпозицией и планом реализации.
        :param rules_path: Путь к YAML-файлу с правилами (для справки).
        :param batch_size: Количество задач в одном батче для обработки.
        :return: Словарь {issue_key: CompletionEvaluation}.
        """
        # Фильтруем только задачи с планом реализации
        tasks_with_plan = [t for t in tasks if t.implementation_plan]

        if not tasks_with_plan:
            print("Нет задач с планом реализации для оценки выполнения.")
            return {}

        print(f"\nОценка выполнения для {len(tasks_with_plan)} задач (батчами по {batch_size})...")

        result = {}
        
        # Разбиваем на батчи
        for i in range(0, len(tasks_with_plan), batch_size):
            batch = tasks_with_plan[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(tasks_with_plan) + batch_size - 1) // batch_size
            
            print(f"\n  Обработка батча {batch_num}/{total_batches} ({len(batch)} задач)...")

            final_prompt = PromptLoader.get_completion_evaluation_prompt(
                tasks=batch,
                rules_filepath=rules_path
            )

            response_str = self.generate_response(final_prompt)
            
            # Логируем первые 500 символов ответа для отладки
            print(f"  Получен ответ длиной {len(response_str)} символов")
            if not response_str or len(response_str) < 50:
                print(f"  ПРЕДУПРЕЖДЕНИЕ: Короткий или пустой ответ: {response_str[:200]}")
                continue
            
            evaluation_data = self._parse_json_response(response_str)
            
            if not evaluation_data:
                print(f"  ПРЕДУПРЕЖДЕНИЕ: Не удалось распарсить JSON из ответа")
                print(f"  Начало ответа: {response_str[:300]}...")
                continue

            # Преобразуем словари в объекты CompletionEvaluation
            batch_success = 0
            for issue_key, eval_dict in evaluation_data.items():
                try:
                    completion_eval = CompletionEvaluation.from_dict(eval_dict)
                    # Пересчитываем overall_completion_percentage на основе шагов
                    completion_eval.overall_completion_percentage = completion_eval.calculate_completion_from_steps()
                    result[issue_key] = completion_eval
                    batch_success += 1
                except Exception as e:
                    print(f"  Ошибка при парсинге оценки для {issue_key}: {e}")
                    continue
            
            print(f"  Успешно обработано: {batch_success}/{len(batch)} задач")

        if result:
            print(f"\nОценка выполнения успешно завершена для {len(result)}/{len(tasks_with_plan)} задач.")
        else:
            print(f"\nНе удалось получить оценки выполнения. Проверьте формат ответа LLM.")
        
        return result

    def full_analysis_with_completion(
            self,
            tasks: List[JiraTask],
            rules_path: str = settings.RULES_FILEPATH,
            decomposition_prompt_path: str = settings.DECOMPOSITION_PROMPT_FILEPATH,
            completion_batch_size: int = 5
    ) -> List[JiraTask]:
        """
        Выполняет полный цикл анализа: декомпозиция + план реализации + оценка выполнения.

        :param tasks: Список задач для обработки.
        :param rules_path: Путь к YAML-файлу с правилами.
        :param decomposition_prompt_path: Путь к промпту декомпозиции.
        :param completion_batch_size: Размер батча для оценки выполнения.
        :return: Список задач с заполненными полями decomposition, implementation_plan и completion_evaluation.
        """
        if not tasks:
            print("Список задач пуст.")
            return tasks

        # Этапы 1 и 2: Декомпозиция и план реализации
        tasks = self.decompose_and_plan(
            tasks=tasks,
            rules_path=rules_path,
            decomposition_prompt_path=decomposition_prompt_path
        )

        # Этап 3: Оценка выполнения
        print("\n" + "=" * 50)
        print("ЭТАП 3: Оценка процента выполнения")
        print("=" * 50)

        completion_result = self.evaluate_task_completion(
            tasks=tasks,
            rules_path=rules_path,
            batch_size=completion_batch_size
        )

        # Применяем оценки к задачам
        for task in tasks:
            if task.issue_key in completion_result:
                task.completion_evaluation = completion_result[task.issue_key]

        # Выводим итоговую статистику
        tasks_with_evaluation = sum(1 for t in tasks if t.completion_evaluation)

        print("\n" + "=" * 50)
        print("ИТОГИ ПОЛНОГО АНАЛИЗА")
        print("=" * 50)
        print(f"Всего задач: {len(tasks)}")
        print(f"Задач с декомпозицией: {sum(1 for t in tasks if t.decomposition)}")
        print(f"Задач с планом реализации: {sum(1 for t in tasks if t.implementation_plan)}")
        print(f"Задач с оценкой выполнения: {tasks_with_evaluation}")

        # Выводим сводку по проценту выполнения
        if tasks_with_evaluation > 0:
            print("\n--- Сводка по выполнению ---")
            for task in tasks:
                if task.completion_evaluation:
                    print(f"  {task.issue_key}: {task.completion_evaluation.overall_completion_percentage:.1f}% "
                          f"(уверенность: {task.completion_evaluation.confidence})")

        return tasks

    def get_completion_summary(self, tasks: List[JiraTask]) -> Dict:
        """
        Возвращает сводную статистику по выполнению задач.

        :param tasks: Список задач с оценкой выполнения.
        :return: Словарь со статистикой.
        """
        tasks_with_eval = [t for t in tasks if t.completion_evaluation]

        if not tasks_with_eval:
            return {
                "total_tasks": len(tasks),
                "evaluated_tasks": 0,
                "average_completion": 0.0,
                "completed_tasks": 0,
                "in_progress_tasks": 0,
                "not_started_tasks": 0,
                "by_confidence": {"high": 0, "medium": 0, "low": 0}
            }

        completions = [t.completion_evaluation.overall_completion_percentage for t in tasks_with_eval]
        avg_completion = sum(completions) / len(completions)

        completed = sum(1 for c in completions if c >= 100)
        in_progress = sum(1 for c in completions if 0 < c < 100)
        not_started = sum(1 for c in completions if c == 0)

        by_confidence = {"high": 0, "medium": 0, "low": 0}
        for t in tasks_with_eval:
            conf = t.completion_evaluation.confidence
            if conf in by_confidence:
                by_confidence[conf] += 1

        return {
            "total_tasks": len(tasks),
            "evaluated_tasks": len(tasks_with_eval),
            "average_completion": round(avg_completion, 2),
            "completed_tasks": completed,
            "in_progress_tasks": in_progress,
            "not_started_tasks": not_started,
            "by_confidence": by_confidence,
            "completion_distribution": {
                "0-25%": sum(1 for c in completions if 0 <= c < 25),
                "25-50%": sum(1 for c in completions if 25 <= c < 50),
                "50-75%": sum(1 for c in completions if 50 <= c < 75),
                "75-100%": sum(1 for c in completions if 75 <= c <= 100)
            }
        }