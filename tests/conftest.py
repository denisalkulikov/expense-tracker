import os
import uuid
import pytest
from dotenv import load_dotenv
from src.database import SupabaseDB

# Загружаем переменные из .env
load_dotenv()

# --- Конфигурация тестового окружения ---
TEST_URL = os.getenv("SUPABASE_URL_TEST")
TEST_KEY = os.getenv("SUPABASE_KEY_TEST")
TEST_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY_TEST")

# Уникальный email для каждого запуска, чтобы не конфликтовать
TEST_EMAIL = f"test-{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "TestPassword123!"


@pytest.fixture(scope="session")
def test_db_raw():
    """Клиент БД без авторизации (для регистрации)"""
    if not TEST_URL or not TEST_KEY:
        pytest.skip("Тестовые credentials не найдены. Установите SUPABASE_URL_TEST и SUPABASE_KEY_TEST")
    return SupabaseDB(url=TEST_URL, key=TEST_KEY)


@pytest.fixture(scope="session")
def test_user(test_db_raw: SupabaseDB):
    """Создает тестового пользователя, возвращает (db, email, password)"""
    db = test_db_raw

    # Регистрация
    try:
        db.sign_up(TEST_EMAIL, TEST_PASSWORD)
    except Exception:
        pass  # Может уже существовать

    # Вход
    resp = db.sign_in(TEST_EMAIL, TEST_PASSWORD)
    assert resp.session, "Не удалось войти в тестовый аккаунт"

    yield db

    # --- Cleanup после всех тестов ---
    # Удаляем все расходы этого пользователя через service_role (если есть ключ)
    if TEST_SERVICE_KEY:
        from supabase import create_client
        admin_client = create_client(TEST_URL, TEST_SERVICE_KEY)
        user = db.get_user()
        if user and user.user:
            admin_client.table("expenses").delete().eq("user_id", str(user.user.id)).execute()
            admin_client.table("budgets").delete().eq("user_id", str(user.user.id)).execute()


@pytest.fixture
def fresh_expense(test_user: SupabaseDB):
    """Создает один расход, возвращает его ID. Удаляет после теста."""
    db = test_user
    result = db.add_expense("Тестовый расход", 999.99, "Квартплата", "Кирова")
    expense_id = result[0]["id"]
    yield expense_id
    try:
        db.delete_expense(expense_id)
    except Exception:
        pass