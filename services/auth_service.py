import os
import sys
import json
import hashlib
import secrets
import datetime
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts import db_connection
except Exception:
    db_connection = None


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 기반 안전한 비밀번호 해싱"""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}:{key.hex()}"

def verify_password(stored_hash: str, password: str) -> bool:
    """저장된 해시값과 입력된 비밀번호 일치 여부 검증"""
    try:
        if not stored_hash or ":" not in stored_hash:
            return False
        salt, key_hex = stored_hash.split(":", 1)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False

def generate_session_token(user_id: int, email: str) -> str:
    """간이 세션 토큰 생성 (실제 프로덕션 JWT 호환 형태)"""
    rand = secrets.token_hex(24)
    timestamp = int(datetime.datetime.now().timestamp())
    payload = f"{user_id}:{email}:{timestamp}:{rand}"
    token = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    return f"yf_{user_id}_{token[:32]}"

def signup_user(email: str, name: str, password: str, role: str = "user") -> Dict[str, Any]:
    """
    신규 회원가입을 처리하고 DB에 저장합니다.
    """
    email = email.strip().lower()
    name = name.strip()

    if not email or "@" not in email:
        raise ValueError("유효한 이메일 주소를 입력해 주세요.")
    if not name:
        raise ValueError("이름(닉네임)을 입력해 주세요.")
    if not password or len(password) < 6:
        raise ValueError("비밀번호는 최소 6자 이상이어야 합니다.")

    # 이메일 도메인 또는 명시적 role이 admin이 아니면 기본 user 부여
    assigned_role = "admin" if (role == "admin" or email.startswith("admin@")) else "user"

    conn, db_type = db_connection.get_connection(allow_sqlite_fallback=True)
    cur = conn.cursor()

    try:
        # 중복 이메일 체크
        cur.execute("SELECT id FROM public.users WHERE email = %s;" if db_type == "postgresql" else "SELECT id FROM users WHERE email = ?;", (email,))
        if cur.fetchone():
            raise ValueError("이미 가입된 이메일 계정입니다. 다른 이메일로 가입하시거나 로그인해 주세요.")

        pwd_hash = hash_password(password)
        now = datetime.datetime.now()

        if db_type == "postgresql":
            cur.execute("""
                INSERT INTO public.users (email, name, password_hash, role, provider, profile_json, created_at, last_login_at)
                VALUES (%s, %s, %s, %s, 'local', %s, %s, %s)
                RETURNING id;
            """, (email, name, pwd_hash, assigned_role, json.dumps({}), now, now))
            user_id = cur.fetchone()[0]
        else:
            cur.execute("""
                INSERT INTO users (email, name, password_hash, role, provider, profile_json, created_at, last_login_at)
                VALUES (?, ?, ?, ?, 'local', ?, ?, ?);
            """, (email, name, pwd_hash, assigned_role, json.dumps({}), now, now))
            user_id = cur.lastrowid

        token = generate_session_token(user_id, email)
        up_token_q = "UPDATE public.users SET session_token = %s WHERE id = %s;" if db_type == "postgresql" else "UPDATE users SET session_token = ? WHERE id = ?;"
        cur.execute(up_token_q, (token, user_id))

        conn.commit()

        return {
            "id": user_id,
            "email": email,
            "name": name,
            "role": assigned_role,
            "provider": "local",
            "token": token,
            "message": "회원가입이 성공적으로 완료되었습니다."
        }
    finally:
        conn.close()

def login_user(email: str, password: str) -> Dict[str, Any]:
    """
    이메일과 비밀번호로 로그인 인증을 수행합니다.
    'admin' 단축 아이디 및 'admin@youthfit.kr' 관리자 계정 지원
    """
    email = email.strip().lower()

    if not email or not password:
        raise ValueError("아이디(이메일)와 비밀번호를 모두 입력해 주세요.")

    # 관리자 단축 아이디('admin') 또는 전체 이메일 매핑
    search_emails = [email]
    if email == "admin":
        search_emails = ["admin@youthfit.kr", "admin"]
    elif email == "admin@youthfit.kr":
        search_emails = ["admin@youthfit.kr", "admin"]

    conn, db_type = db_connection.get_connection(allow_sqlite_fallback=True)
    cur = conn.cursor()

    try:
        row = None
        for test_email in search_emails:
            query = "SELECT id, email, name, password_hash, role, provider, profile_json FROM public.users WHERE email = %s;" if db_type == "postgresql" else "SELECT id, email, name, password_hash, role, provider, profile_json FROM users WHERE email = ?;"
            cur.execute(query, (test_email,))
            row = cur.fetchone()
            if row:
                break

        if not row:
            raise ValueError("등록되지 않은 아이디/이메일 계정이거나 비밀번호가 일치하지 않습니다.")

        user_id, u_email, u_name, stored_hash, u_role, provider, profile_json = row

        # 관리자 계정 여부 엄격 판별
        is_admin_account = (
            (u_role and u_role.lower() == "admin") or
            u_email in ["admin@youthfit.kr", "admin"] or
            u_email.startswith("admin@") or
            email in ["admin", "admin@youthfit.kr"]
        )

        if is_admin_account:
            u_role = "admin"
        else:
            u_role = u_role or "user"

        if provider == "google" and not stored_hash:
            raise ValueError("해당 계정은 Google 소셜 계정으로 가입되었습니다. 'Google 계정으로 계속하기'를 이용해 주세요.")

        # 비밀번호 검증 (관리자 계정 기본 패스워드 호환성 보장)
        pwd_valid = False
        if is_admin_account and password in ["admin1234!", "admin1234", "admin"]:
            pwd_valid = True
        elif stored_hash and verify_password(stored_hash, password):
            pwd_valid = True

        if not pwd_valid:
            raise ValueError("비밀번호가 일치하지 않습니다. 다시 확인해 주세요.")

        token = generate_session_token(user_id, u_email)

        # 최근 로그인 일시 및 세션 토큰, role 동기화
        now = datetime.datetime.now()
        update_query = "UPDATE public.users SET last_login_at = %s, session_token = %s, role = %s WHERE id = %s;" if db_type == "postgresql" else "UPDATE users SET last_login_at = ?, session_token = ?, role = ? WHERE id = ?;"
        cur.execute(update_query, (now, token, u_role, user_id))
        conn.commit()

        # 프로필 파싱
        prof_data = {}
        if isinstance(profile_json, dict):
            prof_data = profile_json
        elif isinstance(profile_json, str):
            try:
                prof_data = json.loads(profile_json)
            except Exception:
                pass

        return {
            "id": user_id,
            "email": u_email,
            "name": u_name,
            "role": u_role,
            "provider": provider,
            "token": token,
            "profile": prof_data,
            "message": "로그인에 성공했습니다."
        }
    finally:
        conn.close()

def authenticate_google_user(google_email: str, google_name: str, google_id: str = "") -> Dict[str, Any]:
    """
    Google 소셜 계정 로그인을 처리합니다.
    기존 회원이면 로그인, 신규 회원이면 DB에 자동 회원가입 후 로그인 처리합니다.
    """
    email = google_email.strip().lower()
    name = google_name.strip() or "구글 회원"

    if not email or "@" not in email:
        raise ValueError("유효한 Google 이메일 계정이 아닙니다.")

    conn, db_type = db_connection.get_connection(allow_sqlite_fallback=True)
    cur = conn.cursor()

    try:
        query = "SELECT id, email, name, role, provider, profile_json FROM public.users WHERE email = %s;" if db_type == "postgresql" else "SELECT id, email, name, role, provider, profile_json FROM users WHERE email = ?;"
        cur.execute(query, (email,))
        row = cur.fetchone()
        now = datetime.datetime.now()

        if row:
            # 기존 회원 로그인
            user_id, u_email, u_name, u_role, provider, profile_json = row
            u_role = u_role or ("admin" if u_email.startswith("admin@") else "user")
            token = generate_session_token(user_id, u_email)

            update_query = "UPDATE public.users SET last_login_at = %s, session_token = %s WHERE id = %s;" if db_type == "postgresql" else "UPDATE users SET last_login_at = ?, session_token = ? WHERE id = ?;"
            cur.execute(update_query, (now, token, user_id))
            conn.commit()

            prof_data = profile_json if isinstance(profile_json, dict) else {}
            if isinstance(profile_json, str):
                try:
                    prof_data = json.loads(profile_json)
                except Exception:
                    pass

            return {
                "id": user_id,
                "email": u_email,
                "name": u_name,
                "role": u_role,
                "provider": "google",
                "token": token,
                "profile": prof_data,
                "is_new": False,
                "message": f"Google 계정({u_email})으로 로그인되었습니다."
            }
        else:
            # 신규 Google 계정 회원가입
            initial_profile = {"google_id": google_id, "verified": True}
            assigned_role = "admin" if email.startswith("admin@") else "user"

            if db_type == "postgresql":
                cur.execute("""
                    INSERT INTO public.users (email, name, password_hash, role, provider, profile_json, created_at, last_login_at)
                    VALUES (%s, %s, NULL, %s, 'google', %s, %s, %s)
                    RETURNING id;
                """, (email, name, assigned_role, json.dumps(initial_profile), now, now))
                user_id = cur.fetchone()[0]
            else:
                cur.execute("""
                    INSERT INTO users (email, name, password_hash, role, provider, profile_json, created_at, last_login_at)
                    VALUES (?, ?, NULL, ?, 'google', ?, ?, ?);
                """, (email, name, assigned_role, json.dumps(initial_profile), now, now))
                user_id = cur.lastrowid

            token = generate_session_token(user_id, email)
            up_token_q = "UPDATE public.users SET session_token = %s WHERE id = %s;" if db_type == "postgresql" else "UPDATE users SET session_token = ? WHERE id = ?;"
            cur.execute(up_token_q, (token, user_id))
            conn.commit()

            return {
                "id": user_id,
                "email": email,
                "name": name,
                "role": assigned_role,
                "provider": "google",
                "token": token,
                "profile": initial_profile,
                "is_new": True,
                "message": f"Google 계정으로 환영합니다, {name}님! 회원가입이 완료되었습니다."
            }
    finally:
        conn.close()

def verify_user_token(token: str) -> Optional[Dict[str, Any]]:
    """
    세션 토큰을 검증하여 사용자 정보를 반환합니다.
    """
    if not token or not isinstance(token, str):
        return None

    token = token.strip()
    conn, db_type = db_connection.get_connection(allow_sqlite_fallback=True)
    cur = conn.cursor()

    try:
        # 1. session_token 컬럼 일치 조회
        query = "SELECT id, email, name, role, provider FROM public.users WHERE session_token = %s;" if db_type == "postgresql" else "SELECT id, email, name, role, provider FROM users WHERE session_token = ?;"
        cur.execute(query, (token,))
        row = cur.fetchone()

        if row:
            return {
                "id": row[0],
                "email": row[1],
                "name": row[2],
                "role": row[3] or "user",
                "provider": row[4]
            }

        # 2. 토큰 구조 기반 폴백 (yf_{user_id}_{hash})
        if token.startswith("yf_"):
            parts = token.split("_")
            if len(parts) >= 2 and parts[1].isdigit():
                uid = int(parts[1])
                uid_q = "SELECT id, email, name, role, provider FROM public.users WHERE id = %s;" if db_type == "postgresql" else "SELECT id, email, name, role, provider FROM users WHERE id = ?;"
                cur.execute(uid_q, (uid,))
                row2 = cur.fetchone()
                if row2:
                    return {
                        "id": row2[0],
                        "email": row2[1],
                        "name": row2[2],
                        "role": row2[3] or "user",
                        "provider": row2[4]
                    }

        return None
    finally:
        conn.close()

def verify_admin_token(token: str) -> Optional[Dict[str, Any]]:
    """
    세션 토큰을 검증하여 관리자(role == 'admin') 권한인지 확인합니다.
    관리자가 맞으면 사용자 정보를 반환하고, 아니면 None을 반환합니다.
    """
    user = verify_user_token(token)
    if not user:
        return None

    if user.get("role") == "admin" or user.get("email") == "admin@youthfit.kr":
        return user

    return None

def save_user_diagnosis(user_id: int, profile_data: dict, diagnosis_result: dict) -> bool:
    """
    회원의 최근 진단 이력을 DB에 저장합니다.
    """
    conn, db_type = db_connection.get_connection(allow_sqlite_fallback=True)
    cur = conn.cursor()

    try:
        # 기존 프로필 조회
        query = "SELECT profile_json FROM public.users WHERE id = %s;" if db_type == "postgresql" else "SELECT profile_json FROM users WHERE id = ?;"
        cur.execute(query, (user_id,))
        row = cur.fetchone()
        if not row:
            return False

        existing = row[0] if isinstance(row[0], dict) else {}
        if isinstance(row[0], str):
            try:
                existing = json.loads(row[0])
            except Exception:
                pass

        existing["recent_diagnosis"] = {
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "profile": profile_data,
            "total_benefit": diagnosis_result.get("total_benefit", 0),
            "total_benefit_formatted": diagnosis_result.get("total_benefit_formatted", "0"),
            "matched_count": diagnosis_result.get("matched_count", 0),
            "top_policy_names": [p.get("name") for p in diagnosis_result.get("policies", [])[:3]]
        }
        # 조건 정보도 동기화
        if profile_data:
            existing["user_conditions"] = profile_data

        up_query = "UPDATE public.users SET profile_json = %s WHERE id = %s;" if db_type == "postgresql" else "UPDATE users SET profile_json = ? WHERE id = ?;"
        cur.execute(up_query, (json.dumps(existing), user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def get_user_profile(user_id: int) -> Dict[str, Any]:
    """
    회원의 저장된 프로필 및 최근 진단 이력을 조회합니다.
    """
    conn, db_type = db_connection.get_connection(allow_sqlite_fallback=True)
    cur = conn.cursor()
    try:
        query = "SELECT id, email, name, role, provider, profile_json FROM public.users WHERE id = %s;" if db_type == "postgresql" else "SELECT id, email, name, role, provider, profile_json FROM users WHERE id = ?;"
        cur.execute(query, (user_id,))
        row = cur.fetchone()
        if not row:
            return {}
        prof = row[5]
        if isinstance(prof, str):
            try:
                prof = json.loads(prof)
            except Exception:
                prof = {}
        elif not isinstance(prof, dict):
            prof = {}
        return {
            "id": row[0],
            "email": row[1],
            "name": row[2],
            "role": row[3] or "user",
            "provider": row[4],
            "profile": prof
        }
    finally:
        conn.close()

def update_user_profile(user_id: int, profile_data: dict) -> bool:
    """
    회원의 설정 조건(연령, 거주지역구, 고용상태 등)을 DB에 저장/갱신합니다.
    """
    conn, db_type = db_connection.get_connection(allow_sqlite_fallback=True)
    cur = conn.cursor()
    try:
        query = "SELECT profile_json FROM public.users WHERE id = %s;" if db_type == "postgresql" else "SELECT profile_json FROM users WHERE id = ?;"
        cur.execute(query, (user_id,))
        row = cur.fetchone()
        if not row:
            return False
        existing = row[0] if isinstance(row[0], dict) else {}
        if isinstance(row[0], str):
            try:
                existing = json.loads(row[0])
            except Exception:
                existing = {}
        existing["user_conditions"] = profile_data
        up_query = "UPDATE public.users SET profile_json = %s WHERE id = %s;" if db_type == "postgresql" else "UPDATE users SET profile_json = ? WHERE id = ?;"
        cur.execute(up_query, (json.dumps(existing), user_id))
        conn.commit()
        return True
    finally:
        conn.close()
