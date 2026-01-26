from pathlib import Path
from typing import List

import yaml
import os
from app.config.settings import settings


def load_repo_config(config_path: str) -> List[dict]:
    """
    Загружает список репозиториев из YAML файла.
    Заменяет плейсхолдеры PAT на реальный токен из окружения.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config_data = yaml.safe_load(file)

        repos = config_data.get('repositories', [])
        pat = settings.PAT

        if not pat:
            print("ВНИМАНИЕ: PAT не найден в окружении. URL репозиториев могут быть невалидными.")

        final_repos = []
        for repo in repos:
            # Замена плейсхолдера на реальный токен
            if pat and '<YOUR_PAT_PLACEHOLDER>' in repo.get('url', ''):
                repo['url'] = repo['url'].replace('<YOUR_PAT_PLACEHOLDER>', pat)

            # Добавляем путь к корню синхронизации
            if 'local_path' in repo:
                # Присоединяем к общему корневому пути, который будет в CodeSyncManager
                # Пока просто оставляем относительный путь, чтобы CodeSyncManager мог его собрать
                pass
            final_repos.append(repo)

        return final_repos

    except FileNotFoundError:
        raise FileNotFoundError(f"Файл конфигурации репозиториев не найден: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Ошибка парсинга YAML файла: {e}")
