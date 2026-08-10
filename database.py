from datetime import datetime
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'forum.db')


def get_connection():
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  conn = get_connection()
  cursor = conn.cursor()

  cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kulup_id TEXT NOT NULL,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

  conn.commit()
  conn.close()


def add_message(kulup_id, username, content):
  """Yeni mesajı veritabanına kaydeder."""
  conn = get_connection()
  cursor = conn.cursor()

  created_at = datetime.now().strftime('%d.%m.%Y %H:%M')
  cursor.execute(
      '''
        INSERT INTO messages (kulup_id, username, content, created_at)
        VALUES (?, ?, ?, ?)
    ''',
      (kulup_id, username, content, created_at),
  )

  conn.commit()
  conn.close()


def get_messages(kulup_id, limit=20):
  """Buffer şişirmeyen fonksiyon: Sadece istenen kulübün son 'limit' kadar mesajını getirir."""
  conn = get_connection()
  cursor = conn.cursor()

  cursor.execute(
      '''
        SELECT username AS isim, content AS mesaj, created_at AS tarih 
        FROM messages 
        WHERE kulup_id = ?
        ORDER BY id DESC 
        LIMIT ?
    ''',
      (kulup_id, limit),
  )

  rows = cursor.fetchall()
  conn.close()

  messages = [dict(row) for row in rows]
  messages.reverse()
  return messages 