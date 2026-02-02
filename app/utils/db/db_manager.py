import os
import shutil
from typing import List

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from app.config.settings import settings

# Конфигурация
DB_PERSIST_DIRECTORY = "../../chroma_db"
SOURCE_CODE_DIRECTORY = "../../data"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


class VectorDBManager:
    """
    Класс для управления созданием и обновлением векторной базы данных.
    С исправленной логикой удаления и обновленными импортами.
    """

    def __init__(self,
                 persist_directory: str = settings.DB_PERSIST_DIRECTORY,
                 embedding_model_name: str = settings.EMBEDDING_MODEL_NAME):
        self.persist_directory = persist_directory
        print(f"Загрузка embedding-модели: {embedding_model_name}...")
        # Используем новый класс HuggingFaceEmbeddings
        self.embedding_function = HuggingFaceEmbeddings(
            model_name=embedding_model_name
        )
        self.vector_store = None
        print("Менеджер векторной БД инициализирован.")

    def _load_and_split_documents(self, source_dir: str) -> List[Document]:
        """
        Загружает файлы и разделяет их на чанки.
        """
        print(f"\nЗагрузка документов из директории: {source_dir}")
        loader = DirectoryLoader(
            source_dir,
            glob="**/*.*",  # Лучше использовать *.* чтобы не захватывать папки
            loader_cls=TextLoader,
            loader_kwargs={'encoding': 'utf-8', 'autodetect_encoding': True},
            show_progress=True,
            silent_errors=True
        )
        documents = loader.load()
        if not documents:
            print("Документы для индексации не найдены.")
            return []
        print(f"Найдено {len(documents)} файлов для обработки.")

        universal_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        split_chunks = universal_splitter.split_documents(documents)
        print(f"Документы разделены на {len(split_chunks)} чанков.")
        return split_chunks

    def create_index_from_directory(self,
                                    source_directory: str = settings.SOURCE_CODE_DIRECTORY,
                                    force_recreate: bool = settings.FORCE_RECREATE_DB):
        if force_recreate and os.path.exists(self.persist_directory):
            print(f"Удаление старой векторной БД: {self.persist_directory}")
            shutil.rmtree(self.persist_directory)

        chunks = self._load_and_split_documents(source_directory)
        if not chunks:
            return

        print("\nНачало процесса векторизации и индексации...")
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embedding_function,
            persist_directory=self.persist_directory
        )

        print(f"Векторная база данных успешно создана в {self.persist_directory}")

    def get_retriever(self, k: int = 5):
        """
        Метод для получения объекта retriever для последующего поиска.
        """
        if self.vector_store is None:
            # Если индекс не создавался, а просто подключаемся к существующему
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embedding_function
            )
        return self.vector_store.as_retriever(
            search_kwargs={'k': k}
        )
