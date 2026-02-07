# ProjectTeamAssistant

Система для автоматизации оценки выполнения задач команды разработки с использованием LLM.

## 📋 Описание

ProjectTeamAssistant — это инструмент для автоматизации процессов управления задачами команды разработки. Он позволяет:

- 📥 **Загружать задачи** из CSV-файлов (экспорт из Jira)
- 🔍 **Декомпозировать задачи** на подзадачи с помощью LLM
- 📝 **Генерировать планы реализации** для каждой задачи
- 📊 **Оценивать процент выполнения** задач на основе анализа статуса и прогресса
- 📈 **Визуализировать данные** через интерактивный дашборд

## 🏗 Архитектура

```
ProjectTeamAssistant/
├── app/
│   ├── config/              # Конфигурация приложения
│   │   ├── settings.py       # Настройки из .env
│   │   └── yaml_loader.py    # Загрузка YAML конфигов
│   ├── services/
│   │   ├── completion/       # Сервис оценки выполнения
│   │   ├── dashboard/        # Сервис дашборда
│   │   ├── llm/              # Обёртка для LLM
│   │   └── pipeline/         # Основной пайплайн обработки
│   ├── utils/
│   │   ├── data/             # Утилиты загрузки данных
│   │   │   ├── gitlab_fetcher.py   # Загрузка из GitLab
│   │   │   ├── jira_csv_loader.py  # Загрузка из CSV
│   │   │   └── promt_loader.py      # Загрузка промптов
│   │   └── db/               # Работа с базой данных
│   ├── dashboard_app.py      # Streamlit дашборд
│   └── run_pipeline.py      # Точка входа пайплайна
├── config/
│   ├── promts/               # Промпты для LLM
│   │   ├── completion_evaluation_prompt.txt
│   │   ├── decomposition_prompt.txt
│   │   └── implementation_plan_prompt.txt
│   └── task_decomposition.yaml
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.10+
- Docker и Docker Compose (опционально)

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository_url>
cd ProjectTeamAssistant
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
.\venv\Scripts\activate   # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе примера:
```bash
cp .env.example .env
```

### Настройка переменных окружения

Создайте файл `.env` со следующими переменными:

```env
# LLM Settings
LLM_API_KEY=your_api_key
LLM_PROVIDER=openai  # или litellm
LITELLM_MODEL=gpt-4
TEMPERATURE=0.1
LITELLM_PROXY_URL=http://localhost:4000

# VectorDB Settings
DB_PERSIST_DIRECTORY=chroma_db
SOURCE_CODE_DIRECTORY=./data/repos
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
FORCE_RECREATE_DB=False

# Git Sync Settings
PAT=your_gitlab_pat
FORCE_FULL_SYNC=True
CONFIG_FILE_PATH=config/task_decomposition.yaml

# Decomposition Settings
RULES_FILEPATH=config/task_decomposition.yaml
DECOMPOSITION_PROMPT_FILEPATH=config/promts/decomposition_prompt.txt

# Dashboard Settings
DASHBOARD_JSON_FOLDER=data/output

# Pipeline Settings
CSV_DEFAULT_FOLDER=data/jira_tasks/
JSON_OUTPUT_FOLDER=data/output/
```

## 📖 Использование

### Запуск пайплайна

```bash
python app/run_pipeline.py --csv data/jira_tasks/tasks.csv --dashboard
```

### Запуск дашборда отдельно

```bash
streamlit run app/dashboard_app.py
```

### Docker

```bash
docker-compose up --build
```

## 📊 Формат входных данных

Система ожидает CSV-файл со следующими колонками:

| Колонка | Описание | Обязательная |
|---------|----------|--------------|
| Issue key | Идентификатор задачи | Да |
| Summary | Название задачи | Да |
| Status | Статус (To Do, In Progress, Done и т.д.) | Да |
| Issue id | ID задачи | Нет |
| Created | Дата создания | Нет |
| Updated | Дата обновления | Нет |
| Description | Описание задачи | Нет |
| Assignee | Исполнитель | Нет |
| Project role | Проектная роль (смета, эпик) | Нет |
| Due date | Срок выполнения | Нет |

### Пример CSV

```csv
Issue key,Summary,Status,Assignee,Project role
PROJ-123,Реализовать API авторизации,In Progress,Иван Иванов,"Смета 1|Эпик Auth"
PROJ-124,Написать unit-тесты,To Do,Петр Петров,"Смета 1|Эпик Auth"
```

## 📈 Результаты

После выполнения пайплайна создаются:

- **JSON-файл** с полными результатами анализа
- **CSV-файл** с таблицей задач и процентами выполнения
- **Дашборд** с интерактивной визуализацией

### Формат JSON-результата

```json
{
  "PROJ-123": {
    "overall_completion_percentage": 62,
    "status_factor": "Статус 'Code Review' указывает на завершение основной разработки",
    "steps_evaluation": [
      {
        "step_number": 1,
        "step_description": "Создать модель User",
        "is_completed": true,
        "completion_percentage": 100,
        "weight": 15,
        "reasoning": "Базовый шаг"
      }
    ],
    "confidence": "medium",
    "notes": "Завершены базовые шаги..."
  }
}
```

## 🔧 Конфигурация промптов

Промпты находятся в директории `config/promts/` и могут быть настроены под ваши нужды:

- [`completion_evaluation_prompt.txt`](config/promts/completion_evaluation_prompt.txt) — оценка выполнения задач
- [`decomposition_prompt.txt`](config/promts/decomposition_prompt.txt) — декомпозиция задач
- [`implementation_plan_prompt.txt`](config/promts/implementation_plan_prompt.txt) — генерация плана реализации

## 📁 Структура проекта

- [`app/services/pipeline/pipeline_service.py`](app/services/pipeline/pipeline_service.py) — основной пайплайн
- [`app/services/llm/llm_wrapper.py`](app/services/llm/llm_wrapper.py) — работа с LLM
- [`app/services/completion/completion_service.py`](app/services/completion/completion_service.py) — оценка выполнения
- [`app/services/dashboard/dashboard_service.py`](app/services/dashboard/dashboard_service.py) — формирование данных для дашборда
- [`app/dashboard_app.py`](app/dashboard_app.py) — Streamlit дашборд
- [`app/utils/data/jira_csv_loader.py`](app/utils/data/jira_csv_loader.py) — загрузка из CSV

## 🛠 Технологии

- **Python 3.10+**
- **LangChain** — работа с LLM
- **Streamlit** — интерактивный дашборд
- **Pandas** — обработка данных
- **PyYAML** — конфигурация
- **Docker** — контейнеризация

