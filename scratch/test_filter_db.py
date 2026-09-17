import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")
from scripts.db_connection import get_connection

conn, _ = get_connection()
cur = conn.cursor()
cur.execute("SELECT policy_id, name, supervising_inst, operating_inst, apply_url FROM policies")
rows = cur.fetchall()
conn.close()

print(f"Total policies in DB: {len(rows)}")

PROVINCE_PATTERNS = {
    "서울": {"tokens": ["서울", "서울특별시", "서울시"], "domains": ["seoul.go.kr"]},
    "경기": {"tokens": ["경기", "경기도", "수원", "용인", "고양", "성남", "화성", "부천", "남양주", "안산", "평택", "안양", "시흥", "파주", "김포", "의정부", "하남", "광명", "군포", "양주", "오산", "이천", "안성", "구리", "의왕", "포천"], "domains": ["gg.go.kr", "jobaba.net"]},
    "인천": {"tokens": ["인천", "인천광역시", "인천시", "제물포", "미추홀", "연수구", "남동구", "부평구", "계양구", "강화군", "옹진군"], "domains": ["incheon.go.kr"]},
    "부산": {"tokens": ["부산", "부산광역시", "부산시", "해운대", "사하구", "금정구", "연제구", "수영구", "사상구", "기장군"], "domains": ["busan.go.kr"]},
    "대구": {"tokens": ["대구", "대구광역시", "대구시", "달서구", "달성군", "수성구"], "domains": ["daegu.go.kr"]},
    "대전": {"tokens": ["대전", "대전광역시", "대전시", "유성구", "대덕구"], "domains": ["daejeon.go.kr"]},
    "광주": {"tokens": ["광주", "광주광역시", "광주시", "전남광주", "광주전남", "광산구"], "domains": ["gwangju.go.kr"]},
    "울산": {"tokens": ["울산", "울산광역시", "울산시", "울주군"], "domains": ["ulsan.go.kr"]},
    "세종": {"tokens": ["세종", "세종특별자치시", "세종시"], "domains": ["sejong.go.kr"]},
    "강원": {"tokens": ["강원", "강원도", "강원특별자치도", "춘천", "원주", "강릉"], "domains": ["gwd.go.kr", "gangwon.go.kr"]},
    "충북": {"tokens": ["충북", "충청북도", "청주", "충주", "제천"], "domains": ["chungbuk.go.kr"]},
    "충남": {"tokens": ["충남", "충청남도", "천안", "아산", "서산", "당진", "공주", "보령", "논산"], "domains": ["chungnam.go.kr"]},
    "전북": {"tokens": ["전북", "전라북도", "전북특별자치도", "전주", "군산", "익산", "정읍", "남원", "김제", "완주"], "domains": ["jeonbuk.go.kr"]},
    "전남": {"tokens": ["전남", "전라남도", "전남광주", "광주전남", "화순", "나주", "영암", "광양", "목포", "여수", "순천", "해남", "담양", "완도", "진도", "신안"], "domains": ["jeonnam.go.kr"]},
    "경북": {"tokens": ["경북", "경상북도", "포항", "구미", "경주", "안동", "김천", "경산", "칠곡"], "domains": ["gb.go.kr"]},
    "경남": {"tokens": ["경남", "경상남도", "창원", "김해", "진주", "양산", "거제", "통영", "사천"], "domains": ["gyeongnam.go.kr"]},
    "제주": {"tokens": ["제주", "제주도", "제주특별자치도", "서귀포"], "domains": ["jeju.go.kr"]}
}

def is_other_province(policy, user_prov):
    if user_prov == "전국":
        return False
    name = policy["name"] or ""
    sup = policy["supervising_inst"] or ""
    op = policy["operating_inst"] or ""
    url = policy["apply_url"] or ""

    user_tokens = PROVINCE_PATTERNS.get(user_prov, {}).get("tokens", [user_prov])

    # If already explicitly targeting user province or national
    is_user_prov = any(t in sup or t in op or t in name for t in user_tokens)
    if is_user_prov:
        return False

    for prov, meta in PROVINCE_PATTERNS.items():
        if prov == user_prov:
            continue
        # Check supervising or operating
        for t in meta["tokens"]:
            if (t in sup) or (t in op):
                return True
        # Check domain
        for d in meta["domains"]:
            if d in url:
                return True
        # Check title patterns
        for t in meta["tokens"]:
            patterns = [f"[{t}", f"({t}", f"{t} ", f"{t}시", f"{t}도", f"{t}광역", f"{t}특별", f"{t}청년", f"{t}형"]
            if any(p in name for p in patterns):
                return True
    return False

# Test for Seoul
seoul_kept = []
seoul_excluded = []
for r in rows:
    p = {"name": r[1], "supervising_inst": r[2], "operating_inst": r[3], "apply_url": r[4]}
    if is_other_province(p, "서울"):
        seoul_excluded.append(p)
    else:
        seoul_kept.append(p)

print(f"For Seoul: Kept {len(seoul_kept)}, Excluded {len(seoul_excluded)}")
# Check if any 전남광주 leaked into seoul_kept
leaked = [p for p in seoul_kept if "전남" in (p['supervising_inst'] or "") or "광주" in (p['supervising_inst'] or "")]
print(f"Leaked other-province policies in Seoul: {len(leaked)}")
print("\nSample Kept Policies for Seoul:")
for p in seoul_kept[:10]:
    print(f" - {p['name']} (주관: {p['supervising_inst']})")
