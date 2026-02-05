# -*- coding: utf-8 -*-
"""
Скрипт для запуска полного пайплайна обработки задач.

Использование:
    # С указанием входного CSV
    python app/run_pipeline.py --csv data/jira_tasks/my_tasks.csv
    
    # С дашбордом после пайплайна
    python app/run_pipeline.py --csv data/jira_tasks/tasks.csv --dashboard
    
Для запуска дашборда используйте:
    streamlit run app/dashboard_app.py
"""

import argparse
import sys
import os
import subprocess

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings
from app.services.pipeline import PipelineService


def get_default_csv_path():
    """Получает путь к CSV файлу по умолчанию из настроек."""
    default_folder = getattr(settings, 'CSV_DEFAULT_FOLDER', 'data/jira_tasks/')
    
    # Ищем CSV файлы в папке по умолчанию
    if os.path.exists(default_folder):
        csv_files = [f for f in os.listdir(default_folder) if f.endswith('.csv')]
        if csv_files:
            # Возвращаем последний CSV файл (часто последний по дате)
            return os.path.join(default_folder, sorted(csv_files)[-1])
    
    return None


def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Полный пайплайн обработки задач: загрузка CSV -> декомпозиция -> оценка -> JSON с результатами",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Пайплайн с CSV файлом (JSON сохраняется автоматически в data/output):
  python app/run_pipeline.py
  python app/run_pipeline.py --csv data/jira_tasks/tasks.csv
  
  # Пайплайн с дашбордом:
  python app/run_pipeline.py --csv data/jira_tasks/tasks.csv --dashboard
  python app/run_pipeline.py --csv data/jira_tasks/tasks.csv --dashboard --port 8501

  # Запуск单独的 дашборда:
  streamlit run app/dashboard_app.py
        """
    )
    
    parser.add_argument(
        "--csv", "-c",
        type=str,
        default=None,
        help="Путь к CSV файлу с задачами из Jira (по умолчанию: первый CSV в папке из CSV_DEFAULT_FOLDER)"
    )
    
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Путь для сохранения JSON с результатами (по умолчанию: data/output/<имя_файла>_results.json)"
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


def run_dashboard(port: int):
    """Запускает дашборд через streamlit."""
    dashboard_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'app',
        'dashboard_app.py'
    )
    
    cmd = [sys.executable, '-m', 'streamlit', 'run', dashboard_script, '--', '--port', str(port)]
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска дашборда: {e}")
        return False
    except FileNotFoundError:
        print("❌ Ошибка: streamlit не найден. Установите его: pip install streamlit")
        return False


def main():
    """Главная функция запуска пайплайна."""
    args = parse_arguments()
    
    # Определяем путь к CSV файлу
    csv_path = args.csv
    if csv_path is None:
        csv_path = get_default_csv_path()
        if csv_path is None:
            print("❌ Ошибка: CSV файл не найден.")
            print("   Укажите путь к CSV файлу: --csv <путь>")
            print(f"   Или поместите CSV файл в папку: {getattr(settings, 'CSV_DEFAULT_FOLDER', 'data/jira_tasks/')}")
            sys.exit(1)
        else:
            print(f"📄 Используется CSV файл по умолчанию: {csv_path}")
    
    # Проверяем существование CSV файла
    if not os.path.exists(csv_path):
        print(f"❌ Ошибка: CSV файл не найден: {csv_path}")
        sys.exit(1)
    
    # Создаём сервис пайплайна
    pipeline = PipelineService()
    
    # Запускаем полный пайплайн (JSON сохраняется автоматически в data/output)
    result = pipeline.run_full_pipeline(
        csv_path=csv_path,
        output_json_path=args.json_output,
        rules_path=args.rules,
        prompt_path=args.prompt,
        completion_batch_size=args.batch_size
    )
    
    if not result.success:
        print("\n❌ Ошибки пайплайна:")
        for error in result.errors:
            print(f"   • {error}")
        sys.exit(1)
    
    print("\n✅ Пайплайн успешно завершён!")
    
    # Запускаем дашборд, если требуется
    if args.dashboard:
        print(f"\n🚀 Запуск дашборда на порту {args.port}...")
        run_dashboard(args.port)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
