"""
Тесты Row Level Security (RLS).
Проверяют, что пользователи видят только свои данные
и не могут получить доступ к чужим.
"""
import uuid
import pytest
from src.database import SupabaseDB
from supabase import create_client

from conftest import TEST_URL, TEST_KEY, TEST_SERVICE_KEY


@pytest.fixture
def second_user():
    """
    Создаёт второго пользователя с уникальным email.
    Возвращает авторизованный SupabaseDB и его user_id.
    После теста удаляет пользователя через service_role (если ключ есть).
    """
    email = f"test-second-{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    db = SupabaseDB(url=TEST_URL, key=TEST_KEY)
    db.sign_up(email, password)
    resp = db.sign_in(email, password)
    assert resp.session, "Не удалось войти вторым пользователем"

    user_id = str(resp.user.id)

    yield db, user_id

    # --- Cleanup: удаляем данные и самого пользователя ---
    if TEST_SERVICE_KEY:
        admin = create_client(TEST_URL, TEST_SERVICE_KEY)
        # Удаляем данные (на случай, если тест не убрал за собой)
        admin.table("expenses").delete().eq("user_id", user_id).execute()
        admin.table("budgets").delete().eq("user_id", user_id).execute()
        # Удаляем самого пользователя из auth
        try:
            admin.auth.admin.delete_user(user_id)
        except Exception:
            pass


def test_rls_user_cannot_see_other_expenses(test_user, second_user):
    """Второй пользователь НЕ должен видеть расходы первого"""
    db2, _ = second_user

    # Первый создаёт расход
    result = test_user.add_expense("Секретный расход", 12345.67, "Other", "Secret")
    expense_id = result[0]["id"]

    try:
        # Второй получает свой список — чужого расхода там быть не должно
        expenses = db2.get_expenses(limit=1000)
        ids = [e["id"] for e in expenses]
        assert expense_id not in ids, (
            "RLS нарушен: второй пользователь видит расход первого"
        )
    finally:
        test_user.delete_expense(expense_id)


def test_rls_user_cannot_delete_other_expense(test_user, second_user):
    """Второй пользователь НЕ может удалить чужой расход"""
    db2, _ = second_user

    result = test_user.add_expense("Не трогать!", 999, "Other", "Secret")
    expense_id = result[0]["id"]

    try:
        # Второй пытается удалить
        db2.delete_expense(expense_id)

        # Расход должен остаться у первого
        expenses = test_user.get_expenses(limit=1000)
        ids = [e["id"] for e in expenses]
        assert expense_id in ids, (
            "RLS нарушен: второй пользователь удалил чужой расход"
        )
    finally:
        test_user.delete_expense(expense_id)


def test_rls_user_cannot_see_other_budgets(test_user, second_user):
    """Второй пользователь НЕ должен видеть бюджет первого"""
    from datetime import datetime
    db2, _ = second_user

    month, year = datetime.now().month, datetime.now().year
    test_user.set_budget(month, year, 55555.55)

    # Второй пытается прочитать тот же месяц/год
    budget = db2.get_budget(month, year)
    assert budget is None, (
        "RLS нарушен: второй пользователь видит бюджет первого"
    )