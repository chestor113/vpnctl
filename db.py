from datetime import datetime, timedelta, UTC
import logging
import sqlite3


# поиск по uuid
def find_by_uuid(uuid):
    with sqlite3.connect("db.sqlite") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        row = cursor.execute("select * from access_grants where uuid=?", (uuid,)).fetchone()
        if not row:
            return None
        return dict(row)
    
def find_by_username(username):
    with sqlite3.connect("db.sqlite") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        row = cursor.execute("select * from access_grants where username=?", (username,)).fetchone()
        if not row:
            return None
        return dict(row)
    
def find_by_telegram(telegram):
    with sqlite3.connect("db.sqlite") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        row = cursor.execute("select * from access_grants where telegram=?", (telegram,)).fetchone()
        if not row:
            return None
        return dict(row)

# вставка нового пользователя
def insert_grant(payload):
    with sqlite3.connect("db.sqlite") as conn:
        try:
            cursor = conn.execute("""
        INSERT INTO access_grants (
            uuid, username, telegram, created_at, expires_at, is_enabled, access_tag, wg_public_key, wg_private_key, wg_assigned_ip, wg_preshared_key
        ) VALUES (
            :uuid, :username, :telegram, :created_at, :expires_at, :is_enabled, :access_tag, :wg_public_key, :wg_private_key, :wg_assigned_ip, :wg_preshared_key
        )
        """, payload)
            return cursor.lastrowid
        except sqlite3.Error as e:
            logging.info("Error: %s", e)
            return None
    
def enable_by_uuid(uuid):
    with sqlite3.connect("db.sqlite") as conn:
        try:
            cursor = conn.execute("""update access_grants set is_enabled=1, turned_off_reason=null, turned_off_at=null where uuid = ? """, (uuid,))
            if cursor.rowcount == 1:
                return True
            else: return False
        except sqlite3.Error as e:
            logging.info("Error: %s", e)
            return False

def disable_by_uuid(uuid, reason):
    with sqlite3.connect("db.sqlite") as conn:
        now = datetime.now(UTC)
        try:
            cursor = conn.execute("""update access_grants set is_enabled=0 , turned_off_reason=?, turned_off_at=? where uuid = ? """, (reason,now.strftime("%Y-%m-%d %H:%M:%S"), uuid))
            if cursor.rowcount == 1:
                return True
            else: return False
        except sqlite3.Error as e:
            logging.info("Error: %s", e)
            return False

def renew_by_uuid(uuid, days):
    with sqlite3.connect("db.sqlite") as conn:
        try:
            now = datetime.now(UTC)
            new_exp_date = now + timedelta(days = days)
            cursor = conn.execute("""update access_grants set expires_at=? , turned_off_reason=null, turned_off_at=null, is_enabled=1 where uuid = ? """, (new_exp_date.strftime("%Y-%m-%d %H:%M:%S"),uuid))
            if cursor.rowcount == 1:
                return True
            else: return False
        except sqlite3.Error as e:
            logging.info("Error: %s", e)
            return False
        
def get_active_clients():
    with sqlite3.connect("db.sqlite") as conn:
        try:
            now = datetime.now(UTC)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """select uuid, telegram from access_grants where (access_tag='vip' and is_enabled=1) or (is_enabled = 1 and expires_at > ?);""", (now.strftime("%Y-%m-%d %H:%M:%S"),)
            ).fetchall()
            if not rows:
                return []
            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            logging.info("Error: %s", e)
            return []
        
def get_expired_uuids():
    with sqlite3.connect("db.sqlite") as conn:
        try:
            now = datetime.now(UTC)
            cursor = conn.execute(
                """select uuid from access_grants where  (expires_at < ? and is_enabled = 1) and access_tag != 'vip';""", (now.strftime("%Y-%m-%d %H:%M:%S"),)
            ).fetchall()

            return [row[0] for row in cursor]

        except sqlite3.Error as e:
            logging.info("Error: %s", e)
            return []

def expire_job():  
    off_result = get_expired_uuids()
    if off_result:
        for uuid in off_result:
            disable_by_uuid(uuid, 'expired')
            logging.info("Expire user: %s ", uuid)
        return off_result
    else: return None

def get_ip_addresses():
    with sqlite3.connect("db.sqlite") as conn:
        try:
            cursor = conn.execute(
                """select wg_assigned_ip from access_grants ; """).fetchall()

            return [row[0] for row in cursor if row[0] is not None]

        except sqlite3.Error as e:
            logging.info("Error: %s", e)
            return []