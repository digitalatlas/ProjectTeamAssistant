# -*- coding: utf-8 -*-
"""
Скрипт для запуска полного пайплайна обработки задач.

Использование:
    # Полный пайплайн с CSV
    python app/run_pipeline.py --csv data/jira_tasks/tasks.csv
    python app/run_pipeline.py --csv data/jira_tasks/tasks.csv --output data/output/results.json
    python app/run_pipeline.py --csv data/jira_tasks/tasks.csv --dashboard
    
    # Запуск дашборда из сохранённых JSON результатов (без LLM обработки)
    python app/run_pipeline.py --json data/output/results.json --dashboard
"""

import argparse
import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pipeline import PipelineService


def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Полный пайплайн обработки задач: загрузка CSV -> декомпозиция -> оценка -> дашборд",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Полный пайплайн с CSV файлом:
  python app/run_pipeline.py --csv data/jira_tasks/tasks.csv
  python app/run_pipeline.py --csv data/jira_tasks/tasks.csv --output results.json
  python app/run_pipeline.py --csv data/jira_tasks/tasks.csv --dashboard
  python app/run_pipeline.py --csv data/jira_tasks/tasks.csv --dashboard --port 8502

  # Запуск дашборда из сохранённых результатов (без LLM):
  python app/run_pipeline.py --json data/output/results.json --dashboard
  python app/run_pipeline.py --json data/output/results.json --dashboard --port 8502
        """
    )
    
    # Группа взаимоисключающих источников данных
    source_group = parser.add_mutually_exclusive_group(required=True)
    
    source_group.add_argument(
        "--csv", "-c",
        type=str,
        help="Путь к CSV файлу с задачами из Jira (запускает полный пайплайн с LLM)"
    )
    
    source_group.add_argument(
        "--json", "-j",
        type=str,
        help="Путь к JSON файлу с результатами пайплайна (только для дашборда, без LLM)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Путь для сохранения результатов в JSON (только для --csv режима)"
    )
    
    parser.add_argument(
        "--dashboard", "-d",
        action="store_true",
        help="Запустить интерактивный дашборд после обработки"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8501,
        help="Порт для дашборда (по умолчанию: 8501)"
    )
    
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=5,
        help="Размер батча для оценки выполнения (по умолчанию: 5)"
    )
    
    parser.add_argument(
        "--rules",
        type=str,
        default=None,
        help="Путь к YAML файлу с правилами декомпозиции"
    )
    
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Путь к файлу с промптом декомпозиции"
    )
    
    return parser.parse_args()


def main():
    """Главная функция запуска пайплайна."""
    args = parse_arguments()
    
    # Создаём сервис пайплайна
    pipeline = PipelineService()
    
    # Режим JSON - только дашборд из сохранённых результатов
    if args.json:
        # Проверяем существование JSON файла
        if not os.path.exists(args.json):
            print(f"❌ Ошибка: JSON файл не найден: {args.json}")
            sys.exit(1)
        
        if not args.dashboard:
            print("⚠️  Режим --json требует флаг --dashboard для запуска дашборда")
            print("   Используйте: python app/run_pipeline.py --json <путь> --dashboard")
            sys.exit(1)
        
        # Запускаем дашборд из JSON
        result = pipeline.run_dashboard_from_json(
            json_path=args.json,
            port=args.port
        )
    
    # Режим CSV - полный пайплайн
    else:
        # Проверяем существование CSV файла
        if not os.path.exists(args.csv):
            print(f"❌ Ошибка: CSV файл не найден: {args.csv}")
            sys.exit(1)
        
        # Запускаем полный пайплайн
        result = pipeline.run_full_pipeline(
            csv_path=args.csv,
            output_json_path=args.output,
            launch_dashboard=args.dashboard,
            dashboard_port=args.port,
            rules_path=args.rules,
            prompt_path=args.prompt,
            completion_batch_size=args.batch_size
        )
    
    # Возвращаем код выхода
    if result.success:
        print("\n✅ Операция успешно завершена!")
        sys.exit(0)
    else:
        print("\n❌ Операция завершилась с ошибками")
        for error in result.errors:
            print(f"   • {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
