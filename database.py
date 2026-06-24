import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    #Creates and returns aconnection to the PostgreSQL database.
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

#Setup the database and create the necessary tables
def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Table 1: Saves info when the bot is added to a group
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id                      SERIAL PRIMARY KEY,
            group_id                BIGINT UNIQUE,
            group_name              TEXT,
            added_by_id             BIGINT,
            added_by_username       TEXT,
            added_by_name           TEXT,
            admin_name              TEXT,
            admin_username          TEXT,
            date_added              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    #Table 2: Saves every message where the bot is mentioned
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mentions (
            id              SERIAL PRIMARY KEY,
            message_id      BIGINT,
            message_text    TEXT,
            user_id         BIGINT,
            username        TEXT,
            first_name      TEXT,
            group_id        BIGINT,
            group_name      TEXT,
            date_time       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    #Table 3: Keeps message count running total per group or private chat
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_counts(
            id              SERIAL PRIMARY KEY,
            chat_id         BIGINT UNIQUE,
            chat_type       TEXT,
            chat_name       TEXT,
            message_count   INTEGER DEFAULT 0,
            last_updated    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("PostgreSQL database ready.")

#Save group info when the bot is added
def save_group(group_id, group_name, added_by_id, added_by_username, added_by_name, admin_name, admin_username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO groups
        (group_id, group_name, added_by_id, added_by_username, added_by_name, admin_name, admin_username)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (group_id) DO UPDATE SET
            group_name              = EXCLUDED.group_name,
            added_by_id             = EXCLUDED.added_by_id,
            added_by_username       = EXCLUDED.added_by_username,
            added_by_name           = EXCLUDED.added_by_name,
            admin_name              = EXCLUDED.admin_name,
            admin_username          = EXCLUDED.admin_username
    """, (group_id, group_name, added_by_id, added_by_username, added_by_name, admin_name, admin_username))
    conn.commit()
    conn.close()

#Get group info for /admin command
def get_group_info(group_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM groups WHERE group_id = %s
    """, (group_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# Saves when the bot is mentioned
def save_mention(message_id, message_text, user_id, username, first_name, group_id, group_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mentions
        (message_id, message_text, user_id, username, first_name, group_id, group_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (message_id, message_text, user_id, username, first_name, group_id, group_name))
    conn.commit()
    conn.close()

# Increase message counter by 1
def count_message(chat_id, chat_type, chat_name):
    conn = get_connection()
    cursor = conn.cursor()

    #Create the row if this chat is new
    cursor.execute("""
        INSERT INTO message_counts (chat_id, chat_type, chat_name, message_count)
        VALUES (%s, %s, %s, 1)
        ON CONFLICT (chat_id) DO UPDATE SET
            message_count = message_counts.message_count + 1,
            last_updated = CURRENT_TIMESTAMP
    """, (chat_id, chat_type, chat_name))
    conn.commit()
    conn.close()

#Get message count for /totalmsg command
def get_message_count(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message_count FROM message_counts WHERE chat_id = %s
    """, (chat_id,))
    row = cursor.fetchone()
    conn.close()
    return row["message_count"] if row else 0

# Get all chat IDs for broadcast
def get_all_chats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM message_counts")
    rows = cursor.fetchall()
    conn.close()
    return [row["chat_id"] for row in rows]
