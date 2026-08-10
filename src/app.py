import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from database import SupabaseDB

st.set_page_config(page_title="Expense Tracker", layout="wide")

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
    st.title("🔐 Expense Tracker")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                try:
                    resp = db.sign_in(email, password)
                    if resp.session:
                        st.session_state.access_token = resp.session.access_token
                        st.session_state.refresh_token = resp.session.refresh_token
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.success("Welcome back!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    with tab2:
        with st.form("register"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Create account"):
                try:
                    db.sign_up(email, password)
                    st.success("Account created! You can log in now.")
                except Exception as e:
                    st.error(f"Registration failed: {e}")

    st.stop()

# ==================== APP ====================
st.sidebar.header(f"👤 {st.session_state.user_email}")
if st.sidebar.button("Logout"):
    db.sign_out()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ---------- Sidebar: Add + Budget ----------
with st.sidebar:
    st.header("➕ Add Expense")
    with st.form("add_form"):
        desc = st.selectbox("Description", [
            "Английский", "Водоснабжение", "Газ", "Гимнастика", "Домофон",
            "ЕИРЦ", "Занимательный русский", "Интернет", "Капитальный ремонт", "Квартплата",
            "Логика", "Отопление", "Подготовка", "Садик", "Экострой", "Электроэнергия"
        ])
        amount = st.number_input("Amount", min_value=0.01, step=0.01)
        category = st.selectbox("Category", ["Интернет", "Квартплата", "Образование"])
        location = st.selectbox("Location", ["Кирова", "Юбилейная", "Карла Маркса", "Лицей", "Гимнастика"])
        expense_date = st.date_input("Date", value=datetime.now().date())
        submitted = st.form_submit_button("Add")
        if submitted and desc and location:
            try:
                db.add_expense(desc, amount, category, location, expense_date=expense_date)
                st.success("Added!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    st.header("💰 Budget")
    cm, cy = datetime.now().month, datetime.now().year
    b_val = st.number_input("Monthly budget", min_value=0.0, step=10.0, value=0.0)
    if st.button("Set Budget"):
        try:
            db.set_budget(cm, cy, b_val)
            st.success("Saved!")
        except Exception as e:
            st.error(f"Error: {e}")

# ---------- Main Dashboard ----------
st.title("💰 Expense Tracker")

try:
    expenses = db.get_expenses()
except Exception as e:
    st.error(f"Failed to load: {e}")
    expenses = []

df = pd.DataFrame(expenses) if expenses else pd.DataFrame()

if not df.empty:
    summary = db.get_summary()
    budget = db.get_budget(cm, cy)
    budget_val = budget["amount"] if budget else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", f"₽{summary['total']:,.2f}")
    c2.metric("Transactions", summary["count"])
    c3.metric("Categories", len(summary["by_category"]))
    c4.metric("Locations", len(summary["by_location"]))

    if budget_val > 0:
        remaining = budget_val - summary["total"]
        st.metric("Budget Remaining", f"₽{remaining:,.2f}", delta=f"of ₽{budget_val:,.2f}")
        if remaining < 0:
            st.error(f"⚠️ Exceeded by ₽{abs(remaining):,.2f}!")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("By Category")
        cat_df = pd.DataFrame([{"cat": k, "amount": v} for k, v in summary["by_category"].items()])
        st.plotly_chart(px.pie(cat_df, values="amount", names="cat", hole=0.4), width='stretch')

    with col2:
        st.subheader("By Location")
        loc_df = pd.DataFrame([{"loc": k, "amount": v} for k, v in summary["by_location"].items()])
        st.plotly_chart(px.bar(loc_df, x="loc", y="amount"), width='stretch')

    st.subheader("Trend")
    df["date"] = pd.to_datetime(df["date"])
    daily = df.groupby("date")["amount"].sum().reset_index()
    st.plotly_chart(px.line(daily, x="date", y="amount", markers=True), width='stretch')

    st.subheader("History")
    st.dataframe(df[["date", "description", "amount", "category", "location"]].head(50), width='stretch')

    st.subheader("Manage")
    for _, row in df.head(10).iterrows():
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
                st.error(f"Error: {e}")
else:
    st.info("No expenses yet. Add your first one in the sidebar!")