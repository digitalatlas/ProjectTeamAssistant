import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Класс для хранения всех конфигурационных настроек приложения.
    Читает переменные из .env файла и предоставляет их в виде атрибутов.
    """

    def __init__(self):
        project_root = Path(__file__).parent.parent.parent
        # --- LLM Settings ---
        self.LLM_API_KEY: str = os.getenv("LLM_API_KEY")
        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER")
        self.LITELLM_MODEL: str = os.getenv("LITELLM_MODEL")
        self.TEMPERATURE: float = float(os.getenv("TEMPERATURE"))
        self.LITELLM_PROXY_URL: str = os.getenv("LITELLM_PROXY_URL")

        # --- VectorDB Settings ---
        self.DB_PERSIST_DIRECTORY: str = project_root / os.getenv("DB_PERSIST_DIRECTORY")
        self.SOURCE_CODE_DIRECTORY: str = project_root / os.getenv("SOURCE_CODE_DIRECTORY")
        self.EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

        recreate_db_str = os.getenv("FORCE_RECREATE_DB", "False").lower()
        self.FORCE_RECREATE_DB: bool = recreate_db_str in ("true", "1", "t")

        # --- Git sync Settings ---
        self.PAT : str = os.getenv("PAT")
        force_full_sync_str = os.getenv("FORCE_FULL_SYNC", "True").lower()
        self.FORCE_FULL_SYNC: bool = force_full_sync_str in ("true", "1", "t")
        self.CONFIG_FILE_PATH: str  = project_root / os.getenv("CONFIG_FILE_PATH")

        # --- Decomposition Settings ---
        self.RULES_FILEPATH = project_root / os.getenv("RULES_FILEPATH")
        self.DECOMPOSITION_PROMPT_FILEPATH= project_root / os.getenv("DECOMPOSITION_PROMPT_FILEPATH")

        # --- Dashboard Settings ---
        self.DASHBOARD_JSON_FOLDER: str = os.getenv("DASHBOARD_JSON_FOLDER", "data/output")

        # --- Pipeline Settings ---
        self.CSV_DEFAULT_FOLDER: str = os.getenv("CSV_DEFAULT_FOLDER", "data/jira_tasks/")


settings = Settings()
