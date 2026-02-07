# -*- coding: utf-8 -*-
"""
Интерактивный дашборд для отображения данных о выполнении задач.
Использует Streamlit для визуализации с раскрывающимися строками таблицы.

Запуск: streamlit run app/dashboard_app.py
"""

import os
os.environ.setdefault("STREAMLIT_SERVER_FILEWATCHERTYPE", "none")

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
import sys
import json
import glob
import yaml

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.dashboard import DashboardService
from app.config.settings import settings
from app.utils.data.jira_csv_loader import JiraTask, CompletionEvaluation, StepEvaluation


def load_tasks_from_json(json_path: str) -> List[JiraTask]:
    """
    Загружает задачи из JSON файла (результат пайплайна).
    Восстанавливает полные данные включая оценки выполнения.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tasks = []
    for task_data in data:
        # Создаём объект JiraTask
        task = JiraTask(
            issue_key=task_data.get('issue_key', ''),
            issue_id=task_data.get('issue_id', 0),
            summary=task_data.get('summary', ''),
            status=task_data.get('status', ''),
            created=task_data.get('created', ''),
            updated=task_data.get('updated', ''),
            description=task_data.get('description'),
            assignee=task_data.get('assignee'),
            project_role=task_data.get('project_role', []),
            due_date=task_data.get('due_date'),
            decomposition=task_data.get('decomposition'),
            implementation_plan=task_data.get('implementation_plan')
        )
        
        # Восстанавливаем оценку выполнения, если есть
        if 'completion_evaluation' in task_data and task_data['completion_evaluation']:
            eval_data = task_data['completion_evaluation']
            steps = []
            for step_data in eval_data.get('steps_evaluation', []):
                step = StepEvaluation(
                    step_number=step_data.get('step_number', 0),
                    step_description=step_data.get('step_description', ''),
                    is_completed=step_data.get('is_completed', False),
                    completion_percentage=float(step_data.get('completion_percentage', 0)),
                    weight=float(step_data.get('weight', 0)),
                    reasoning=step_data.get('reasoning', '')
                )
                steps.append(step)
            
            task.completion_evaluation = CompletionEvaluation(
                overall_completion_percentage=float(eval_data.get('overall_completion_percentage', 0)),
                status_factor=eval_data.get('status_factor', ''),
                steps_evaluation=steps,
                confidence=eval_data.get('confidence', 'medium'),
                notes=eval_data.get('notes')
            )
        
        tasks.append(task)
    
    return tasks


def get_json_files_from_folder(folder_path: str) -> List[str]:
    """
    Возвращает список JSON файлов из указанной папки.
    """
    if not os.path.exists(folder_path):
        return []
    
    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    return sorted(json_files)


def load_primitives_from_yaml(yaml_path: str) -> List[Dict[str, str]]:
    """
    Загружает примитивы из YAML файла декомпозиции задач.
    
    :param yaml_path: Путь к YAML файлу с декомпозицией.
    :return: Список словарей с id и description примитивов.
    """
    if not os.path.exists(yaml_path):
        return []
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        if data and 'decomposition_rules' in data:
            primitives = []
            for rule in data['decomposition_rules']:
                primitives.append({
                    'id': rule.get('id', ''),
                    'description': rule.get('description', '')
                })
            return primitives
        return []
    except Exception as e:
        print(f"Ошибка загрузки YAML: {e}")
        return []


def get_task_primitives(task: JiraTask) -> List[str]:
    """
    Возвращает список примитивов задачи из декомпозиции.
    
    :param task: Задача Jira.
    :return: Список ID примитивов.
    """
    if task.decomposition and isinstance(task.decomposition, list):
        return [str(p) for p in task.decomposition]
    return []


def calculate_primitive_stats_for_all(tasks: List[JiraTask]) -> List[Dict[str, Any]]:
    """
    Рассчитывает статистику для всех примитивов в отфильтрованных задачах.
    
    Смысл метрик:
    - completion: средняя выполненность именно этого примитива в задачах
      (рассчитывается как средняя доля выполнения задачи, приходящаяся на этот примитив)
    - incompleteness_contribution: вклад в незавершённость, суммируется в 100%
      (это доля общей незавершённости работы над данным примитивом)
    
    :param tasks: Список отфильтрованных задач.
    :return: Список словарей со статистикой по каждому примитиву.
    """
    if not tasks:
        return []
    
    # Собираем все уникальные примитивы из задач
    all_primitives = set()
    for task in tasks:
        task_primitives = get_task_primitives(task)
        all_primitives.update(task_primitives)
    
    total_tasks = len(tasks)
    
    # Создаём список для результатов
    primitive_stats = []
    
    for primitive in all_primitives:
        # Задачи, содержащие данный примитив
        tasks_with_primitive = [
            task for task in tasks
            if primitive in get_task_primitives(task)
        ]
        
        tasks_with_count = len(tasks_with_primitive)
        
        # Процент задач с примитивом
        primitive_percentage = (tasks_with_count / total_tasks) * 100 if total_tasks > 0 else 0
        
        # Вес примитива в задаче рассчитывается как 1/количество_примитивов_в_задаче
        # (равномерное распределение работы между примитивами)
        # Выполненность примитива = средняя доля выполнения задачи, приходящаяся на этот примитив
        primitive_completions = []
        for task in tasks_with_primitive:
            task_primitives = get_task_primitives(task)
            primitives_count = len(task_primitives)
            if primitives_count > 0:
                # Доля выполнения задачи, приходящаяся на этот примитив
                task_completion = task.get_completion_percentage()
                primitive_share = task_completion / primitives_count
                primitive_completions.append(primitive_share)
        
        # Средняя выполненность именно этого примитива
        avg_primitive_completion = sum(primitive_completions) / len(primitive_completions) if primitive_completions else 0
        
        # Вклад в незавершённость: средняя доля незавершённости, приходящаяся на этот примитив
        primitive_incompletenesses = []
        for task in tasks_with_primitive:
            task_primitives = get_task_primitives(task)
            primitives_count = len(task_primitives)
            if primitives_count > 0:
                # Доля незавершённости задачи, приходящаяся на этот примитив
                task_incompleteness = 100 - task.get_completion_percentage()
                primitive_share_incompleteness = task_incompleteness / primitives_count
                primitive_incompletenesses.append(primitive_share_incompleteness)
        
        avg_primitive_incompleteness = sum(primitive_incompletenesses) / len(primitive_incompletenesses) if primitive_incompletenesses else 0
        
        # Собираем все средние незавершённости примитивов для нормализации
        all_avg_incompletenesses = []
        for p in all_primitives:
            p_tasks = [t for t in tasks if p in get_task_primitives(t)]
            if p_tasks:
                p_incompletenesses = []
                for t in p_tasks:
                    t_primitives = get_task_primitives(t)
                    if len(t_primitives) > 0:
                        t_incompleteness = 100 - t.get_completion_percentage()
                        p_incompletenesses.append(t_incompleteness / len(t_primitives))
                if p_incompletenesses:
                    all_avg_incompletenesses.append(sum(p_incompletenesses) / len(p_incompletenesses))
        
        total_avg_incompleteness = sum(all_avg_incompletenesses) if all_avg_incompletenesses else 1
        
        # Вклад в незавершённость (нормализуем, чтобы сумма была 100%)
        if total_avg_incompleteness > 0:
            incompleteness_contribution = (avg_primitive_incompleteness / total_avg_incompleteness) * 100
        else:
            incompleteness_contribution = 0
        
        # Добавляем статистику для данного примитива
        primitive_stats.append({
            'primitive': primitive,
            'tasks_count': tasks_with_count,
            'tasks_percentage': round(primitive_percentage, 1),
            'weight': round(avg_primitive_completion, 1),
            'completion': round(avg_primitive_completion, 1),
            'incompleteness_contribution': round(incompleteness_contribution, 1)
        })
    
    return primitive_stats


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
    
    # Получаем папку с JSON файлами из настроек
    json_folder = settings.DASHBOARD_JSON_FOLDER
    
    # Получаем список JSON файлов
    json_files = get_json_files_from_folder(json_folder)
    
    if not json_files:
        st.warning(f"📂 Папка '{json_folder}' не найдена или пуста")
        st.info("Создайте JSON файлы в формате результатов пайплайна")
        st.stop()
    
    # Получаем относительные пути для отображения
    file_options = [os.path.relpath(f, json_folder) for f in json_files]
    
    # Боковая панель с выбором файла
    with st.sidebar:
        
        # Радио баттон для выбора файла
        selected_file = st.radio(
            "Выберите файл:",
            options=file_options,
            index=len(file_options) - 1 if file_options else 0  # По умолчанию последний файл
        )
        
        # Полный путь к выбранному файлу
        selected_json_path = os.path.join(json_folder, selected_file)
        
        st.markdown("---")
        st.markdown("""
        ### 📝 Легенда
        - 🟢 **Выполнено** (>=75%)
        - 🟡 **В процессе** (50-74%)
        - 🔴 **Требует внимания** (<50%)
        """)
    
    # Загрузка данных из выбранного JSON файла
    try:
        tasks = load_tasks_from_json(selected_json_path)
        st.sidebar.success(f"✅ Загружено {len(tasks)} задач")
    except FileNotFoundError:
        st.error(f"Файл не найден: {selected_json_path}")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"Ошибка парсинга JSON: {e}")
        st.stop()
    except Exception as e:
        st.error("Ошибка загрузки данных: " + str(e))
        st.stop()
    
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
        project_roles = list(set(row["Проектная роль"] for row in table_data))
        selected_project_role = st.multiselect("Проектная роль:", project_roles, default=project_roles)
    
    # Применяем базовые фильтры
    filtered_by_base = [
        row for row in table_data
        if row["Смета"] in selected_estimate
        and row["Эпик"] in selected_epic
        and row["Проектная роль"] in selected_project_role
    ]
    
    # Получаем ключи задач, прошедших базовую фильтрацию
    filtered_task_keys = set(row["_task_key"] for row in filtered_by_base)
    
    # Получаем задачи, прошедшие базовую фильтрацию
    base_filtered_tasks = [task for task in tasks if task.issue_key in filtered_task_keys]
    
    # Получаем уникальные примитивы из отфильтрованных задач
    available_primitives = set()
    for task in base_filtered_tasks:
        task_primitives = get_task_primitives(task)
        available_primitives.update(task_primitives)
    
    # Применяем фильтр по примитивам
    filtered_data = filtered_by_base
    
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
                st.markdown("**Проектная роль:** " + row['Проектная роль'])
            
            with col2:
                st.markdown("**Статус:** " + row['Статус'])
                st.markdown("**Ремейнинг:** " + row['Ремейнинг'])
                st.progress(min(completion / 100, 1.0))
            
            st.markdown("---")
            
            # Отображаем полное примечание, если есть
            if row.get("_notes"):
                st.markdown("##### 📋 Примечание:")
                st.info(row["_notes"])
            
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
                "Проектная роль": row["Проектная роль"],
                "Задача": row["Задача"],
                "Статус": row["Статус"].split(" | ")[0],  # Только основной статус
                "Выполнение (%)": row["Выполнение (%)"],
                "Ремейнинг": row["Ремейнинг"]
            }
            for row in filtered_data
        ])
        
        # Стилизация таблицы с контрастными цветами
        def highlight_completion(val):
            if isinstance(val, (int, float)):
                if val >= 75:
                    return 'background-color: #155724; color: #ffffff'  # Тёмно-зелёный фон, белый текст
                elif val >= 50:
                    return 'background-color: #856404; color: #ffffff'  # Тёмно-жёлтый/коричневый фон, белый текст
                else:
                    return 'background-color: #721c24; color: #ffffff'  # Тёмно-красный фон, белый текст
            return ''
        
        styled_df = df_display.style.map(
            highlight_completion,
            subset=['Выполнение (%)']
        )
        
        st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Таблица статистики по примитивам
    st.markdown("---")
    st.subheader("📊 Статистика по примитивам")
    
    # Рассчитываем статистику по всем примитивам
    primitive_stats = calculate_primitive_stats_for_all(base_filtered_tasks)
    
    if primitive_stats:
        # Создаем DataFrame для отображения
        df_primitives = pd.DataFrame(primitive_stats)
        
        # Переименовываем столбцы для лучшего отображения
        df_primitives.columns = [
            'Примитив',
            'Кол-во задач',
            'Доля задач (%)',
            'Вес',
            'Выполненность',
            'Вклад в незавершенность (%)'
        ]
        
        # Сортируем по количеству задач (по убыванию)
        df_primitives = df_primitives.sort_values('Кол-во задач', ascending=False)
        
        # Отображаем таблицу
        st.dataframe(df_primitives, use_container_width=True)
    else:
        st.info("Нет данных о примитивах в отфильтрованных задачах")



if __name__ == "__main__":
    main()
