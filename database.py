import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict
from models import Ticket, TicketStatus


class Database:
    def __init__(self, db_name: str = "tickets.db"):
        self.db_name = db_name
        self.conn = None
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Создаем таблицу заявок с колонками для оценок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                room TEXT NOT NULL,
                problem TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_by TEXT,
                closed_at TIMESTAMP,
                admin_response TEXT,
                rating INTEGER,
                feedback TEXT
            )
        ''')

        # Создаем индекс для быстрого поиска по user_id
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_id ON tickets (user_id)
        ''')

        # Создаем индекс для быстрого поиска по статусу
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status ON tickets (status)
        ''')

        # Создаем индекс для сортировки по дате создания
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON tickets (created_at)
        ''')

        # Создаем индекс для оценок
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_rating ON tickets (rating)
        ''')

        self.conn.commit()
        logging.info("База данных инициализирована")

    def add_ticket(self, user_id: int, full_name: str, room: str, problem: str) -> int:
        """Добавление новой заявки"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO tickets (user_id, full_name, room, problem, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, full_name, room, problem, TicketStatus.OPEN.value))
            self.conn.commit()
            ticket_id = cursor.lastrowid
            logging.info(f"Добавлена новая заявка #{ticket_id} от пользователя {user_id}")
            return ticket_id
        except Exception as e:
            logging.error(f"Ошибка при добавлении заявки: {e}")
            self.conn.rollback()
            raise

    def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        """Получение заявки по ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_ticket(row)
            return None
        except Exception as e:
            logging.error(f"Ошибка при получении заявки #{ticket_id}: {e}")
            return None

    def update_ticket_status(self, ticket_id: int, status: TicketStatus,
                             closed_by: Optional[str] = None, response: Optional[str] = None):
        """Обновление статуса заявки"""
        try:
            cursor = self.conn.cursor()

            if status == TicketStatus.CLOSED:
                cursor.execute('''
                    UPDATE tickets 
                    SET status = ?, closed_by = ?, closed_at = CURRENT_TIMESTAMP, admin_response = ?
                    WHERE id = ?
                ''', (status.value, closed_by, response, ticket_id))
            else:
                cursor.execute('''
                    UPDATE tickets 
                    SET status = ?, admin_response = ?
                    WHERE id = ?
                ''', (status.value, response, ticket_id))

            self.conn.commit()
            logging.info(f"Заявка #{ticket_id} обновлена: статус {status.value}")
        except Exception as e:
            logging.error(f"Ошибка при обновлении заявки #{ticket_id}: {e}")
            self.conn.rollback()
            raise

    def update_ticket_rating(self, ticket_id: int, rating: int, feedback: Optional[str] = None):
        """Обновление оценки заявки"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE tickets 
                SET rating = ?, feedback = ?
                WHERE id = ?
            ''', (rating, feedback, ticket_id))

            self.conn.commit()
            logging.info(f"Заявка #{ticket_id} оценена на {rating} звезд")
            return True
        except Exception as e:
            logging.error(f"Ошибка при обновлении оценки заявки #{ticket_id}: {e}")
            self.conn.rollback()
            return False

    def get_open_tickets(self) -> List[Dict]:
        """Получение всех открытых заявок (статус OPEN)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM tickets 
                WHERE status = ? 
                ORDER BY created_at DESC
            ''', (TicketStatus.OPEN.value,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Ошибка при получении открытых заявок: {e}")
            return []

    def get_in_progress_tickets(self) -> List[Dict]:
        """Получение всех заявок в работе (статус IN_PROGRESS)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM tickets 
                WHERE status = ? 
                ORDER BY created_at DESC
            ''', (TicketStatus.IN_PROGRESS.value,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Ошибка при получении заявок в работе: {e}")
            return []

    def get_closed_tickets(self) -> List[Dict]:
        """Получение всех закрытых заявок (статус CLOSED)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM tickets 
                WHERE status = ? 
                ORDER BY closed_at DESC
            ''', (TicketStatus.CLOSED.value,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Ошибка при получении закрытых заявок: {e}")
            return []

    def get_user_tickets(self, user_id: int) -> List[Dict]:
        """Получение заявок пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM tickets 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Ошибка при получении заявок пользователя {user_id}: {e}")
            return []

    def get_rated_tickets(self, limit: int = 10) -> List[Dict]:
        """Получение заявок с оценками"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM tickets 
                WHERE rating IS NOT NULL 
                ORDER BY closed_at DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Ошибка при получении заявок с оценками: {e}")
            return []

    def get_rating_stats(self) -> Dict:
        """Получение статистики оценок"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT 
                    AVG(rating) as avg_rating,
                    COUNT(*) as total_ratings,
                    COUNT(CASE WHEN rating = 5 THEN 1 END) as five_stars,
                    COUNT(CASE WHEN rating = 4 THEN 1 END) as four_stars,
                    COUNT(CASE WHEN rating = 3 THEN 1 END) as three_stars,
                    COUNT(CASE WHEN rating = 2 THEN 1 END) as two_stars,
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as one_stars
                FROM tickets 
                WHERE rating IS NOT NULL
            ''')
            result = cursor.fetchone()
            return dict(result) if result else {}
        except Exception as e:
            logging.error(f"Ошибка при получении статистики оценок: {e}")
            return {}

    def get_all_tickets(self) -> List[Dict]:
        """Получение всех заявок"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM tickets ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Ошибка при получении всех заявок: {e}")
            return []

    def get_tickets_stats(self) -> Dict:
        """Получение статистики по заявкам"""
        try:
            cursor = self.conn.cursor()

            # Общее количество заявок
            cursor.execute("SELECT COUNT(*) FROM tickets")
            total = cursor.fetchone()[0]

            # Заявки по статусам
            cursor.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
            status_stats = {row[0]: row[1] for row in cursor.fetchall()}

            # Заявки за сегодня
            cursor.execute("SELECT COUNT(*) FROM tickets WHERE DATE(created_at) = DATE('now')")
            today = cursor.fetchone()[0]

            return {
                'total': total,
                'open': status_stats.get('open', 0),
                'in_progress': status_stats.get('in_progress', 0),
                'closed': status_stats.get('closed', 0),
                'today': today
            }
        except Exception as e:
            logging.error(f"Ошибка при получении статистики: {e}")
            return {
                'total': 0,
                'open': 0,
                'in_progress': 0,
                'closed': 0,
                'today': 0
            }

    def _row_to_ticket(self, row) -> Ticket:
        """Преобразование строки базы данных в объект Ticket"""
        try:
            created_at = datetime.fromisoformat(row['created_at']) if row['created_at'] else None
            closed_at = datetime.fromisoformat(row['closed_at']) if row['closed_at'] else None

            return Ticket(
                id=row['id'],
                user_id=row['user_id'],
                full_name=row['full_name'],
                room=row['room'],
                problem=row['problem'],
                status=TicketStatus(row['status']),
                created_at=created_at,
                closed_by=row['closed_by'],
                closed_at=closed_at,
                admin_response=row['admin_response'],
                rating=row['rating'],
                feedback=row['feedback']
            )
        except Exception as e:
            logging.error(f"Ошибка преобразования строки в объект Ticket: {e}")
            raise

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
            logging.info("Соединение с базой данных закрыто")

    def __del__(self):
        """Деструктор - автоматическое закрытие соединения"""
        self.close()