import os
import shutil
from typing import List
from git import Repo, GitCommandError
from app.config.yaml_loader import load_repo_config  # Новый импорт
from app.config.settings import settings

os.environ['GIT_TERMINAL_PROMPT'] = '0'

class CodeSyncManager:
    """
    Управляет синхронизацией, загружая список репозиториев из YAML файла.
    """

    def __init__(self,
                 force_full_sync: bool = settings.FORCE_FULL_SYNC,
                 config_file_path: str = settings.CONFIG_FILE_PATH):

        # 1. Загружаем список репозиториев из YAML файла
        repos_from_file = load_repo_config(config_file_path)

        # 2. Окончательно собираем полный путь для каждого репозитория
        self.repos = []
        for repo_conf in repos_from_file:
            # Собираем полный локальный путь: ../../data/auth_service
            repo_conf['local_path'] = os.path.join(settings.SOURCE_CODE_DIRECTORY, repo_conf['local_path'])
            self.repos.append(repo_conf)

        self.force_full_sync = force_full_sync

        print(f"Менеджер синхронизации кода инициализирован. Загружено {len(self.repos)} репозиториев.")


    def _clone_repository(self, repo_config: dict):
        local_path = repo_config['local_path']
        repo_url = repo_config['url']
        repo_name = repo_config['name']

        print(f"\n--- Клонирование репозитория '{repo_name}' ---")
        if os.path.exists(local_path):
            print(f"Папка {local_path} уже существует. Пропускаем клонирование.")
            return

        try:
            Repo.clone_from(repo_url, local_path)
            print(f"Успешно клонирован: {repo_name} в {local_path}")
        except GitCommandError as e:
            print(f"Ошибка клонирования репозитория {repo_name}. Проверьте URL/PAT: {e}")
        except Exception as e:
            print(f"Непредвиденная ошибка при клонировании: {e}")

    def _pull_repository(self, repo_config: dict):
        local_path = repo_config['local_path']
        repo_name = repo_config['name']

        print(f"\n--- Обновление репозитория '{repo_name}' (git pull) ---")
        if not os.path.exists(local_path):
            print(f"Папка {local_path} не найдена. Необходимо клонирование.")
            return

        try:
            repo = Repo(local_path)
            origin = repo.remotes.origin
            origin.fetch()
            origin.pull()
            print(f"Успешно обновлен: {repo_name}")
        except GitCommandError as e:
            print(
                f"Ошибка git pull в репозитории {repo_name}. Возможно, локальные изменения или проблемы с веткой: {e}")
        except Exception as e:
            print(f"Непредвиденная ошибка при обновлении: {e}")

    def synchronize(self):
        if self.force_full_sync and os.path.exists(settings.SOURCE_CODE_DIRECTORY):
            print(f"\n[ОПАСНО] Полная очистка корневой директории: {settings.SOURCE_CODE_DIRECTORY}")
            shutil.rmtree(settings.SOURCE_CODE_DIRECTORY)
            os.makedirs(settings.SOURCE_CODE_DIRECTORY, exist_ok=True)

        for repo_config in self.repos:
            if self.force_full_sync or not os.path.exists(repo_config['local_path']):
                self._clone_repository(repo_config)
            else:
                self._pull_repository(repo_config)

        print("\n=== Синхронизация кода завершена ===")