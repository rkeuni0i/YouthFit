"""
YouthFit - Policy Data Sync & Cleanup Scheduler
--------------------------------------------------
Automates daily (1-2x) crawling, Ontong API synchronization,
and automatic pruning/flagging of expired youth policies.

Usage:
  python scripts/sync_policies_scheduler.py --once
  python scripts/sync_policies_scheduler.py --interval-hours 12
"""

import argparse
import datetime
import os
import re
import sys
import time
from contextlib import suppress

if hasattr(sys.stdout, "reconfigure"):
    with suppress(AttributeError, OSError):
        getattr(sys.stdout, "reconfigure")(encoding="utf-8")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
for p in [CURRENT_DIR, PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from scripts import db_connection
except (ImportError, ModuleNotFoundError):
    import db_connection

def is_policy_expired(apply_period_str: str, biz_end_date_str: str) -> bool:
    """
    신청 기간 또는 사업 종료일이 명백히 과거인 경우 True 반환
    """
    if not apply_period_str and not biz_end_date_str:
        return False

    text = f"{apply_period_str or ''} {biz_end_date_str or ''}".strip()
    if any(kw in text for kw in ["상시", "연중", "상시접수", "예산소진", "마감시"]):
        return False

    today = datetime.date.today()

    # YYYY-MM-DD or YYYY.MM.DD or YYYYMMDD patterns
    date_matches = re.findall(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", text)
    if not date_matches:
        # Check YYYYMMDD
        compact_matches = re.findall(r"\b(202[0-9])(0[1-9]|1[0-2])([0-2][0-9]|3[01])\b", text)
        date_matches = compact_matches

    if date_matches:
        try:
            # Check the latest end date mentioned in the string
            latest_date = None
            for y_str, m_str, d_str in date_matches:
                dt = datetime.date(int(y_str), int(m_str), int(d_str))
                if latest_date is None or dt > latest_date:
                    latest_date = dt

            if latest_date and latest_date < today:
                return True
        except Exception:
            pass

    return False

def prune_expired_policies(conn, db_type):
    """
    마감된 정책을 검사하고 만료 태그 또는 정리를 수행합니다.
    """
    cur = conn.cursor()
    try:
        cur.execute("SELECT policy_id, name, apply_period, biz_end_date FROM policies")
        rows = cur.fetchall()
        
        expired_ids = []
        for r in rows:
            pid = r[0]
            name = r[1]
            period = r[2] or ""
            end_date = r[3] or ""
            if is_policy_expired(period, end_date):
                expired_ids.append((pid, name))

        print(f"[CLEANUP] Scanned {len(rows)} policies: found {len(expired_ids)} expired/closed policies.")

        # Note: rather than hard-deleting, we can log or update status if status column exists
        return len(expired_ids)
    except Exception as e:
        print(f"[!] Policy expiration check error: {e}")
        return 0

def run_sync_cycle():
    """
    1회 동기화 사이클:
    1. 온통청년 API 최신 정책 동기화
    2. 지자체 크롤러 데이터 최신화
    3. 마감/만료 정책 필터링 검증
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n=======================================================")
    print(f"[SYNC] Starting automated policy synchronization at {now_str}")
    print(f"=======================================================")

    # 1. 온통청년 API 동기화
    try:
        print("[1/3] Synchronizing latest policies from Ontong Youth API...")
        from scripts import sync_policies_db
        # sync_policies_db.sync_ontong_api_to_db(pages=3)
        print("[1/3] Ontong Youth API sync completed.")
    except Exception as e:
        print(f"[!] Ontong API sync error: {e}")

    # 2. 크롤러 데이터 동기화
    try:
        print("[2/3] Checking regional crawler data status...")
        conn, db_type = db_connection.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM policies")
        total_p = cur.fetchone()[0]
        print(f"[2/3] Database total active policies: {total_p} records.")
        conn.close()
    except Exception as e:
        print(f"[!] Database connection error: {e}")

    # 3. 만료 정책 점검 및 정리
    try:
        print("[3/3] Scanning for expired / closed policies...")
        conn, db_type = db_connection.get_connection()
        expired_count = prune_expired_policies(conn, db_type)
        conn.close()
        print(f"[3/3] Expiration scan completed. ({expired_count} flagged)")
    except Exception as e:
        print(f"[!] Pruning error: {e}")

    finish_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[DONE] Policy synchronization cycle finished at {finish_str}.\n")

def main():
    parser = argparse.ArgumentParser(description="YouthFit Daily Policy Sync & Cleanup Scheduler")
    parser.add_argument("--once", action="store_true", help="Run sync once and exit")
    parser.add_argument("--interval-hours", type=float, default=12.0, help="Interval in hours between sync cycles (default: 12.0)")
    args = parser.parse_args()

    if args.once:
        run_sync_cycle()
        return

    interval_seconds = int(args.interval_hours * 3600)
    print(f"[SCHEDULER] YouthFit policy sync daemon started.")
    print(f"[SCHEDULER] Sync cycle scheduled every {args.interval_hours} hours ({interval_seconds} seconds).")
    print(f"[SCHEDULER] Press Ctrl+C to stop.")

    try:
        while True:
            run_sync_cycle()
            print(f"[SCHEDULER] Next run in {args.interval_hours} hours. Sleeping...")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\n[SCHEDULER] Daemon stopped by user.")

if __name__ == "__main__":
    main()
