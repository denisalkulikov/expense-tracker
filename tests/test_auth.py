"""
Тесты авторизации: вход, выход, неверные credentials,
поведение неавторизованного клиента.
"""
import uuid
import pytest
from src.database import SupabaseDB

from conftest import TEST_URL, TEST_KEY


@pytest.fixture
def anon_db():
    """Клиент БД без авторизации"""
    return SupabaseDB(url=TEST_URL, key=TEST_KEY)


def test_sign_in_and_get_user(test_user):
    """После входа get_user возвращает пользователя с email"""
    user = test_user.get_user()
    assert user.user is not None
    assert "@" in user.user.email


def test_sign_in_with_wrong_password(anon_db):
    """Неверный пароль не должен логинить"""
    with pytest.raises(Exception):
        anon_db.sign_in("nonexistent@example.com", "totally-wrong-password")


def test_sign_in_with_wrong_email(anon_db):
    """Несуществующий email не должен логинить"""
    with pytest.raises(Exception):
        anon_db.sign_in(f"nobody-{uuid.uuid4().hex[:8]}@example.com", "any-password")


def test_unauthenticated_add_expense_raises(anon_db):
    """Без авторизации add_expense бросает исключение"""
    with pytest.raises(Exception, match="Not authenticated"):
        anon_db.add_expense("Тест", 100, "Other", "Unknown")


def test_unauthenticated_delete_expense_raises(anon_db):
    """Без авторизации delete_expense бросает исключение"""
    with pytest.raises(Exception, match="Not authenticated"):
        anon_db.delete_expense(1)


def test_unauthenticated_get_expenses_returns_empty(anon_db):
    """Без авторизации get_expenses возвращает пустой список"""
    assert anon_db.get_expenses() == []


def test_unauthenticated_get_budget_returns_none(anon_db):
    """Без авторизации get_budget возвращает None"""
    assert anon_db.get_budget(1, 2024) is None


def test_sign_out_clears_session(test_user):
    """
    После sign_out пользователь не должен быть доступен.
    ВАЖНО: это разрушает сессию session-scoped фикстуры test_user,
    поэтому тест помечен последним по смыслу, но pytest порядок не гарантирует.
    Используем отдельного пользователя, чтобы не сломать другие тесты.
    """
    email = f"test-logout-{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    db = SupabaseDB(url=TEST_URL, key=TEST_KEY)
    db.sign_up(email, password)
    db.sign_in(email, password)

    assert db.get_user().user is not None

    db.sign_out()

    # После sign_out get_user должен вернуть None или пустой user
    user = db.get_user()
    assert user is None or user.user is None