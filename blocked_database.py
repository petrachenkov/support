import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict


class BlockedDatabase:
    def __init__(self, db_name: str = "blocked_users.db"):
        self.db_name = db_name
        self.conn = None
        self.init_db()

    def init_db(self):
        """Инициализация базы данных заблокированных пользователей"""
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Создаем таблицу заблокированных пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                blocked_by INTEGER NOT NULL,
                blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
        ''')

        self.conn.commit()

    def block_user(self, user_id: int, blocked_by: int, username: Optional[str] = None,
                   first_name: Optional[str] = None, last_name: Optional[str] = None,
                   reason: Optional[str] = None) -> bool:
        """Блокировка пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO blocked_users 
                (user_id, username, first_name, last_name, blocked_by, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, blocked_by, reason))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при блокировке пользователя: {e}")
            return False

    def unblock_user(self, user_id: int) -> bool:
        """Разблокировка пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM blocked_users WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Ошибка при разблокировке пользователя: {e}")
            return False

    def is_user_blocked(self, user_id: int) -> bool:
        """Проверка, заблокирован ли пользователь"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id FROM blocked_users WHERE user_id = ?', (user_id,))
        return cursor.fetchone() is not None

    def get_blocked_users(self) -> List[Dict]:
        """Получение списка всех заблокированных пользователей"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM blocked_users 
            ORDER BY blocked_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_blocked_user_info(self, user_id: int) -> Optional[Dict]:
        """Получение информации о блокировке пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM blocked_users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()