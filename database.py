import sqlite3
from config import database_path

def init_db():
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            address TEXT NOT NULL,
            private_key TEXT NOT NULL,
            balance REAL DEFAULT 0,
            available_balance REAL DEFAULT 0,
            frozen_balance REAL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recharge_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed INTEGER DEFAULT 0,
            UNIQUE(user_id, amount, timestamp)
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, address, private_key):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (user_id, address, private_key) VALUES (?, ?, ?)', (user_id, address, private_key))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_balance(user_id, balance):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance=? WHERE user_id=?', (balance, user_id))
    conn.commit()
    conn.close()

def update_available_balance(user_id, amount):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET available_balance = available_balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

def add_recharge_record(user_id, amount):
    """添加一条新的充值记录"""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO recharge_records (user_id, amount, processed) VALUES (?, ?, 0)", 
        (user_id, amount)
    )
    conn.commit()
    conn.close()

def mark_recharges_processed(user_id):
    """标记用户的充值记录为已处理"""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE recharge_records SET processed = 1 WHERE user_id = ? AND processed = 0", 
        (user_id,)
    )
    conn.commit()
    conn.close()

def get_unprocessed_recharges(user_id):
    """获取用户未处理的充值记录"""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recharge_records WHERE user_id = ? AND processed = 0", (user_id,))
    recharges = cursor.fetchall()
    conn.close()
    return recharges

if __name__ == '__main__':
    init_db()
