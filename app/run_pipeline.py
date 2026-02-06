# -*- coding: utf-8 -*-
"""
Скрипт запуска полного пайплайна проекта: синхронизация репозиториев, построение векторной базы,
обработка всех CSV-файлов с задачами и запуск дашборда.

Использование:
    python app/run_pipeline.py             # Обрабатывает все CSV из папки CSV_DEFAULT_FOLDER и сохраняет JSON
    python app/run_pipeline.py --csv data/jira_tasks/tasks.csv
    python app/run_pipeline.py --csv data/jira_tasks/tasks.csv --dashboard
    python app/run_pipeline.py --dashboard --port 8501
"""

import argparse
import sys
import os
import subprocess
from typing import List, Optional

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings
from app.services.pipeline import PipelineService
from app.utils.data.gitlab_fetcher import CodeSyncManager
from app.utils.db.db_manager import VectorDBManager


def sync_repositories() -> None:
    """Синхронизирует показанные в конфигурации репозитории с локальной копией."""
    print("\n" + "=" * 60)
    print("ЭТАП 0: Синхронизация репозиториев")
    print("=" * 60)
    try:
        sync_manager = CodeSyncManager()
        sync_manager.synchronize()
    except Exception as exc:
        print(f"❌ Не удалось синхронизировать репозитории: {exc}")
        sys.exit(1)


def build_vector_database(force_recreate: Optional[bool] = None) -> None:
    """Создаёт или обновляет векторную базу данных проекта."""
    print("\n" + "=" * 60)
    print("ЭТАП 1: Построение векторной базы данных")
    print("=" * 60)

    recreate = settings.FORCE_RECREATE_DB if force_recreate is None else force_recreate
    try:
        db_manager = VectorDBManager()
        db_manager.create_index_from_directory(force_recreate=recreate)
    except Exception as exc:
        print(f"❌ Ошибка построения векторной базы: {exc}")
        sys.exit(1)


def get_csv_paths_to_process(explicit_csv: Optional[str]) -> List[str]:
    """Возвращает список CSV-файлов для обработки: либо один указанный пользователем, либо все из папки по умолчанию."""
    if explicit_csv:
        if not os.path.exists(explicit_csv):
            print(f"❌ CSV файл не найден: {explicit_csv}")
            return []
        return [explicit_csv]

    csv_folder = str(settings.CSV_DEFAULT_FOLDER)
    if not os.path.isdir(csv_folder):
        print(f"❌ Папка с CSV по умолчанию не найдена: {csv_folder}")
        return []

    csv_files = [
        os.path.join(csv_folder, f)
        for f in os.listdir(csv_folder)
        if f.lower().endswith(".csv")
    ]

    csv_files = sorted(csv_files, key=lambda path: os.path.getmtime(path))
    return csv_files


def run_pipeline_for_csvs(csv_paths: List[str], pipeline: PipelineService, args: argparse.Namespace) -> bool:
    """Прогоняет пайплайн последовательно для каждого CSV-файла."""
    if args.json_output and len(csv_paths) > 1:
        print("ℹ️  Параметр --json-output применяется только к одному CSV; генерация пути будет выполнена автоматически для каждого файла.")

    overall_success = True
    for idx, csv_path in enumerate(csv_paths, start=1):
        print("\n" + "~" * 60)
        print(f"Файл ({idx}/{len(csv_paths)}): {csv_path}")
        print("~" * 60)

        output_json = args.json_output if len(csv_paths) == 1 else None
        result = pipeline.run_full_pipeline(
            csv_path=csv_path,
            output_json_path=output_json,
            rules_path=args.rules,
            prompt_path=args.prompt,
            completion_batch_size=args.batch_size
        )

        if not result.success:
            overall_success = False

    return overall_success


def parse_arguments() -> argparse.Namespace:
    """Парсинг аргументов командной строки для запуска пайплайна проекта."""
    parser = argparse.ArgumentParser(
        description="Выполняет полный пайплайн: git sync -> векторная база -> LLM -> JSON -> дашборд",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--csv", "-c",
        type=str,
        default=None,
        help="Путь к CSV-файлу с задачами (если не указан, будут обработаны все CSV из CSV_DEFAULT_FOLDER)"
    )

    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Путь для сохранения результатов в JSON (только если обрабатывается один CSV-файл)"
    )

    parser.add_argument(
        "--dashboard", "-d",
        action="store_true",
        help="Запустить Streamlit-дашборд после обработки"
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
        help="Путь к YAML-файлу с правилами декомпозиции"
    )

    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Путь к файлу с промптом для декомпозиции"
    )

    return parser.parse_args()


def run_dashboard(port: int) -> bool:
    """Запускает Streamlit-дашборд с помощью subprocess."""
    dashboard_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'app',
        'dashboard_app.py'
    )

    cmd = [sys.executable, '-m', 'streamlit', 'run', dashboard_script, '--', '--port', str(port)]

    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"❌ Ошибка запуска дашборда: {exc}")
        return False
    except FileNotFoundError:
        print("❌ streamlit не найден. Установите его: pip install streamlit")
        return False


def main() -> None:
    """Основной сценарий запуска полного пайплайна проекта."""
    args = parse_arguments()

    csv_paths = get_csv_paths_to_process(args.csv)
    if not csv_paths:
        print("❌ CSV-файлы для обработки не найдены.")
        sys.exit(1)

    sync_repositories()
    build_vector_database()

    pipeline = PipelineService()
    success = run_pipeline_for_csvs(csv_paths, pipeline, args)

    if not success:
        sys.exit(1)

    print("\n✅ Все CSV-файлы успешно обработаны.")

    if args.dashboard:
        print(f"\n🚀 Запуск дашборда на порту {args.port}...")
        run_dashboard(args.port)

    sys.exit(0)


if __name__ == "__main__":
    main()
