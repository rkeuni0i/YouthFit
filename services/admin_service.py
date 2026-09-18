import os
import sys
import json
import sqlite3
import datetime
from typing import Optional, Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts import db_connection
except ImportError:
    db_connection = None

def get_db_conn():
    if db_connection:
        return db_connection.get_connection(allow_sqlite_fallback=True)
    sqlite_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "youthfit.db"
    )
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    return sqlite3.connect(sqlite_path), "sqlite"

def init_admin_tables():
    """관리자 로그 및 통계 테이블 생성"""
    conn, db_type = get_db_conn()
    cur = conn.cursor()
    try:
        if db_type == "postgresql":
            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_activity_logs (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(64),
                user_email VARCHAR(255),
                user_name VARCHAR(100),
                action VARCHAR(100) NOT NULL,
                details TEXT,
                ip_address VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS service_logs (
                id SERIAL PRIMARY KEY,
                method VARCHAR(16) NOT NULL,
                path VARCHAR(500) NOT NULL,
                status_code INTEGER NOT NULL,
                duration_ms REAL NOT NULL,
                client_ip VARCHAR(100),
                error_msg TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS policy_stats (
                policy_id VARCHAR(64) PRIMARY KEY,
                policy_name VARCHAR(500) NOT NULL,
                category VARCHAR(100),
                matches_count INTEGER DEFAULT 0,
                views_count INTEGER DEFAULT 0,
                clicks_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
        else:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_email TEXT,
                user_name TEXT,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS service_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                duration_ms REAL NOT NULL,
                client_ip TEXT,
                error_msg TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS policy_stats (
                policy_id TEXT PRIMARY KEY,
                policy_name TEXT NOT NULL,
                category TEXT,
                matches_count INTEGER DEFAULT 0,
                views_count INTEGER DEFAULT 0,
                clicks_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
        conn.commit()
    except Exception as e:
        print(f"[!] 관리자 테이블 초기화 실패: {e}")
    finally:
        conn.close()

# 앱 로드 시 자동 초기화
init_admin_tables()

def log_user_activity(action: str, details: str = "", user_email: str = None, user_name: str = None, user_id: str = None, ip_address: str = ""):
    """사용자 활동 로그 기록"""
    try:
        conn, db_type = get_db_conn()
        cur = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if db_type == "postgresql":
            cur.execute("""
                INSERT INTO user_activity_logs (user_id, user_email, user_name, action, details, ip_address, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (str(user_id or ""), user_email or "게스트(비회원)", user_name or "비회원 청년", action, details, ip_address, now_str))
        else:
            cur.execute("""
                INSERT INTO user_activity_logs (user_id, user_email, user_name, action, details, ip_address, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (str(user_id or ""), user_email or "게스트(비회원)", user_name or "비회원 청년", action, details, ip_address, now_str))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] log_user_activity error: {e}")

def log_service_request(method: str, path: str, status_code: int, duration_ms: float, client_ip: str = "", error_msg: str = None):
    """웹 서비스 작동 로그 기록"""
    try:
        conn, db_type = get_db_conn()
        cur = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if db_type == "postgresql":
            cur.execute("""
                INSERT INTO service_logs (method, path, status_code, duration_ms, client_ip, error_msg, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (method, path, status_code, round(duration_ms, 2), client_ip, error_msg or "", now_str))
        else:
            cur.execute("""
                INSERT INTO service_logs (method, path, status_code, duration_ms, client_ip, error_msg, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (method, path, status_code, round(duration_ms, 2), client_ip, error_msg or "", now_str))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] log_service_request error: {e}")

def track_policy_match(policy_id: str, policy_name: str, category: str = ""):
    """진단 매칭 시 정책 카운트 증가"""
    if not policy_id:
        return
    try:
        conn, db_type = get_db_conn()
        cur = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if db_type == "postgresql":
            cur.execute("""
                INSERT INTO policy_stats (policy_id, policy_name, category, matches_count, views_count, clicks_count, last_accessed)
                VALUES (%s, %s, %s, 1, 0, 0, %s)
                ON CONFLICT (policy_id) DO UPDATE SET
                    matches_count = policy_stats.matches_count + 1,
                    policy_name = EXCLUDED.policy_name,
                    category = EXCLUDED.category,
                    last_accessed = %s
            """, (policy_id, policy_name, category, now_str, now_str))
        else:
            cur.execute("""
                INSERT INTO policy_stats (policy_id, policy_name, category, matches_count, views_count, clicks_count, last_accessed)
                VALUES (?, ?, ?, 1, 0, 0, ?)
                ON CONFLICT (policy_id) DO UPDATE SET
                    matches_count = policy_stats.matches_count + 1,
                    policy_name = excluded.policy_name,
                    category = excluded.category,
                    last_accessed = ?
            """, (policy_id, policy_name, category, now_str, now_str))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] track_policy_match error: {e}")

def track_policy_click(policy_id: str, policy_name: str = "", category: str = ""):
    """정책 상세 보기 또는 공식 신청하기 클릭 시 카운트 증가"""
    if not policy_id:
        return
    try:
        conn, db_type = get_db_conn()
        cur = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if db_type == "postgresql":
            cur.execute("""
                INSERT INTO policy_stats (policy_id, policy_name, category, matches_count, views_count, clicks_count, last_accessed)
                VALUES (%s, %s, %s, 0, 1, 1, %s)
                ON CONFLICT (policy_id) DO UPDATE SET
                    clicks_count = policy_stats.clicks_count + 1,
                    views_count = policy_stats.views_count + 1,
                    last_accessed = %s
            """, (policy_id, policy_name or policy_id, category, now_str, now_str))
        else:
            cur.execute("""
                INSERT INTO policy_stats (policy_id, policy_name, category, matches_count, views_count, clicks_count, last_accessed)
                VALUES (?, ?, ?, 0, 1, 1, ?)
                ON CONFLICT (policy_id) DO UPDATE SET
                    clicks_count = policy_stats.clicks_count + 1,
                    views_count = policy_stats.views_count + 1,
                    last_accessed = ?
            """, (policy_id, policy_name or policy_id, category, now_str, now_str))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] track_policy_click error: {e}")

def get_admin_dashboard_data() -> Dict[str, Any]:
    """관리자 메인 대시보드 종합 지표 조회"""
    conn, db_type = get_db_conn()
    cur = conn.cursor()

    total_diagnoses = 0
    total_users = 0
    total_requests = 0
    avg_response_time = 0.0
    error_count = 0
    popular_policies = []
    recent_user_logs = []
    recent_service_logs = []

    try:
        # 1. 진단 수
        cur.execute("SELECT COUNT(*) FROM user_activity_logs WHERE action LIKE '%진단%'")
        row = cur.fetchone()
        if row:
            total_diagnoses = row[0]

        # 2. 회원 수
        try:
            cur.execute("SELECT COUNT(*) FROM users")
            u_row = cur.fetchone()
            if u_row:
                total_users = u_row[0]
        except Exception:
            total_users = 0

        # 3. 서비스 요청 수 & 평균 응답속도 & 오류 수
        cur.execute("SELECT COUNT(*), AVG(duration_ms) FROM service_logs")
        s_row = cur.fetchone()
        if s_row and s_row[0]:
            total_requests = s_row[0]
            avg_response_time = round(float(s_row[1] or 0.0), 1)

        cur.execute("SELECT COUNT(*) FROM service_logs WHERE status_code >= 400")
        err_row = cur.fetchone()
        if err_row:
            error_count = err_row[0]

        # 4. 인기 정책 TOP 10 (매칭수 및 클릭수 합산 기준)
        cur.execute("""
            SELECT policy_id, policy_name, category, matches_count, views_count, clicks_count,
                   (matches_count * 1 + clicks_count * 3) AS popularity_score
            FROM policy_stats
            ORDER BY popularity_score DESC, matches_count DESC
            LIMIT 10
        """)
        p_rows = cur.fetchall()
        for r in p_rows:
            popular_policies.append({
                "policy_id": r[0],
                "policy_name": r[1],
                "category": r[2] or "청년지원",
                "matches_count": r[3],
                "views_count": r[4],
                "clicks_count": r[5],
                "score": r[6]
            })

        # 5. 최근 사용자 로그 20건
        cur.execute("""
            SELECT id, user_id, user_email, user_name, action, details, ip_address, created_at
            FROM user_activity_logs
            ORDER BY id DESC
            LIMIT 20
        """)
        u_logs = cur.fetchall()
        for r in u_logs:
            recent_user_logs.append({
                "id": r[0],
                "user_id": r[1],
                "user_email": r[2],
                "user_name": r[3],
                "action": r[4],
                "details": r[5],
                "ip_address": r[6],
                "created_at": str(r[7])
            })

        # 6. 최근 서비스 작동 로그 20건
        cur.execute("""
            SELECT id, method, path, status_code, duration_ms, client_ip, error_msg, created_at
            FROM service_logs
            ORDER BY id DESC
            LIMIT 20
        """)
        s_logs = cur.fetchall()
        for r in s_logs:
            recent_service_logs.append({
                "id": r[0],
                "method": r[1],
                "path": r[2],
                "status_code": r[3],
                "duration_ms": r[4],
                "client_ip": r[5],
                "error_msg": r[6],
                "created_at": str(r[7])
            })

    except Exception as e:
        print(f"[!] get_admin_dashboard_data error: {e}")
    finally:
        conn.close()

    success_rate = 100.0
    if total_requests > 0:
        success_rate = round(((total_requests - error_count) / total_requests) * 100, 1)

    top_policy_name = popular_policies[0]["policy_name"] if popular_policies else "서울시 청년수당"

    return {
        "overview": {
            "total_diagnoses": total_diagnoses,
            "total_users": total_users,
            "total_requests": total_requests,
            "avg_response_time_ms": avg_response_time,
            "error_count": error_count,
            "success_rate": success_rate,
            "top_policy": top_policy_name
        },
        "popular_policies": popular_policies,
        "recent_user_logs": recent_user_logs,
        "recent_service_logs": recent_service_logs
    }

def get_popular_policies(limit: int = 50) -> List[Dict[str, Any]]:
    """많이 찾는 정책 데이터 목록 조회"""
    conn, _ = get_db_conn()
    cur = conn.cursor()
    results = []
    try:
        cur.execute("""
            SELECT policy_id, policy_name, category, matches_count, views_count, clicks_count,
                   (matches_count * 1 + clicks_count * 3) AS score, last_accessed
            FROM policy_stats
            ORDER BY score DESC, matches_count DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        for r in rows:
            results.append({
                "policy_id": r[0],
                "policy_name": r[1],
                "category": r[2] or "청년지원",
                "matches_count": r[3],
                "views_count": r[4],
                "clicks_count": r[5],
                "score": r[6],
                "last_accessed": str(r[7])
            })
    except Exception as e:
        print(f"[!] get_popular_policies error: {e}")
    finally:
        conn.close()
    return results

def get_user_activity_logs(limit: int = 100, action_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    conn, _ = get_db_conn()
    cur = conn.cursor()
    logs = []
    try:
        if action_filter:
            cur.execute("""
                SELECT id, user_id, user_email, user_name, action, details, ip_address, created_at
                FROM user_activity_logs
                WHERE action LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (f"%{action_filter}%", limit))
        else:
            cur.execute("""
                SELECT id, user_id, user_email, user_name, action, details, ip_address, created_at
                FROM user_activity_logs
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        rows = cur.fetchall()
        for r in rows:
            logs.append({
                "id": r[0],
                "user_id": r[1],
                "user_email": r[2],
                "user_name": r[3],
                "action": r[4],
                "details": r[5],
                "ip_address": r[6],
                "created_at": str(r[7])
            })
    except Exception as e:
        print(f"[!] get_user_activity_logs error: {e}")
    finally:
        conn.close()
    return logs

def get_service_operation_logs(limit: int = 100, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    conn, _ = get_db_conn()
    cur = conn.cursor()
    logs = []
    try:
        if status_filter == "error":
            cur.execute("""
                SELECT id, method, path, status_code, duration_ms, client_ip, error_msg, created_at
                FROM service_logs
                WHERE status_code >= 400
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        elif status_filter == "success":
            cur.execute("""
                SELECT id, method, path, status_code, duration_ms, client_ip, error_msg, created_at
                FROM service_logs
                WHERE status_code < 400
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        else:
            cur.execute("""
                SELECT id, method, path, status_code, duration_ms, client_ip, error_msg, created_at
                FROM service_logs
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        rows = cur.fetchall()
        for r in rows:
            logs.append({
                "id": r[0],
                "method": r[1],
                "path": r[2],
                "status_code": r[3],
                "duration_ms": r[4],
                "client_ip": r[5],
                "error_msg": r[6],
                "created_at": str(r[7])
            })
    except Exception as e:
        print(f"[!] get_service_operation_logs error: {e}")
    finally:
        conn.close()
    return logs
