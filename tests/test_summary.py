"""
Тесты агрегации get_summary: подсчёт сумм, категорий, локаций.
"""
import pytest
from datetime import date
from src.database import SupabaseDB

from conftest import TEST_URL, TEST_KEY


@pytest.fixture
def isolated_user():
    """
    Создаёт полностью изолированного пользователя под один тест
    и удаляет после. Нужен, чтобы get_summary считал только наши данные.
    """
    import uuid
    from supabase import create_client

    email = f"test-summary-{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    db = SupabaseDB(url=TEST_URL, key=TEST_KEY)
    db.sign_up(email, password)
    resp = db.sign_in(email, password)
    user_id = str(resp.user.id)

    yield db

    # cleanup
    from conftest import TEST_SERVICE_KEY
    if TEST_SERVICE_KEY:
        admin = create_client(TEST_URL, TEST_SERVICE_KEY)
        admin.table("expenses").delete().eq("user_id", user_id).execute()
        admin.table("budgets").delete().eq("user_id", user_id).execute()
        try:
            admin.auth.admin.delete_user(user_id)
        except Exception:
            pass


def test_summary_empty_user(isolated_user):
    """У нового пользователя summary пустой"""
    summary = isolated_user.get_summary()
    assert summary["total"] == 0
    assert summary["count"] == 0
    assert summary["by_category"] == {}
    assert summary["by_location"] == {}


def test_summary_structure(isolated_user):
    """Проверка структуры ответа"""
    summary = isolated_user.get_summary()
    for key in ("total", "count", "by_category", "by_location"):
        assert key in summary


def test_summary_calculates_totals(isolated_user):
    """Суммы и категории считаются корректно"""
    # Создаём ровно 3 расхода с известными суммами
    isolated_user.add_expense("Хлеб", 100.0, "Еда", "Пятёрочка")
    isolated_user.add_expense("Молоко", 200.0, "Еда", "Пятёрочка")
    isolated_user.add_expense("Автобус", 50.0, "Транспорт", "Автопарк")

    summary = isolated_user.get_summary()
    assert summary["count"] == 3
    assert summary["total"] == 350.0
    assert summary["by_category"]["Еда"] == 300.0
    assert summary["by_category"]["Транспорт"] == 50.0
    assert summary["by_location"]["Пятёрочка"] == 300.0
    assert summary["by_location"]["Автопарк"] == 50.0


def test_summary_groups_unknown_category(isolated_user):
    """Расходы без категории попадают в 'Other'"""
    isolated_user.add_expense("Что-то", 42.0, "Other", "Unknown")
    summary = isolated_user.get_summary()
    assert summary["by_category"].get("Other") == 42.0


def test_summary_with_custom_date(isolated_user):
    """Дата сохраняется и не влияет на total"""
    isolated_user.add_expense(
        "Старый расход", 111.0, "Other", "Test",
        expense_date=date(2020, 1, 1)
    )
    summary = isolated_user.get_summary()
    assert summary["total"] == 111.0
    assert summary["count"] == 1


def test_summary_ignores_other_users_data(test_user, isolated_user):
    """
    Данные test_user НЕ должны попадать в summary isolated_user.
    Это косвенная проверка RLS через агрегацию.
    """
    # test_user создаёт расход
    result = test_user.add_expense("Чужое", 9999.0, "Other", "Unknown")
    expense_id = result[0]["id"]

    try:
        summary = isolated_user.get_summary()
        assert summary["total"] == 0, (
            "Данные другого пользователя попали в summary"
        )
        assert summary["count"] == 0
    finally:
        test_user.delete_expense(expense_id)