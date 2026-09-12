import os
from sqlalchemy import create_engine, text
import datetime

# Fallback to local SQLite if DATABASE_URL or POSTGRES_URL are not set
DATABASE_URL = os.getenv("POSTGRES_URL", os.getenv("DATABASE_URL", "sqlite:///visa_tracker.db"))

# Vercel/Heroku Postgres URL fix for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

def init_db():
    with engine.begin() as conn:
        # 1. Decisions Table
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS decisions (
                irl_number VARCHAR PRIMARY KEY,
                status VARCHAR,
                decision_date VARCHAR,
                last_updated TIMESTAMP
            )
        '''))
        
        # 2. Subscriptions Table
        is_postgres = "postgresql" in DATABASE_URL
        if is_postgres:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    irl_number VARCHAR NOT NULL,
                    email VARCHAR NOT NULL,
                    is_notified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
        else:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    irl_number VARCHAR NOT NULL,
                    email VARCHAR NOT NULL,
                    is_notified BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))

def upsert_decisions(decisions_data):
    init_db() # Ensure tables exist
    if not decisions_data:
        return

    current_time = datetime.datetime.now(datetime.timezone.utc)
    is_postgres = "postgresql" in DATABASE_URL
    
    with engine.begin() as conn:
        if is_postgres:
            sql = text('''
                INSERT INTO decisions (irl_number, status, decision_date, last_updated)
                VALUES (:irl_number, :status, :decision_date, :last_updated)
                ON CONFLICT (irl_number) DO UPDATE SET
                    status = EXCLUDED.status,
                    decision_date = EXCLUDED.decision_date,
                    last_updated = EXCLUDED.last_updated
            ''')
        else:
            sql = text('''
                INSERT INTO decisions (irl_number, status, decision_date, last_updated)
                VALUES (:irl_number, :status, :decision_date, :last_updated)
                ON CONFLICT(irl_number) DO UPDATE SET
                    status = excluded.status,
                    decision_date = excluded.decision_date,
                    last_updated = excluded.last_updated
            ''')
        
        data = [
            {
                "irl_number": d["irl_number"],
                "status": d["status"],
                "decision_date": d["decision_date"],
                "last_updated": current_time
            } for d in decisions_data
        ]
        conn.execute(sql, data)

def get_decision(irl_number):
    with engine.connect() as conn:
        result = conn.execute(
            text('SELECT status, decision_date FROM decisions WHERE irl_number = :irl'), 
            {"irl": irl_number}
        ).fetchone()
        
    if result:
        return {"found": True, "status": result[0], "date": result[1]}
    return {"found": False, "message": "Application still processing or not yet published."}

def get_all_decisions(limit=10000):
    with engine.connect() as conn:
        rows = conn.execute(
            text('SELECT irl_number, status, decision_date, last_updated FROM decisions ORDER BY decision_date DESC, last_updated DESC LIMIT :limit'), 
            {"limit": limit}
        ).fetchall()
        
    return [
        {
            "irl_number": r[0],
            "status": r[1],
            "decision_date": r[2],
            "last_updated": str(r[3])
        } for r in rows
    ]

def get_db_status():
    with engine.connect() as conn:
        total_records = conn.execute(text('SELECT COUNT(*) FROM decisions')).fetchone()[0]
        last_sync = conn.execute(text('SELECT MAX(last_updated) FROM decisions')).fetchone()[0]
        
    return {
        "last_sync": str(last_sync) if last_sync else None,
        "total_records": total_records
    }

# --- Subscription Logic ---
def add_subscription(irl_number, email):
    init_db() # Ensure tables exist in serverless environments
    with engine.begin() as conn:
        is_postgres = "postgresql" in DATABASE_URL
        false_val = "FALSE" if is_postgres else "0"
        
        # Check if subscription already exists for this IRL and Email
        existing = conn.execute(
            text(f'SELECT id FROM subscriptions WHERE irl_number = :irl AND email = :email AND is_notified = {false_val}'),
            {"irl": irl_number, "email": email}
        ).fetchone()
        
        if existing:
            return False # Already subscribed
            
        conn.execute(
            text('INSERT INTO subscriptions (irl_number, email) VALUES (:irl, :email)'),
            {"irl": irl_number, "email": email}
        )
        return True

def get_pending_subscriptions_with_decisions():
    with engine.connect() as conn:
        is_postgres = "postgresql" in DATABASE_URL
        false_val = "FALSE" if is_postgres else "0"
        
        # Inner join to find subscriptions that now have a corresponding published decision
        sql = text(f'''
            SELECT s.id, s.irl_number, s.email, d.status, d.decision_date
            FROM subscriptions s
            JOIN decisions d ON s.irl_number = d.irl_number
            WHERE s.is_notified = {false_val}
        ''')
        rows = conn.execute(sql).fetchall()
        
        return [
            {
                "id": r[0],
                "irl_number": r[1],
                "email": r[2],
                "status": r[3],
                "decision_date": r[4]
            } for r in rows
        ]

def mark_subscription_notified(sub_id):
    with engine.begin() as conn:
        is_postgres = "postgresql" in DATABASE_URL
        true_val = "TRUE" if is_postgres else "1"
        
        conn.execute(
            text(f'UPDATE subscriptions SET is_notified = {true_val} WHERE id = :id'),
            {"id": sub_id}
        )
