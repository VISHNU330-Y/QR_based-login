import sqlite3
import os
from config import DATABASE_PATH


def get_db():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            roll_no TEXT,
            department TEXT,
            year INTEGER,
            hostel_block TEXT,
            photo_url TEXT,
            role TEXT NOT NULL CHECK(role IN ('student', 'hod', 'warden', 'security')),
            parent_contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS gate_passes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            destination TEXT NOT NULL,
            date TEXT NOT NULL,
            exit_time TEXT NOT NULL,
            return_time TEXT NOT NULL,
            parent_contact TEXT,
            hod_status TEXT DEFAULT 'pending' CHECK(hod_status IN ('pending', 'approved', 'rejected')),
            warden_status TEXT DEFAULT 'pending' CHECK(warden_status IN ('pending', 'approved', 'rejected')),
            pass_status TEXT DEFAULT 'requested' CHECK(pass_status IN (
                'requested', 'hod_approved', 'warden_approved',
                'exit_used', 'entry_used', 'completed',
                'rejected_hod', 'rejected_warden', 'expired', 'cancelled'
            )),
            hod_id INTEGER,
            warden_id INTEGER,
            hod_remarks TEXT,
            warden_remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (hod_id) REFERENCES users(id),
            FOREIGN KEY (warden_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pass_id INTEGER NOT NULL,
            qr_type TEXT NOT NULL CHECK(qr_type IN ('exit', 'entry')),
            qr_token TEXT UNIQUE NOT NULL,
            qr_data TEXT NOT NULL,
            qr_image TEXT,
            qr_expiry TIMESTAMP NOT NULL,
            is_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pass_id) REFERENCES gate_passes(id)
        );

        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pass_id INTEGER NOT NULL,
            action_type TEXT NOT NULL CHECK(action_type IN ('exit', 'entry')),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            gate_number TEXT DEFAULT 'Gate 1',
            security_guard_id INTEGER,
            FOREIGN KEY (pass_id) REFERENCES gate_passes(id),
            FOREIGN KEY (security_guard_id) REFERENCES users(id)
        );
    ''')

    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully!")


def query_db(query, args=(), one=False):
    """Execute a query and return results as dicts."""
    conn = get_db()
    cursor = conn.execute(query, args)
    results = cursor.fetchall()
    conn.close()
    if one:
        return dict(results[0]) if results else None
    return [dict(row) for row in results]


def execute_db(query, args=()):
    """Execute a write query and return lastrowid."""
    conn = get_db()
    cursor = conn.execute(query, args)
    conn.commit()
    lastrowid = cursor.lastrowid
    conn.close()
    return lastrowid
