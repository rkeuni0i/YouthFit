import sys
import os
import json
import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from scripts import db_connection
from services.auth_service import hash_password, generate_session_token

def setup_users_table():
    conn, db_type = db_connection.get_connection(allow_sqlite_fallback=True)
    cur = conn.cursor()

    print(f"Connected to {db_type.upper()} database.")

    # PostgreSQL / SQLite users table schema with role and session_token
    if db_type == "postgresql":
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            password_hash VARCHAR(255),
            role VARCHAR(20) DEFAULT 'user',
            provider VARCHAR(50) DEFAULT 'local',
            profile_json JSONB DEFAULT '{}',
            session_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS session_token TEXT;
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
        """)
        conn.commit()
    else:
        cur.executescript(create_sql)
        conn.commit()

    # 안전한 ALTER TABLE (이미 존재하는 테이블에 role, session_token 없을 경우)
    for col_def in [("role", "TEXT DEFAULT 'user'"), ("session_token", "TEXT")]:
        try:
            col_name, col_type = col_def
            cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};")
            conn.commit()
            print(f"  + Added column {col_name} to users table.")
        except Exception:
            # 이미 컬럼이 존재하는 경우 무시
            conn.rollback() if db_type == "postgresql" else None

    print("✓ 'users' table created/verified.")

    # 기본 관리자(admin) 및 일반 테스트 사용자(user) 시딩
    seed_accounts = [
        {
            "email": "admin@youthfit.kr",
            "name": "시스템 최고관리자",
            "password": "admin1234!",
            "role": "admin",
            "profile": {"title": "YouthFit AI Super Admin", "department": "운영관제팀"}
        },
        {
            "email": "user@youthfit.kr",
            "name": "김청년",
            "password": "user1234!",
            "role": "user",
            "profile": {"target_region": "서울시", "target_category": "취업/주거"}
        }
    ]

    now = datetime.datetime.now()
    for acc in seed_accounts:
        check_q = "SELECT id FROM public.users WHERE email = %s;" if db_type == "postgresql" else "SELECT id FROM users WHERE email = ?;"
        cur.execute(check_q, (acc["email"],))
        row = cur.fetchone()

        pwd_hash = hash_password(acc["password"])
        prof_json = json.dumps(acc["profile"])

        if row:
            user_id = row[0]
            token = generate_session_token(user_id, acc["email"])
            up_q = """
                UPDATE users 
                SET role = %s, password_hash = %s, session_token = %s, profile_json = %s, last_login_at = %s 
                WHERE id = %s;
            """ if db_type == "postgresql" else """
                UPDATE users 
                SET role = ?, password_hash = ?, session_token = ?, profile_json = ?, last_login_at = ? 
                WHERE id = ?;
            """
            cur.execute(up_q, (acc["role"], pwd_hash, token, prof_json, now, user_id))
            print(f"  ✓ Updated seed user: {acc['email']} (role: {acc['role']})")
        else:
            ins_q = """
                INSERT INTO users (email, name, password_hash, role, provider, profile_json, created_at, last_login_at)
                VALUES (%s, %s, %s, %s, 'local', %s, %s, %s) RETURNING id;
            """ if db_type == "postgresql" else """
                INSERT INTO users (email, name, password_hash, role, provider, profile_json, created_at, last_login_at)
                VALUES (?, ?, ?, ?, 'local', ?, ?, ?);
            """
            cur.execute(ins_q, (acc["email"], acc["name"], pwd_hash, acc["role"], prof_json, now, now))
            user_id = cur.fetchone()[0] if db_type == "postgresql" else cur.lastrowid
            token = generate_session_token(user_id, acc["email"])
            
            token_up_q = "UPDATE users SET session_token = %s WHERE id = %s;" if db_type == "postgresql" else "UPDATE users SET session_token = ? WHERE id = ?;"
            cur.execute(token_up_q, (token, user_id))
            print(f"  ✓ Created seed user: {acc['email']} (role: {acc['role']}, id: {user_id})")

    conn.commit()

    # Check table columns
    print("\nCurrent columns in users table:")
    if db_type == "postgresql":
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users';
        """)
        for col in cur.fetchall():
            print(f"  - {col[0]} ({col[1]})")
    else:
        cur.execute("PRAGMA table_info(users);")
        for col in cur.fetchall():
            print(f"  - {col[1]} ({col[2]})")

    conn.close()
    print("\n✓ User table setup & seeding completed successfully!")

if __name__ == "__main__":
    setup_users_table()
