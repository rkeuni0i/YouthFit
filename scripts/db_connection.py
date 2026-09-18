import json
import os
import sqlite3
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

SQLITE_FALLBACK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "youthfit.db"
)

_fallback_warned = False

def get_database_url():
    """
    환경 변수에서 데이터베이스 연결 문자열을 가져옵니다.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "youthfit")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

def is_postgres():
    url = get_database_url()
    return url.startswith(("postgresql://", "postgres://"))

def get_connection(allow_sqlite_fallback=False):
    """
    데이터베이스 연결 객체를 생성하여 반환합니다.
    기본적으로 PostgreSQL을 사용하며, 실패 시 allow_sqlite_fallback이 True면 SQLite로 대체합니다.
    """
    url = get_database_url()

    global _fallback_warned
    if is_postgres():
        if not PSYCOPG2_AVAILABLE:
            if allow_sqlite_fallback:
                if not _fallback_warned:
                    print("[!] psycopg2 모듈 미설치로 SQLite 데이터베이스로 대체합니다.")
                    _fallback_warned = True
                os.makedirs(os.path.dirname(SQLITE_FALLBACK_PATH), exist_ok=True)
                return sqlite3.connect(SQLITE_FALLBACK_PATH), "sqlite"
            raise RuntimeError(
                "psycopg2 모듈이 설치되어 있지 않습니다.\n"
                "다음 명령어로 설치해주세요: pip install psycopg2-binary"
            )
        try:
            conn = psycopg2.connect(url, connect_timeout=3)
            return conn, "postgresql"
        except psycopg2.OperationalError as e:
            if allow_sqlite_fallback:
                if not _fallback_warned:
                    print(f"[!] PostgreSQL 연결 실패 ({e}). SQLite로 임시 대체합니다.")
                    _fallback_warned = True
                os.makedirs(os.path.dirname(SQLITE_FALLBACK_PATH), exist_ok=True)
                return sqlite3.connect(SQLITE_FALLBACK_PATH), "sqlite"
            else:
                parsed = urlparse(url)
                masked_netloc = f"{parsed.username}:***@{parsed.hostname}:{parsed.port}"
                raise ConnectionError(
                    f"\n{'='*65}\n"
                    f"[!] PostgreSQL 데이터베이스에 연결할 수 없습니다.\n"
                    f" • 대상 서버: {masked_netloc}{parsed.path}\n"
                    f" • 오류 원인: {e}\n"
                    f"\n[해결 방법]\n"
                    f" 1. PostgreSQL 서비스 또는 Docker 컨테이너가 실행 중인지 확인하세요.\n"
                    f" 2. .env 파일의 DATABASE_URL 설정(호스트, 포트, 계정, 비밀번호)을 확인하세요.\n"
                    f" 3. 임시로 SQLite를 사용하려면 fallback 옵션을 활용할 수 있습니다.\n"
                    f"{'='*65}\n"
                ) from e
    else:
        # SQLite
        path = url.replace("sqlite:///", "") if url.startswith("sqlite:///") else SQLITE_FALLBACK_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return sqlite3.connect(path), "sqlite"

def init_db(conn=None):
    """
    데이터베이스 테이블 및 인덱스를 생성/초기화합니다.
    """
    close_conn = False
    if conn is None:
        conn, db_type = get_connection(allow_sqlite_fallback=True)
        close_conn = True
    else:
        db_type = "postgresql" if "psycopg2" in str(type(conn)) else "sqlite"

    if conn is None:
        raise ConnectionError("데이터베이스에 연결할 수 없습니다.")

    cur = conn.cursor()

    if db_type == "postgresql":
        # PostgreSQL DDL
        cur.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            policy_id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(500) NOT NULL,
            category_large VARCHAR(100),
            category_mid VARCHAR(100),
            keyword TEXT,
            min_age INTEGER,
            max_age INTEGER,
            age_limit_yn VARCHAR(10),
            support_content TEXT,
            explanation TEXT,
            required_docs TEXT,
            apply_method TEXT,
            apply_url TEXT,
            apply_period TEXT,
            biz_start_date VARCHAR(50),
            biz_end_date VARCHAR(50),
            supervising_inst VARCHAR(255),
            operating_inst VARCHAR(255),
            zip_codes TEXT,
            raw_json JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # PostgreSQL Indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_policies_age ON policies(min_age, max_age);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_policies_category ON policies(category_large, category_mid);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_policies_name ON policies(name);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_policies_raw_json ON policies USING gin(raw_json);")

        conn.commit()
    else:
        # SQLite DDL
        cur.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            policy_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category_large TEXT,
            category_mid TEXT,
            keyword TEXT,
            min_age INTEGER,
            max_age INTEGER,
            age_limit_yn TEXT,
            support_content TEXT,
            explanation TEXT,
            required_docs TEXT,
            apply_method TEXT,
            apply_url TEXT,
            apply_period TEXT,
            biz_start_date TEXT,
            biz_end_date TEXT,
            supervising_inst TEXT,
            operating_inst TEXT,
            zip_codes TEXT,
            raw_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_age ON policies(min_age, max_age);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_category ON policies(category_large, category_mid);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_name ON policies(name);")
        conn.commit()

    return conn, db_type

def upsert_policy(cur, norm, raw, db_type="postgresql"):
    """
    정책 데이터를 INSERT 또는 UPDATE (UPSERT) 합니다.
    """
    raw_json_str = json.dumps(raw, ensure_ascii=False)

    if db_type == "postgresql":
        query = """
        INSERT INTO policies (
            policy_id, name, category_large, category_mid, keyword,
            min_age, max_age, age_limit_yn, support_content, explanation,
            required_docs, apply_method, apply_url, apply_period,
            biz_start_date, biz_end_date, supervising_inst, operating_inst,
            zip_codes, raw_json
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (policy_id) DO UPDATE SET
            name = EXCLUDED.name,
            category_large = EXCLUDED.category_large,
            category_mid = EXCLUDED.category_mid,
            keyword = EXCLUDED.keyword,
            min_age = EXCLUDED.min_age,
            max_age = EXCLUDED.max_age,
            age_limit_yn = EXCLUDED.age_limit_yn,
            support_content = EXCLUDED.support_content,
            explanation = EXCLUDED.explanation,
            required_docs = EXCLUDED.required_docs,
            apply_method = EXCLUDED.apply_method,
            apply_url = EXCLUDED.apply_url,
            apply_period = EXCLUDED.apply_period,
            biz_start_date = EXCLUDED.biz_start_date,
            biz_end_date = EXCLUDED.biz_end_date,
            supervising_inst = EXCLUDED.supervising_inst,
            operating_inst = EXCLUDED.operating_inst,
            zip_codes = EXCLUDED.zip_codes,
            raw_json = EXCLUDED.raw_json;
        """
        cur.execute(query, (
            norm.get("policy_id", ""),
            norm.get("name", ""),
            norm.get("category_large", ""),
            norm.get("category_mid", ""),
            norm.get("keyword", ""),
            norm.get("min_age", 0) or 0,
            norm.get("max_age", 99) or 99,
            norm.get("age_limit_yn", "Y"),
            norm.get("support_content", ""),
            norm.get("explanation", ""),
            norm.get("required_docs", ""),
            norm.get("apply_method", ""),
            norm.get("apply_url", ""),
            norm.get("apply_period", ""),
            norm.get("biz_start_date", ""),
            norm.get("biz_end_date", ""),
            norm.get("supervising_inst", ""),
            norm.get("operating_inst", ""),
            norm.get("zip_codes", ""),
            raw_json_str
        ))
    else:
        query = """
        INSERT OR REPLACE INTO policies (
            policy_id, name, category_large, category_mid, keyword,
            min_age, max_age, age_limit_yn, support_content, explanation,
            required_docs, apply_method, apply_url, apply_period,
            biz_start_date, biz_end_date, supervising_inst, operating_inst,
            zip_codes, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        cur.execute(query, (
            norm.get("policy_id", ""),
            norm.get("name", ""),
            norm.get("category_large", ""),
            norm.get("category_mid", ""),
            norm.get("keyword", ""),
            norm.get("min_age", 0) or 0,
            norm.get("max_age", 99) or 99,
            norm.get("age_limit_yn", "Y"),
            norm.get("support_content", ""),
            norm.get("explanation", ""),
            norm.get("required_docs", ""),
            norm.get("apply_method", ""),
            norm.get("apply_url", ""),
            norm.get("apply_period", ""),
            norm.get("biz_start_date", ""),
            norm.get("biz_end_date", ""),
            norm.get("supervising_inst", ""),
            norm.get("operating_inst", ""),
            norm.get("zip_codes", ""),
            raw_json_str
        ))
