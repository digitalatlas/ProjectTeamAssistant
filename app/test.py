from typing import List

from app.utils.data.jira_csv_loader import JiraCsvLoader, JiraTask
from app.services.llm.llm_wrapper import LLMService

from app.utils.db.db_manager import VectorDBManager

import pandas as pd


csv_loader = JiraCsvLoader('data/jira_tasks/tasks.csv')
tasks: List[JiraTask] = csv_loader.load_tasks()

llm = LLMService()

# Используем новый метод для полного цикла: декомпозиция + план реализации
tasks = llm.decompose_and_plan(tasks)

# Выводим результаты для первой задачи
if tasks:
    first_task = tasks[0]
    print("\n" + "=" * 60)
    print(f"ЗАДАЧА: {first_task.issue_key}")
    print("=" * 60)
    print(f"Заголовок: {first_task.summary}")
    print(f"\nОписание: {first_task.description}")
    
    print(f"\nШаги декомпозиции:")
    if first_task.decomposition:
        for step in first_task.decomposition:
            print(f"  - {step}")
    else:
        print("  (не определены)")
    
    print(f"\nПлан реализации:")
    if first_task.implementation_plan:
        for step in first_task.implementation_plan:
            print(f"  {step}")
    else:
        print("  (не сгенерирован)")

# Поиск по векторной БД с учётом плана реализации
db_manager = VectorDBManager()
# db_manager.create_index_from_directory()
retriever = db_manager.get_retriever(k=6)

if tasks:
    first_task = tasks[0]
    # Формируем запрос с учётом плана реализации
    plan_str = "\n".join(first_task.implementation_plan) if first_task.implementation_plan else ""
    query = (f"summary={first_task.summary}\ndescription={first_task.description}\n"
             f"components={first_task.components}\ndecomposition={first_task.decomposition}\n"
             f"implementation_plan={plan_str}")
    print("\n" + "=" * 60)
    print("ПОИСК ПО ВЕКТОРНОЙ БД")
    print("=" * 60)
    search_results = retriever.invoke(query)
    for doc in search_results:
        print("\n--- НАЙДЕННЫЙ ФРАГМЕНТ ---")
        print(f"Источник (метаданные): {doc.metadata.get('source', 'N/A')}")
        print("Содержимое:")
        print(doc.page_content)


# sync_manager = CodeSyncManager()
# sync_manager.synchronize()
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
