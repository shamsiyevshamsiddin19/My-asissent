import sqlite3
import logging
from typing import List, Tuple, Optional
from config import DATABASE_FILE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.init_database()
    
    def init_database(self):
        """Database jadvallarini yaratish"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            # Foydalanuvchilar jadvali
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT
                )
            ''')
            
            # Kanallar jadvali
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    channel_id TEXT,
                    channel_name TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Rejalar jadvali
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    channel_id TEXT,
                    message TEXT,
                    time TEXT,
                    with_date INTEGER DEFAULT 0,
                    start_date TEXT,
                    day_count INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
            logger.info("Database jadvallari yaratildi")
    
    def add_user(self, user_id: int, username: str = None):
        """Foydalanuvchi qo'shish"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)',
                (user_id, username)
            )
            conn.commit()
    
    def add_channel(self, user_id: int, channel_id: str, channel_name: str):
        """Kanal qo'shish"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO channels (user_id, channel_id, channel_name) VALUES (?, ?, ?)',
                (user_id, channel_id, channel_name)
            )
            conn.commit()
    
    def get_user_channels(self, user_id: int) -> List[Tuple[str, str]]:
        """Foydalanuvchining kanallarini olish"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT channel_id, channel_name FROM channels WHERE user_id = ?',
                (user_id,)
            )
            return cursor.fetchall()
    
    def add_schedule(self, user_id: int, channel_id: str, message: str, 
                    time: str, with_date: bool, start_date: str) -> int:
        """Reja qo'shish"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO schedules (user_id, channel_id, message, time, with_date, start_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, channel_id, message, time, int(with_date), start_date))
            conn.commit()
            return cursor.lastrowid
    
    def get_user_schedules(self, user_id: int) -> List[Tuple]:
        """Foydalanuvchining rejalarini olish"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.id, s.channel_id, s.message, s.time, s.with_date, 
                       s.start_date, s.day_count, c.channel_name
                FROM schedules s
                LEFT JOIN channels c ON s.channel_id = c.channel_id
                WHERE s.user_id = ?
                ORDER BY s.id DESC
            ''', (user_id,))
            return cursor.fetchall()
    
    def get_schedule_by_id(self, schedule_id: int) -> Optional[Tuple]:
        """Reja ID bo'yicha olish"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM schedules WHERE id = ?
            ''', (schedule_id,))
            return cursor.fetchone()
    
    def update_day_count(self, schedule_id: int, day_count: int):
        """Challenge kunini yangilash"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE schedules SET day_count = ? WHERE id = ?',
                (day_count, schedule_id)
            )
            conn.commit() 

    def delete_schedule(self, schedule_id: int):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
            conn.commit() 

    def delete_channel(self, user_id: int, channel_id: str):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM channels WHERE user_id = ? AND channel_id = ?', (user_id, channel_id))
            conn.commit() 