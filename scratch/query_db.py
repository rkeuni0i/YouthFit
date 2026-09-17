import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")
from scripts.db_connection import get_connection

conn, db_type = get_connection()
cur = conn.cursor()
cur.execute("SELECT policy_id, name, supervising_inst, operating_inst FROM policies WHERE name LIKE '%월세%' OR supervising_inst LIKE '%광주%' OR supervising_inst LIKE '%전남%'")
rows = cur.fetchall()
print(f"Total matching policies: {len(rows)}")
for r in rows[:15]:
    name = r[1] or ""
    sup = r[2] or ""
    print(f"- [{r[0]}] {name} (주관: {sup})")
conn.close()
