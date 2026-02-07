"""
Тестовый скрипт для демонстрации функциональности оценки выполнения задач.
"""

from app.utils.data.jira_csv_loader import (
    JiraTask, 
    CompletionEvaluation, 
    StepEvaluation
)
from app.services.completion.completion_service import (
    CompletionService,
    CompletionStatus
)


def create_sample_tasks() -> list[JiraTask]:
    """Создаёт примеры задач с декомпозицией и планом реализации."""
    
    # Задача 1: В процессе разработки
    task1 = JiraTask(
        issue_key="DI-101",
        issue_id=101,
        summary="Реализовать API для управления пользователями",
        status="In Progress",
        created="2024-01-15",
        updated="2024-01-20",
        description="Создать REST API для CRUD операций с пользователями",
        assignee="developer1",
        project_role=["Backend", "API"],
        decomposition=["backend_api_endpoint", "backend_business_logic", "backend_validation"],
        implementation_plan=[
            "Создать модель User в models/user.py",
            "Добавить миграцию для таблицы users",
            "Реализовать UserService с методами CRUD",
            "Создать эндпоинты GET/POST/PUT/DELETE в routers/users.py",
            "Добавить валидацию входящих данных",
            "Написать unit-тесты для UserService"
        ]
    )
    
    # Добавляем оценку выполнения для задачи 1
    task1.completion_evaluation = CompletionEvaluation(
        overall_completion_percentage=55.0,
        status_factor="Статус 'In Progress' указывает на активную разработку",
        steps_evaluation=[
            StepEvaluation(
                step_number=1,
                step_description="Создать модель User",
                is_completed=True,
                completion_percentage=100,
                weight=15,
                reasoning="Базовый шаг, выполнен первым"
            ),
            StepEvaluation(
                step_number=2,
                step_description="Добавить миграцию",
                is_completed=True,
                completion_percentage=100,
                weight=10,
                reasoning="Необходим для работы модели"
            ),
            StepEvaluation(
                step_number=3,
                step_description="Реализовать UserService",
                is_completed=True,
                completion_percentage=100,
                weight=25,
                reasoning="Основная бизнес-логика"
            ),
            StepEvaluation(
                step_number=4,
                step_description="Создать эндпоинты",
                is_completed=False,
                completion_percentage=50,
                weight=20,
                reasoning="Частично реализованы GET и POST"
            ),
            StepEvaluation(
                step_number=5,
                step_description="Добавить валидацию",
                is_completed=False,
                completion_percentage=0,
                weight=10,
                reasoning="Ещё не начато"
            ),
            StepEvaluation(
                step_number=6,
                step_description="Написать unit-тесты",
                is_completed=False,
                completion_percentage=0,
                weight=20,
                reasoning="Тесты пишутся после основного кода"
            )
        ],
        confidence="high",
        notes="Модель, миграция, сервис и GET эндпоинт готовы. PATCH эндпоинт на ревью, тесты ещё не начаты"
    )
    
    # Задача 2: На ревью
    task2 = JiraTask(
        issue_key="DI-102",
        issue_id=102,
        summary="Добавить авторизацию через JWT",
        status="Code Review",
        created="2024-01-10",
        updated="2024-01-22",
        description="Реализовать JWT-авторизацию для API",
        assignee="developer2",
        project_role=["Backend", "Auth"],
        decomposition=["backend_auth", "backend_validation"],
        implementation_plan=[
            "Настроить библиотеку PyJWT",
            "Создать сервис генерации токенов",
            "Реализовать middleware для проверки токенов",
            "Добавить эндпоинты login/logout",
            "Написать тесты для авторизации"
        ]
    )
    
    task2.completion_evaluation = CompletionEvaluation(
        overall_completion_percentage=85.0,
        status_factor="Статус 'Code Review' указывает на завершение разработки",
        steps_evaluation=[
            StepEvaluation(
                step_number=1,
                step_description="Настроить PyJWT",
                is_completed=True,
                completion_percentage=100,
                weight=10,
                reasoning="Конфигурация выполнена"
            ),
            StepEvaluation(
                step_number=2,
                step_description="Создать сервис токенов",
                is_completed=True,
                completion_percentage=100,
                weight=25,
                reasoning="Основная логика готова"
            ),
            StepEvaluation(
                step_number=3,
                step_description="Реализовать middleware",
                is_completed=True,
                completion_percentage=100,
                weight=25,
                reasoning="Middleware работает"
            ),
            StepEvaluation(
                step_number=4,
                step_description="Добавить эндпоинты",
                is_completed=True,
                completion_percentage=100,
                weight=20,
                reasoning="Все эндпоинты готовы"
            ),
            StepEvaluation(
                step_number=5,
                step_description="Написать тесты",
                is_completed=False,
                completion_percentage=25,
                weight=20,
                reasoning="Тесты частично написаны"
            )
        ],
        confidence="high",
        notes="Основная часть готова - модель, валидация, сервис, эндпоинты. Осталось завершить тесты"
    )
    
    # Задача 3: Только начата
    task3 = JiraTask(
        issue_key="DI-103",
        issue_id=103,
        summary="Создать UI для настроек профиля",
        status="To Do",
        created="2024-01-18",
        updated="2024-01-18",
        description="Разработать React-компоненты для страницы настроек",
        assignee="developer3",
        project_role=["Frontend", "UI"],
        decomposition=["frontend_ui_component_new", "frontend_state_management"],
        implementation_plan=[
            "Создать компонент ProfileSettings",
            "Добавить форму редактирования профиля",
            "Интегрировать с Redux store",
            "Подключить API для сохранения",
            "Добавить валидацию формы",
            "Написать компонентные тесты"
        ]
    )
    
    task3.completion_evaluation = CompletionEvaluation(
        overall_completion_percentage=10.0,
        status_factor="Статус 'To Do' указывает на начальную стадию",
        steps_evaluation=[
            StepEvaluation(
                step_number=1,
                step_description="Создать компонент ProfileSettings",
                is_completed=False,
                completion_percentage=50,
                weight=20,
                reasoning="Базовая структура создана"
            ),
            StepEvaluation(
                step_number=2,
                step_description="Добавить форму",
                is_completed=False,
                completion_percentage=0,
                weight=20,
                reasoning="Не начато"
            ),
            StepEvaluation(
                step_number=3,
                step_description="Интегрировать с Redux",
                is_completed=False,
                completion_percentage=0,
                weight=15,
                reasoning="Не начато"
            ),
            StepEvaluation(
                step_number=4,
                step_description="Подключить API",
                is_completed=False,
                completion_percentage=0,
                weight=15,
                reasoning="Не начато"
            ),
            StepEvaluation(
                step_number=5,
                step_description="Добавить валидацию",
                is_completed=False,
                completion_percentage=0,
                weight=15,
                reasoning="Не начато"
            ),
            StepEvaluation(
                step_number=6,
                step_description="Написать тесты",
                is_completed=False,
                completion_percentage=0,
                weight=15,
                reasoning="Не начато"
            )
        ],
        confidence="medium",
        notes="Только созданы файлы. Основная разработка ещё не начата - модель, UI и логика не реализованы"
    )
    
    return [task1, task2, task3]


def main():
    """Основная функция демонстрации."""
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ ОЦЕНКИ ВЫПОЛНЕНИЯ ЗАДАЧ")
    print("=" * 60)
    
    # Создаём примеры задач
    tasks = create_sample_tasks()
    
    # Инициализируем сервис
    service = CompletionService()
    
    # 1. Генерируем отчёты по каждой задаче
    print("\n--- Отчёты по отдельным задачам ---\n")
    
    for task in tasks:
        report = service.generate_task_report(task)
        if report:
            print(f"Задача: {report.issue_key}")
            print(f"  Название: {report.summary}")
            print(f"  Статус Jira: {report.status}")
            print(f"  Процент выполнения: {report.completion_percentage}%")
            print(f"  Статус выполнения: {report.completion_status.value}")
            print(f"  Шагов выполнено: {report.steps_completed}/{report.steps_total}")
            print(f"  Уверенность оценки: {report.confidence}")
            
            if report.bottleneck_steps:
                print(f"  Блокирующие шаги:")
                for step in report.bottleneck_steps:
                    print(f"    - {step}")
            
            if report.notes:
                print(f"  Заметки: {report.notes}")
            print()
    
    # 2. Генерируем сводный отчёт по проекту
    print("\n--- Сводный отчёт по проекту ---\n")
    
    project_report = service.generate_project_report(tasks)
    print(service.format_report_as_text(project_report))
    
    # 3. Получаем приоритетные задачи
    print("\n--- Приоритетные задачи ---\n")
    
    priority_tasks = service.get_priority_tasks(tasks, limit=3)
    for issue_key, completion, bottlenecks in priority_tasks:
        print(f"  {issue_key}: {completion}% выполнено")
        if bottlenecks:
            print(f"    Блокирующие шаги: {len(bottlenecks)}")
    
    # 4. Оценка оставшейся работы
    print("\n--- Оценка оставшейся работы ---\n")
    
    for task in tasks:
        effort = service.estimate_remaining_effort(task, hours_per_step=3.0)
        if effort:
            print(f"Задача: {effort['issue_key']}")
            print(f"  Текущий прогресс: {effort['current_completion']}%")
            print(f"  Оставшееся время: ~{effort['total_remaining_hours']} часов")
            print(f"  Уверенность: {effort['confidence']}")
            print()
    
    # 5. Демонстрация расчёта взвешенного процента
    print("\n--- Демонстрация расчёта взвешенного процента ---\n")
    
    task = tasks[0]  # DI-101
    if task.completion_evaluation:
        steps = task.completion_evaluation.steps_evaluation
        
        print(f"Задача: {task.issue_key}")
        print(f"Формула: completion = Σ (step_completion * step_weight / 100)")
        print()
        
        total = 0
        for step in steps:
            contribution = step.weighted_completion()
            total += contribution
            print(f"  Шаг {step.step_number}: {step.completion_percentage}% × {step.weight}% = {contribution:.1f}%")
        
        print(f"\n  Итого: {total:.1f}%")
        print(f"  Сохранённое значение: {task.completion_evaluation.overall_completion_percentage}%")


if __name__ == "__main__":
    main()
