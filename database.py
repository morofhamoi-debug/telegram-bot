import sqlite3
from datetime import datetime

DB_NAME = "bot_database.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблица пользователей (общая информация)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT
        )
    """)
    
    # Таблица привязки пользователя к конкретной группе (раздельный XP, уровни, победы)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            user_id INTEGER,
            chat_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            win_streak INTEGER DEFAULT 0,
            max_win_streak INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, chat_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    
    # Таблица предупреждений (варнов)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id INTEGER,
            moderator_id INTEGER,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица антистикеров (пользователи, которым запрещены стикеры в конкретном чате)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anti_sticker (
            user_id INTEGER,
            chat_id INTEGER,
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    
    conn.commit()
    conn.close()

def register_user(user_id: int, username: str, full_name: str, chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Сохраняем или обновляем пользователя
    cursor.execute("""
        INSERT INTO users (user_id, username, full_name) 
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
            username = excluded.username,
            full_name = excluded.full_name
    """, (user_id, username, full_name))
    
    # Инициализируем запись участника в конкретной группе, если её еще нет
    cursor.execute("""
        INSERT OR IGNORE INTO group_members (user_id, chat_id) 
        VALUES (?, ?)
    """, (user_id, chat_id))
    
    conn.commit()
    conn.close()
