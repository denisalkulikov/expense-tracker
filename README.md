# 💰 Expense Tracker

Fullstack-приложение для учёта личных расходов с авторизацией, визуализацией и бюджетированием. Работает в браузере и на телефоне.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.61%2B-ff4b4b)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ecf8e)

---

## ✨ Функционал

- 🔐 **Регистрация и вход** через Supabase Auth (email + password)
- 💵 **Добавление расходов** с описанием, суммой, категорией, локацией и датой
- 📊 **Дашборд** с метриками, круговой диаграммой по категориям и столбчатой по локациям
- 📈 **Динамика расходов** по дням
- 🎯 **Бюджет на месяц** с отслеживанием остатка и предупреждением о превышении
- 🗑️ **Удаление записей**
- 🔒 **RLS** — каждый пользователь видит только свои данные

---

## 🏗️ Архитектура
```
┌─────────────┐      HTTPS/REST       ┌──────────────┐      SQL       ┌─────────────┐
│  Streamlit  │  ◄────────────────►   │   Supabase   │  ◄──────────►  │  PostgreSQL │
│   (GUI)     │                       │   (Auth+API) │                │   (RLS)     │
└─────────────┘                       └──────────────┘                └─────────────┘
```
---

## 🛠️ Стек

| Компонент | Технология             |
|-----------|------------------------|
| Frontend | Streamlit              |
| Backend/API | Supabase (REST + Auth) |
| База данных | PostgreSQL (Supabase)  |
| Визуализация | Plotly                 |
| Управление зависимостями | uv                     |
| Язык | Python 3.13+           |

---

## 📁 Структура проекта
```
expense-tracker/
├── .streamlit/
│   └── secrets.toml          # Локальные секреты (не коммитить!)
├── src/
│   ├── app.py                # Точка входа Streamlit
│   └── database.py           # Слой работы с Supabase
├── pyproject.toml            # Зависимости проекта
├── uv.lock                   # Lock-файл (коммитить!)
├── .gitignore
└── README.md
```

---

## ⚙️ Локальный запуск

### 1. Клонирование

```bash
git clone https://github.com/denisalkulikov/expense-tracker.git
cd expense-tracker
```

### 2. Установка зависимостей (uv)
```bash
uv sync
```

### 3. Настройка секретов
Создать файл .streamlit/secrets.toml:
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```
>Ключи берутся из Supabase Dashboard → Project Settings → API.

### 4. Запуск
```bash
uv run streamlit run src/app.py
```
Приложение откроется по адресу http://localhost:8501.

---

## 🌐 Деплой на Streamlit Cloud

### 1. Запушить репозиторий на GitHub (без .streamlit/secrets.toml)

### 2. Перейти на share.streamlit.io
### 3. Подключить репозиторий
### 4. В Settings → Secrets добавить:
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```
### 5. В Advanced settings указать Main file path: src/app.py
### 6. Нажать Deploy

---

## 🗄️ Настройка Supabase

### Создание таблиц
В SQL Editor выполнить:
```sql
create table expenses (
    id bigint generated always as identity primary key,
    created_at timestamptz default now(),
    description text not null,
    amount double precision not null check (amount > 0),
    category text default 'Other',
    location text not null default 'Unknown',
    date date default current_date,
    user_id uuid references auth.users(id)
);

create table budgets (
    id bigint generated always as identity primary key,
    month int not null check (month between 1 and 12),
    year int not null,
    amount double precision not null check (amount > 0),
    user_id uuid references auth.users(id),
    unique(month, year, user_id)
);

-- RLS
alter table expenses enable row level security;
alter table budgets enable row level security;

create policy "Users own expenses"
  on expenses for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users own budgets"
  on budgets for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
```

### Отключение подтверждения email (для теста)
```
Authentication → Providers → Email → Confirm email = OFF
```

---

## 📝 TODO / Идеи для развития
* [ ] Экспорт данных в CSV
* [ ] Редактирование существующих записей
* [ ] Фильтр по диапазону дат
* [ ] Push-уведомления при превышении бюджета

---

## 📄 Лицензия
MIT [License](https://github.com/denisalkulikov/expense-tracker/blob/master/LICENSE)

---

## 👨‍💻 Автор
Денис Куликов