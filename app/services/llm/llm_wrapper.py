import os
from dotenv import load_dotenv
from typing import Literal

# Импортируем классы для работы с конкретными LLM
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama  # Для локальных моделей
from langchain_core.messages import HumanMessage
from langchain_core.exceptions import OutputParserException
from app.config.settings import settings
from langchain_community.chat_models import ChatLiteLLM

# Загружаем переменные окружения из .env файла (например, OPENAI_API_KEY)
load_dotenv()

# Определяем типы для автодополнения в IDE
LLMProvider = Literal["openai", "ollama"]


class LLMService:
    """
    Универсальный сервис для взаимодействия с различными LLM.
    Принимает на вход готовый промпт и возвращает текстовый ответ.
    """

    def __init__(
            self,
            provider: LLMProvider = "google",
            model_name: str = "gemeni-3-flash",  # Современная и недорогая модель OpenAI
            temperature: float = 0.3
    ):
        """
        Инициализация сервиса.

        :param provider: Провайдер LLM ('openai' или 'ollama').
        :param model_name: Конкретная модель (например, 'gpt-4o-mini', 'llama3').
        :param temperature: "Креативность" модели. 0.0 - строгий, 1.0 - очень креативный.
        """
        self.provider = provider
        self.model_name = model_name

        print(f"Инициализация LLM Service с провайдером: '{provider}', модель: '{model_name}'")

        if provider == "openai":
            # Проверяем наличие API ключа
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("Не найден OPENAI_API_KEY в переменных окружения.")
            self.model = ChatOpenAI(model=model_name, temperature=temperature)

        elif provider == "ollama":
            # Для Ollama ключ не нужен, но убедитесь, что сам сервис Ollama запущен
            try:
                self.model = ChatOllama(model=model_name, temperature=temperature)
            except ImportError:
                raise ImportError("Для использования Ollama установите 'langchain-community'.")
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")

    def generate_response(self, prompt: str) -> str:
        """
        Отправляет промпт в LLM и возвращает ответ.

        :param prompt: Полный текстовый промпт для LLM.
        :return: Сгенерированный LLM текстовый ответ.
        """
        if not prompt:
            return "Ошибка: получен пустой промпт."

        print("\n--- Отправка запроса в LLM ---")
        # print(f"Промпт: {prompt[:200]}...") # Раскомментируйте для отладки

        try:
            # Создаем сообщение в формате, который понимает модель
            messages = [HumanMessage(content=prompt)]

            # .invoke() - стандартный метод для вызова модели в LangChain
            response = self.model.invoke(messages)

            # Ответ от модели приходит в виде объекта, извлекаем текстовое содержимое
            return response.content

        except OutputParserException as e:
            print(f"Ошибка парсинга ответа от LLM: {e}")
            return f"Произошла ошибка при обработке ответа модели: {e}"
        except Exception as e:
            # Обработка других возможных ошибок (например, проблемы с API, сетью)
            print(f"Произошла ошибка при обращении к LLM: {e}")
            return f"Произошла ошибка API: {e}"


# --- Пример использования ---
if __name__ == "__main__":
    # --- Пример 1: Использование OpenAI ---
    print("--- Тестирование с OpenAI ---")
    try:
        # 1. Создаем экземпляр сервиса
        openai_service = LLMService(provider="openai", model_name="gpt-4o-mini")

        # 2. Формируем промпт (в вашем случае он будет приходить из другого модуля)
        final_prompt_for_llm = """Ты — ИИ-ассистент для разработчиков.
Основываясь на предоставленном контексте, ответь на вопрос пользователя.
Отвечай кратко и по делу на русском языке.

Контекст:
```python
# Файл: auth_service/core/permissions.py
def check_user_permissions(user, required_role):
    \"\"\"
    Проверяет, имеет ли пользователь необходимую роль.
    Администратор имеет доступ ко всему.
    \"\"\"
    if user.role == "admin":
        return True
    return user.role == required_role
Вопрос пользователя: Как проверить, является ли пользователь админом?

Ответ:
"""
        # 3. Получаем ответ
        response = openai_service.generate_response(final_prompt_for_llm)

        # 4. Выводим результат
        print("\n--- Ответ от LLM ---")
        print(response)

    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")