# -*- coding: utf-8 -*-
"""
Интерактивный дашборд для отображения данных о выполнении задач.
Использует Streamlit для визуализации с раскрывающимися строками таблицы.

Запуск: streamlit run app/dashboard_app.py
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
import sys
import os
import random

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.dashboard import DashboardService
from app.utils.data.jira_csv_loader import JiraCsvLoader, JiraTask, CompletionEvaluation, StepEvaluation


def create_mock_completion_evaluation(task: JiraTask) -> CompletionEvaluation:
    """
    Создает моковую оценку выполнения для задачи (для тестирования).
    В реальности данные будут приходить из LLM сервиса.
    """
    # Генерируем случайные шаги
    num_steps = random.randint(3, 7)
    steps = []
    
    step_descriptions = [
        "Анализ требований",
        "Проектирование архитектуры",
        "Реализация основной логики",
        "Написание unit-тестов",
        "Интеграционное тестирование",
        "Code review",
        "Документирование",
        "Деплой на staging",
        "Финальное тестирование"
    ]
    
    for i in range(1, num_steps + 1):
        completion = random.randint(0, 100)
        is_completed = completion >= 100
        
        step = StepEvaluation(
            step_number=i,
            step_description=step_descriptions[i % len(step_descriptions)],
            is_completed=is_completed,
            completion_percentage=float(completion),
            weight=round(100 / num_steps, 1),
            reasoning="Оценка на основе анализа коммитов и статуса задачи"
        )
        steps.append(step)
    
    # Рассчитываем общий процент
    overall = sum(s.weighted_completion() for s in steps)
    
    confidence_options = ["high", "medium", "low"]
    
    status_factor_text = "Статус '" + task.status + "' учтен в оценке"
    
    return CompletionEvaluation(
        overall_completion_percentage=round(overall, 1),
        status_factor=status_factor_text,
        steps_evaluation=steps,
        confidence=random.choice(confidence_options),
        notes="Автоматически сгенерированная оценка для тестирования"
    )


def load_tasks_with_mock_data(csv_path: str) -> List[JiraTask]:
    """
    Загружает задачи из CSV и добавляет моковые данные оценки.
    """
    loader = JiraCsvLoader(csv_path)
    tasks = loader.load_tasks()
    
    # Добавляем моковые оценки выполнения
    for task in tasks:
        task.completion_evaluation = create_mock_completion_evaluation(task)
    
    return tasks


def create_demo_tasks() -> List[JiraTask]:
    """
    Создает демонстрационные задачи для тестирования без CSV файла.
    """
    demo_tasks = [
        JiraTask(
            issue_key="PROJ-101",
            issue_id=101,
            summary="Реализация API авторизации",
            status="In Progress",
            created="2026-01-15",
            updated="2026-02-01",
            description="Разработка REST API для авторизации пользователей",
            assignee="Иванов И.И.",
            components=["Dev Python", "Backend"]
        ),
        JiraTask(
            issue_key="PROJ-102",
            issue_id=102,
            summary="Интеграция с платежной системой",
            status="To Do",
            created="2026-01-20",
            updated="2026-01-25",
            description="Подключение к API платежного шлюза",
            assignee="Петров П.П.",
            components=["Dev Python"]
        ),
        JiraTask(
            issue_key="PROJ-103",
            issue_id=103,
            summary="Оптимизация запросов к БД",
            status="Done",
            created="2026-01-10",
            updated="2026-02-02",
            description="Улучшение производительности SQL запросов",
            assignee="Сидоров С.С.",
            components=["Dev Python", "Database"]
        ),
        JiraTask(
            issue_key="PROJ-104",
            issue_id=104,
            summary="Разработка модуля отчетности",
            status="In Progress",
            created="2026-01-18",
            updated="2026-02-01",
            description="Создание системы генерации отчетов",
            assignee="Козлов К.К.",
            components=["Dev Python", "Reports"]
        ),
        JiraTask(
            issue_key="PROJ-105",
            issue_id=105,
            summary="Миграция на новую версию фреймворка",
            status="In Review",
            created="2026-01-22",
            updated="2026-02-02",
            description="Обновление Django до версии 5.0",
            assignee="Новиков Н.Н.",
            components=["Dev Python"]
        ),
    ]
    
    # Добавляем моковые оценки
    for task in demo_tasks:
        task.completion_evaluation = create_mock_completion_evaluation(task)
    
    return demo_tasks


def render_step_details(steps: List[Dict[str, Any]]) -> None:
    """
    Отображает детали шагов в раскрывающемся блоке.
    """
    if not steps:
        st.info("Нет данных о шагах выполнения")
        return
    
    for step in steps:
        if step["is_completed"]:
            status_icon = "✅"
        elif step["completion_percentage"] > 0:
            status_icon = "🔄"
        else:
            status_icon = "⏳"
        
        col1, col2, col3 = st.columns([0.5, 3, 1])
        
        with col1:
            st.write(status_icon)
        
        with col2:
            step_title = "**Шаг " + str(step['step_number']) + ":** " + step['description']
            st.write(step_title)
            step_caption = "Вес: " + str(step['weight']) + "% | " + step['reasoning']
            st.caption(step_caption)
        
        with col3:
            st.progress(step["completion_percentage"] / 100)
            st.caption(str(int(step['completion_percentage'])) + "%")


def main():
    """
    Главная функция приложения дашборда.
    """
    st.set_page_config(
        page_title="Дашборд выполнения задач",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Дашборд выполнения задач")
    st.markdown("---")
    
    # Боковая панель с настройками
    with st.sidebar:
        st.header("⚙️ Настройки")
        
        data_source = st.radio(
            "Источник данных:",
            ["Демо-данные", "CSV файл"]
        )
        
        csv_path = None
        if data_source == "CSV файл":
            csv_path = st.text_input(
                "Путь к CSV файлу:",
                value="data/jira_tasks/tasks.csv"
            )
        
        st.markdown("---")
        st.markdown("""
        ### 📝 Легенда
        - 🟢 **Выполнено** (>=75%)
        - 🟡 **В процессе** (50-74%)
        - 🔴 **Требует внимания** (<50%)
        
        ### ℹ️ Информация
        Столбцы **Смета**, **Эпик** и **Ремейнинг** 
        заполнены моковыми данными для тестирования.
        """)
    
    # Загрузка данных
    try:
        if data_source == "CSV файл" and csv_path:
            tasks = load_tasks_with_mock_data(csv_path)
        else:
            tasks = create_demo_tasks()
    except Exception as e:
        st.error("Ошибка загрузки данных: " + str(e))
        tasks = create_demo_tasks()
        st.info("Используются демо-данные")
    
    if not tasks:
        st.warning("Нет задач для отображения")
        return
    
    # Создаем сервис дашборда
    dashboard_service = DashboardService()
    
    # Получаем статистику
    stats = dashboard_service.get_summary_stats(tasks)
    
    # Отображаем метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Всего задач", stats["total_tasks"])
    
    with col2:
        avg_text = str(round(stats['avg_completion'], 1)) + "%"
        st.metric("Средний прогресс", avg_text)
    
    with col3:
        st.metric("Завершено", stats["completed_tasks"])
    
    with col4:
        st.metric("В работе", stats["in_progress_tasks"])
    
    st.markdown("---")
    
    # Получаем данные для таблицы
    table_data = dashboard_service.to_flat_table_data(tasks)
    
    # Фильтры
    st.subheader("🔍 Фильтры")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        estimates = list(set(row["Смета"] for row in table_data))
        selected_estimate = st.multiselect("Смета:", estimates, default=estimates)
    
    with col2:
        epics = list(set(row["Эпик"] for row in table_data))
        selected_epic = st.multiselect("Эпик:", epics, default=epics)
    
    with col3:
        components = list(set(row["Компонент"] for row in table_data))
        selected_component = st.multiselect("Компонент:", components, default=components)
    
    # Фильтруем данные
    filtered_data = [
        row for row in table_data
        if row["Смета"] in selected_estimate
        and row["Эпик"] in selected_epic
        and row["Компонент"] in selected_component
    ]
    
    st.markdown("---")
    
    # Отображаем таблицу с раскрывающимися строками
    st.subheader("📋 Таблица задач")
    
    if not filtered_data:
        st.info("Нет задач, соответствующих фильтрам")
        return
    
    # Создаем раскрывающиеся строки
    for idx, row in enumerate(filtered_data):
        # Определяем цвет индикатора
        completion = row["Выполнение (%)"]
        if completion >= 75:
            indicator = "🟢"
        elif completion >= 50:
            indicator = "🟡"
        else:
            indicator = "🔴"
        
        # Создаем заголовок expander
        expander_title = (
            indicator + " **" + row['Задача'] + "** | " + 
            str(round(completion, 1)) + "% | " + row['Ремейнинг']
        )
        
        with st.expander(expander_title, expanded=False):
            # Основная информация
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Смета:** " + row['Смета'])
                st.markdown("**Эпик:** " + row['Эпик'])
                st.markdown("**Компонент:** " + row['Компонент'])
            
            with col2:
                st.markdown("**Статус:** " + row['Статус'])
                st.markdown("**Ремейнинг:** " + row['Ремейнинг'])
                st.progress(completion / 100)
            
            st.markdown("---")
            
            # Детали шагов
            st.markdown("##### 📝 Детали выполнения по шагам:")
            render_step_details(row["_steps"])
    
    st.markdown("---")
    
    # Альтернативный вид - сводная таблица
    with st.expander("📊 Сводная таблица (альтернативный вид)", expanded=False):
        # Создаем DataFrame для отображения
        df_display = pd.DataFrame([
            {
                "Смета": row["Смета"],
                "Эпик": row["Эпик"],
                "Компонент": row["Компонент"],
                "Задача": row["Задача"],
                "Статус": row["Статус"].split(" | ")[0],  # Только основной статус
                "Выполнение (%)": row["Выполнение (%)"],
                "Ремейнинг": row["Ремейнинг"]
            }
            for row in filtered_data
        ])
        
        # Стилизация таблицы
        def highlight_completion(val):
            if isinstance(val, (int, float)):
                if val >= 75:
                    return 'background-color: #d4edda'
                elif val >= 50:
                    return 'background-color: #fff3cd'
                else:
                    return 'background-color: #f8d7da'
            return ''
        
        styled_df = df_display.style.applymap(
            highlight_completion, 
            subset=['Выполнение (%)']
        )
        
        st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Экспорт данных
    st.markdown("---")
    st.subheader("📥 Экспорт данных")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Экспорт в CSV
        df_export = pd.DataFrame([
            {
                "Смета": row["Смета"],
                "Эпик": row["Эпик"],
                "Компонент": row["Компонент"],
                "Задача": row["Задача"],
                "Статус": row["Статус"],
                "Выполнение (%)": row["Выполнение (%)"],
                "Ремейнинг": row["Ремейнинг"]
            }
            for row in filtered_data
        ])
        
        csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📄 Скачать CSV",
            data=csv_data,
            file_name="dashboard_export.csv",
            mime="text/csv"
        )
    
    with col2:
        st.info("Для экспорта в другие форматы используйте сводную таблицу выше")


if __name__ == "__main__":
    main()
