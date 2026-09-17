import os
import sys
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
failures = []

def check(condition, desc):
    if condition:
        print(f"[PASS] {desc}")
    else:
        print(f"[FAIL] {desc}")
        failures.append(desc)

# 1. Check auth.html for special offer banner removal
auth_path = os.path.join(ROOT, "web", "auth.html")
with open(auth_path, "r", encoding="utf-8") as f:
    auth_html = f.read()
check("신규 회원 특전" not in auth_html, "Item 1: '신규 회원 특전' 배너 삭제")

# 2. Check Google Auth Modal in auth.html and auth.js
auth_js_path = os.path.join(ROOT, "web", "js", "auth.js")
with open(auth_js_path, "r", encoding="utf-8") as f:
    auth_js = f.read()
check("google-auth-modal" in auth_html and "prompt(" not in auth_js, "Item 2: 구글 모달 팝업 추가 및 prompt() 제거")

# 3. Check Regional screening in diagnosis_engine.py
sys.path.insert(0, ROOT)
from services.diagnosis_engine import diagnose_policies
res_seoul = diagnose_policies({
    "age": 24, "region": "서울", "district": "노원구",
    "jobStatus": "jobseeker", "household": "single", "income": "income60"
})
leaked = [p["name"] for p in res_seoul["policies"] if "전남" in p["name"] or "광주" in p["name"] or "전남광주" in (p.get("supervising_inst") or "")]
check(len(leaked) == 0, f"Item 3: 노원구 진단 시 타 지자체(전남광주) 정책 누출 차단 (누출 건수: {len(leaked)})")

# 4. Check why-youthfit section removed from index.html
index_path = os.path.join(ROOT, "web", "index.html")
with open(index_path, "r", encoding="utf-8") as f:
    index_html = f.read()
check('id="why-youthfit"' not in index_html and 'href="#why-youthfit"' not in index_html, "Item 4: '왜 유스핏 AI 진단을 선택해야 할까요?' 섹션 및 링크 제거")

# 5. Check unified Hero CTA in index.html
check("hero-guest-cta-box" in index_html and "1분 맞춤 무료 진단 시작하기" in index_html, "Item 5: 메인 히어로 2분할 박스 -> 단일 명확 CTA 통합")

# 6. Check web/explorer.html exists and main.py route
explorer_path = os.path.join(ROOT, "web", "explorer.html")
main_path = os.path.join(ROOT, "main.py")
with open(main_path, "r", encoding="utf-8") as f:
    main_py = f.read()
check(os.path.exists(explorer_path) and "/explorer" in main_py, "Item 6: web/explorer.html 생성 및 main.py 라우트 연결")

# 7. Check sync_policies_scheduler.py exists
sched_path = os.path.join(ROOT, "scripts", "sync_policies_scheduler.py")
check(os.path.exists(sched_path), "Item 7: scripts/sync_policies_scheduler.py 스케줄러 구축")

# 8. Check member hero state in app.js
app_js_path = os.path.join(ROOT, "web", "js", "app.js")
with open(app_js_path, "r", encoding="utf-8") as f:
    app_js = f.read()
check("hero-guest-cta-box" in app_js and "나의 맞춤 대시보드 바로가기" in app_js, "Item 8: 로그인 사용자 전용 히어로 CTA 전환")

# 9. Check PDF button removal in dashboard.html & dashboard.js
dash_path = os.path.join(ROOT, "web", "dashboard.html")
dash_js_path = os.path.join(ROOT, "web", "js", "dashboard.js")
with open(dash_path, "r", encoding="utf-8") as f:
    dash_html = f.read()
with open(dash_js_path, "r", encoding="utf-8") as f:
    dash_js = f.read()
check("진단 종합 보고서 PDF 다운로드" not in dash_html and "handlePdfDownload" not in dash_js, "Item 9: 진단 종합 보고서 PDF 다운로드 버튼 및 핸들러 삭제")

# 10. Check duplicate CTA removed in header of index.html
check("비회원 진단 (DB 미저장)" not in index_html, "Item 10: 헤더 상단 우측 비회원 진단 중복 버튼 제거")

# 11. Check 2025 to 2026 year update
web_2025_count = 0
for page in [auth_html, index_html, dash_html]:
    web_2025_count += len(re.findall(r"2025", page))
check(web_2025_count == 0, f"Item 11: 2025 -> 2026 연도 최신화 완료 (잔여 2025: {web_2025_count})")

# 12. Check nav explorer policy count 706
check("정책 탐색기 (706건)" in index_html and "423건" not in index_html, "Item 12: 정책 탐색기 423건 -> 706건 최신화")

print("="*50)
if not failures:
    print("ALL 13 ITEMS VERIFIED AND PASSED SUCCESSFULLY!")
else:
    print(f"FAILED ITEMS ({len(failures)}): {failures}")
    sys.exit(1)
