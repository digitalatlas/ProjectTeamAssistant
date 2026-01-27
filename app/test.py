from app.services.code_preprocessing.code_preprocessor import VectorDBManager
from app.services.llm.llm_wrapper import LLMService
from app.services.data_fetcher.gitlab_fetcher import CodeSyncManager

import pandas as pd

# sync_manager = CodeSyncManager()
# sync_manager.synchronize()


# db_manager = VectorDBManager()
# db_manager.create_index_from_directory()
#
# query = 'Promotions: delete and docker fixes'
#
# retriever = db_manager.get_retriever()
# search_results = retriever.invoke(query)
#
# print(f"\nРезультаты поиска по запросу: '{query}'")
# for doc in search_results:
#     print("\n--- НАЙДЕННЫЙ ФРАГМЕНТ ---")
#     print(f"Источник (метаданные): {doc.metadata.get('source', 'N/A')}")
#     print("Содержимое:")
#     print(doc.page_content)

data = pd.read_csv('data/jira_tasks/tasks.csv')
print(data.columns)