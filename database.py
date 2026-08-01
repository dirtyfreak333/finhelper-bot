import sqlite3

DB_NAME = "finhelper.db"


def init_db():
    """Створює таблиці в базі даних, якщо їх ще немає"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            currency TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            created_at TEXT
        )
    """)
    try:
     cursor.execute("ALTER TABLE expenses ADD COLUMN type TEXT DEFAULT 'expense'")
    except sqlite3.OperationalError:
     pass

    try:
     cursor.execute("ALTER TABLE users ADD COLUMN budget REAL DEFAULT 0")
    except sqlite3.OperationalError:
     pass

    conn.commit()
    conn.close()

def save_user_currency(user_id, currency):
    """Зберігає валюту користувача (або оновлює, якщо вже є)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, currency) VALUES (?, ?)",
        (user_id, currency)
    )
    conn.commit()
    conn.close()

def get_user_currency(user_id):
    """Повертає валюту користувача, або None, якщо ще не обрана"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT currency FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None
    
def add_expense(user_id, amount, category):
    """Зберігає одну витрату в базу даних"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (user_id, amount, category, created_at) VALUES (?, ?, ?, datetime('now'))",
        (user_id, amount, category)
    )
    conn.commit()
    conn.close()

def add_income(user_id, amount):
    """Зберігає одне надходження в базу даних"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (user_id, amount, category, type, created_at) VALUES (?, ?, NULL, 'income', datetime('now'))",
        (user_id, amount)
    )
    conn.commit()
    conn.close()

def delete_last_entry(user_id):
    """Видаляє останній доданий запис (витрату або надходження)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM expenses WHERE id = ?", (row[0],))
        conn.commit()
    conn.close()
    return row is not None

def get_all_income(user_id):
    """Повертає список усіх надходжень користувача"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT amount, created_at FROM expenses WHERE user_id = ? AND type = 'income'",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows 

def get_all_expenses(user_id):
    """Повертає список усіх витрат користувача (без надходжень)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT amount, category, created_at FROM expenses WHERE user_id = ? AND type = 'expense'",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_expenses_since(user_id, since_date):
    """Повертає витрати користувача починаючи з певної дати"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT amount, category, created_at FROM expenses WHERE user_id = ? AND type = 'expense' AND created_at >= ?",
        (user_id, since_date)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_income_since(user_id, since_date):
    """Повертає надходження користувача починаючи з певної дати"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT amount, created_at FROM expenses WHERE user_id = ? AND type = 'income' AND created_at >= ?",
        (user_id, since_date)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def set_budget(user_id, budget):
    """Зберігає місячний бюджет користувача"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET budget = ? WHERE user_id = ?", (budget, user_id))
    conn.commit()
    conn.close()


def get_budget(user_id):
    """Повертає місячний бюджет користувача"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT budget FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def get_recent_entries(user_id, limit=10):
    """Повертає останні N записів користувача (і витрати, і надходження) з номером id"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, amount, category, type, created_at FROM expenses "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_entry_by_id(entry_id, user_id):
    """Видаляє конкретний запис за його id (тільки якщо він належить цьому користувачу)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (entry_id, user_id)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted