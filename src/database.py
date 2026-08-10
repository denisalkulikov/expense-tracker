from supabase import create_client, Client
from datetime import date
from typing import List, Optional
import streamlit as st


class SupabaseDB:
    def __init__(self):
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        self.client: Client = create_client(url, key)

    # ---------- Auth ----------
    def sign_up(self, email: str, password: str):
        return self.client.auth.sign_up({"email": email, "password": password})

    def sign_in(self, email: str, password: str):
        return self.client.auth.sign_in_with_password({"email": email, "password": password})

    def sign_out(self):
        return self.client.auth.sign_out()

    def get_user(self):
        return self.client.auth.get_user()

    # ---------- Expenses ----------
    def add_expense(self, description: str, amount: float, category: str, location: str, expense_date: Optional[date] = None):
        user = self.get_user()
        if not user or not user.user:
            raise Exception("Not authenticated")

        data = {
            "description": description,
            "amount": amount,
            "category": category,
            "location": location,
            "date": str(expense_date) if expense_date else str(date.today()),
            "user_id": str(user.user.id),
        }
        return self.client.table("expenses").insert(data).execute().data

    def get_expenses(self, limit: int = 500) -> List[dict]:
        user = self.get_user()
        if not user or not user.user:
            return []

        return (
            self.client.table("expenses")
            .select("*")
            .eq("user_id", str(user.user.id))
            .order("date", desc=True)
            .limit(limit)
            .execute()
            .data
        )

    def delete_expense(self, expense_id: int):
        user = self.get_user()
        if not user or not user.user:
            raise Exception("Not authenticated")

        return (
            self.client.table("expenses")
            .delete()
            .eq("id", expense_id)
            .eq("user_id", str(user.user.id))
            .execute()
            .data
        )

    def get_summary(self) -> dict:
        expenses = self.get_expenses(limit=10000)
        total = sum(e["amount"] for e in expenses)
        by_category = {}
        by_location = {}
        for e in expenses:
            cat = e.get("category", "Other")
            by_category[cat] = by_category.get(cat, 0) + e["amount"]
            loc = e.get("location", "Unknown")
            by_location[loc] = by_location.get(loc, 0) + e["amount"]

        return {
            "total": total,
            "count": len(expenses),
            "by_category": by_category,
            "by_location": by_location,
        }

    # ---------- Budgets ----------
    def set_budget(self, month: int, year: int, amount: float):
        user = self.get_user()
        if not user or not user.user:
            raise Exception("Not authenticated")

        data = {
            "month": month,
            "year": year,
            "amount": amount,
            "user_id": str(user.user.id),
        }
        return self.client.table("budgets").upsert(data).execute().data

    def get_budget(self, month: int, year: int) -> Optional[dict]:
        user = self.get_user()
        if not user or not user.user:
            return None

        data = (
            self.client.table("budgets")
            .select("*")
            .eq("month", month)
            .eq("year", year)
            .eq("user_id", str(user.user.id))
            .execute()
            .data
        )
        return data[0] if data else None