import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from database import SupabaseDB

st.set_page_config(page_title="Учёт расходов", layout="wide")

# ---------- Init DB ----------
if "db" not in st.session_state:
    st.session_state.db = SupabaseDB()
db = st.session_state.db

# ---------- Auth state ----------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Восстановление сессии из session_state (в рамках одной сессии браузера)
if not st.session_state.authenticated:
    if "access_token" in st.session_state and "refresh_token" in st.session_state:
        try:
            db.set_session(st.session_state.access_token, st.session_state.refresh_token)
            user = db.get_user()
            if user and user.user:
                st.session_state.authenticated = True
                st.session_state.user_email = user.user.email
        except Exception:
            # Токен протух или невалиден — чистим
            del st.session_state["access_token"]
            del st.session_state["refresh_token"]

# ==================== AUTH PAGE ====================
if not st.session_state.authenticated:
    st.title("🔐 Учёт расходов")

    tab1, tab2 = st.tabs(["Войти", "Регистрация"])

    with tab1:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Пароль", type="password")
            if st.form_submit_button("Войти"):
                try:
                    resp = db.sign_in(email, password)
                    if resp.session:
                        st.session_state.access_token = resp.session.access_token
                        st.session_state.refresh_token = resp.session.refresh_token
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.success("С возвращением!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Ошибка входа: {e}")

    with tab2:
        with st.form("register"):
            email = st.text_input("Email")
            password = st.text_input("Пароль", type="password")
            if st.form_submit_button("Создать аккаунт"):
                try:
                    db.sign_up(email, password)
                    st.success("Аккаунт создан! ВЫ можете войти.")
                except Exception as e:
                    st.error(f"Регистрация не удалась: {e}")

    st.stop()

# ==================== APP ====================
st.sidebar.header(f"👤 {st.session_state.user_email}")
if st.sidebar.button("Выйти"):
    db.sign_out()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ---------- Sidebar: Add + Budget ----------
with st.sidebar:
    st.header("➕ Добавить расход")
    with st.form("add_form"):
        desc = st.selectbox("Описание", [
            "Английский", "Водоснабжение", "Газ", "Гимнастика", "Домофон",
            "ЕИРЦ", "Занимательный русский", "Интернет", "Капитальный ремонт", "Квартплата",
            "Логика", "Отопление", "Подготовка", "Садик", "Экострой", "Электроэнергия"
        ])
        amount = st.number_input("Сумма", min_value=0.01, step=0.01)
        category = st.selectbox("Категория", ["Интернет", "Квартплата", "Образование"])
        location = st.selectbox("Локация", ["Кирова", "Юбилейная", "Карла Маркса", "Лицей", "Гимнастика"])
        expense_date = st.date_input("Дата", value=datetime.now().date())
        submitted = st.form_submit_button("Добавить")
        if submitted and desc and location:
            try:
                db.add_expense(desc, amount, category, location, expense_date=expense_date)
                st.success("Добавлено!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

    st.divider()
    st.header("💰 Бюджет")
    cm, cy = datetime.now().month, datetime.now().year
    b_val = st.number_input("Месячный бюджет", min_value=0.0, step=10.0, value=0.0)
    if st.button("Установить бюджет"):
        try:
            db.set_budget(cm, cy, b_val)
            st.success("Сохранено!")
        except Exception as e:
            st.error(f"Ошибка: {e}")

# ---------- Main Dashboard ----------
st.title("💰 Учёт расходов")

try:
    expenses = db.get_expenses()
except Exception as e:
    st.error(f"Ошибка загрузки: {e}")
    expenses = []

df = pd.DataFrame(expenses) if expenses else pd.DataFrame()

if not df.empty:
    summary = db.get_summary()
    budget = db.get_budget(cm, cy)
    budget_val = budget["amount"] if budget else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Всего расходов", f"₽{summary['total']:,.2f}")
    c2.metric("Транзакций", summary["count"])
    c3.metric("Категорий", len(summary["by_category"]))
    c4.metric("Локаций", len(summary["by_location"]))

    if budget_val > 0:
        remaining = budget_val - summary["total"]
        st.metric("Budget Remaining", f"₽{remaining:,.2f}", delta=f"of ₽{budget_val:,.2f}")
        if remaining < 0:
            st.error(f"⚠️ Exceeded by ₽{abs(remaining):,.2f}!")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("По категориям")
        cat_df = pd.DataFrame([{"cat": k, "amount": v} for k, v in summary["by_category"].items()])
        st.plotly_chart(px.pie(cat_df, values="amount", names="cat", hole=0.4), width='stretch')

    with col2:
        st.subheader("По локациям")
        loc_df = pd.DataFrame([{"loc": k, "amount": v} for k, v in summary["by_location"].items()])
        st.plotly_chart(px.bar(loc_df, x="loc", y="amount"), width='stretch')

    st.subheader("Динамика по месяцам")

    df["date"] = pd.to_datetime(df["date"])

    months_ru = {
        1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
        7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек"
    }

    monthly = (
        df.groupby([df["date"].dt.year.rename("year"), df["date"].dt.month.rename("month")])["amount"]
        .sum()
        .reset_index()
    )

    monthly["month_label"] = monthly["month"].map(months_ru)
    monthly["year_str"] = monthly["year"].astype(str)

    fig = px.bar(
        monthly,
        x="month_label",
        y="amount",
        color="year_str",
        barmode="group",
        text=monthly["amount"].round(2),
        labels={"month_label": "Месяц", "amount": "Сумма (₽)", "year_str": "Год"},
        category_orders={"month_label": ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
                                         "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]}
    )

    fig.update_traces(texttemplate='%{text:.2f} ₽', textposition='outside')
    fig.update_layout(
        xaxis_tickangle=0,
        legend_title_text="Год",
        height=450
    )

    st.plotly_chart(fig, width='stretch')

    st.subheader("История расходов")
    st.dataframe(df[["date", "description", "amount", "category", "location"]],
                 width='stretch', height=400)

    st.subheader("Управление")

    items_per_page = 10
    total_pages = max(1, (len(df) + items_per_page - 1) // items_per_page)
    page = st.number_input("Страница", min_value=1, max_value=total_pages, value=1, step=1)

    start = (page - 1) * items_per_page
    end = start + items_per_page
    page_df = df.iloc[start:end]

    for _, row in page_df.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1.5, 1.5, 1.5, 1])
        c1.write(str(row["date"])[:10])
        c2.write(row["description"])
        c3.write(f"₽{row['amount']:.2f}")
        c4.write(row["category"])
        c5.write(row["location"])
        if c6.button("🗑️", key=f"del_{row['id']}"):
            try:
                db.delete_expense(row["id"])
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")
else:
    st.info("Ещё нет расходов. Добавьте первый расход в боковом меню!")