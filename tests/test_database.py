import pytest
from datetime import datetime


def test_sign_in_and_get_user(test_user):
    """Проверяем, что тестовый пользователь авторизован"""
    user = test_user.get_user()
    assert user.user is not None
    assert "@" in user.user.email


def test_add_expense(test_user):
    """Создание расхода"""
    result = test_user.add_expense("Интернет", 700.50, "Интернет", "Юбилейная")
    assert len(result) == 1
    assert result[0]["description"] == "Интернет"
    assert result[0]["amount"] == 700.50
    assert result[0]["location"] == "Юбилейная"

    # Удаляем за собой
    test_user.delete_expense(result[0]["id"])


def test_get_expenses_returns_list(test_user, fresh_expense):
    """Получение списка расходов"""
    expenses = test_user.get_expenses()
    assert isinstance(expenses, list)
    assert len(expenses) >= 1
    # Проверяем, что наш тестовый расход есть в списке
    ids = [e["id"] for e in expenses]
    assert fresh_expense in ids


def test_delete_expense(test_user):
    """Удаление расхода"""
    result = test_user.add_expense("На удаление", 100, "Образование", "Лицей")
    expense_id = result[0]["id"]

    delete_result = test_user.delete_expense(expense_id)
    assert delete_result is not None

    # Проверяем, что удалился
    expenses = test_user.get_expenses(limit=1000)
    ids = [e["id"] for e in expenses]
    assert expense_id not in ids


def test_budget_crud(test_user):
    """Создание и чтение бюджета"""
    month, year = datetime.now().month, datetime.now().year

    test_user.set_budget(month, year, 15000.00)
    budget = test_user.get_budget(month, year)

    assert budget is not None
    assert budget["amount"] == 15000.00
    assert budget["month"] == month
    assert budget["year"] == year


def test_summary_calculation(test_user, fresh_expense):
    """Проверка агрегации в get_summary"""
    summary = test_user.get_summary()

    assert "total" in summary
    assert "count" in summary
    assert "by_category" in summary
    assert "by_location" in summary

    assert summary["count"] >= 1
    assert summary["total"] > 0
    assert "Квартплата" in summary["by_category"] or "Интернет" in summary["by_category"]