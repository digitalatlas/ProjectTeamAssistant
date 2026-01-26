import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Класс для хранения всех конфигурационных настроек приложения.
    Читает переменные из .env файла и предоставляет их в виде атрибутов.
    """

    def __init__(self):
        # --- LLM Settings ---
        self.LLM_API_KEY: str = os.getenv("LLM_API_KEY")

        # --- VectorDB Settings ---
        self.DB_PERSIST_DIRECTORY: str = os.getenv("DB_PERSIST_DIRECTORY", "./chroma_db")
        self.SOURCE_CODE_DIRECTORY: str = os.getenv("SOURCE_CODE_DIRECTORY", "./data")
        self.EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

        recreate_db_str = os.getenv("FORCE_RECREATE_DB", "False").lower()
        self.FORCE_RECREATE_DB: bool = recreate_db_str in ("true", "1", "t")

        # --- Git sync options ---
        self.PAT : str = os.getenv("PAT")
        force_full_sync_str = os.getenv("FORCE_FULL_SYNC", "True").lower()
        self.FORCE_FULL_SYNC: bool = force_full_sync_str in ("true", "1", "t")
        self.CONFIG_FILE_PATH: str  = os.getenv("CONFIG_FILE_PATH")


settings = Settings()
