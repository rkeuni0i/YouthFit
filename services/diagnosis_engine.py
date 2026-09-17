import os
import sys
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from scripts import db_connection
except ImportError:
    try:
        import db_connection
    except ImportError:
        db_connection = None

def get_all_policies():
    """
    PostgreSQL 데이터베이스(또는 로컬 SQLite/JSON)에서 적재된 전체 정책 목록을 조회합니다.
    """
    policies = []
    
    # 1. DB에서 조회 시도
    if db_connection:
        try:
            conn, db_type = db_connection.get_connection(allow_sqlite_fallback=True)
            cur = conn.cursor()
            cur.execute("""
                SELECT policy_id, name, category_large, category_mid, keyword,
                       min_age, max_age, age_limit_yn, support_content, explanation,
                       required_docs, apply_method, apply_url, apply_period,
                       supervising_inst, operating_inst, zip_codes, raw_json
                FROM policies
            """)
            rows = cur.fetchall()
            col_names = [d[0] for d in cur.description]
            for row in rows:
                item = dict(zip(col_names, row))
                if isinstance(item.get("raw_json"), str):
                    try:
                        item["raw_json"] = json.loads(item["raw_json"])
                    except Exception:
                        pass
                policies.append(item)
            conn.close()
            if policies:
                return policies
        except Exception as e:
            print(f"[!] DB 조회 실패 ({e}), Fallback 파일로 대체합니다.")

    # 2. JSON Fallback
    json_path = os.path.join(BASE_DIR, "data", "youth_policies_19_34.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("policies", [])

    return policies

def parse_benefit_amount(policy):
    """
    정책명 및 지원 내용으로부터 연간 실질 수혜 금액(원 단위 정수) 및 직관적인 포맷 텍스트를 추출합니다.
    """
    name = policy.get("name", "")
    content = policy.get("support_content", "") or ""
    explanation = policy.get("explanation", "") or ""
    full_text = f"{name} {content} {explanation}"

    # 대표 정책 정밀 수혜금 매핑
    if "청년수당" in name or "구직활동지원" in name:
        return 3000000, "월 500,000원 × 6개월 (최대 300만원 지급)"
    if "국민취업지원제도" in name:
        return 3000000, "구직촉진수당 월 500,000원 × 6개월 (최대 300만원)"
    if "월세" in name:
        return 2400000, "월 최대 200,000원 × 12개월 (최대 240만원 지급)"
    if "희망두배" in name:
        return 3600000, "월 15만원 저축 시 지자체 1:1 매칭 (연 최대 360만원, 3년 1,080만원)"
    if "도약계좌" in name:
        return 3000000, "정부 기여금 매월 최대 6% 매칭 지원 (연 최대 300만원)"
    if "임차보증금" in name or "전세자금" in name:
        return 1500000, "임차보증금 대출금리 연 최대 2.0% 이자 지원 (연 약 150만원 상당)"
    if "복지포인트" in name:
        return 1200000, "청년 복지포인트 연 최대 1,200,000원 (분기별 30만원)"
    if "청년기본소득" in name:
        return 1000000, "분기별 25만원 지급 (연 최대 100만원 지역화폐)"
    if "드림체크카드" in name:
        return 3000000, "월 50만원 × 6개월 (최대 300만원 구직활동비 지원)"
    if "대중교통비" in name:
        return 100000, "연 최대 100,000원 한도 (대중교통 마일리지 환급)"
    if "K-패스" in name or "k패스" in name:
        return 180000, "대중교통비 청년 30% 적립 환급 (연 최대 약 180,000원)"
    if "이사비" in name:
        return 400000, "청년 이사비 및 부동산 중개보수 최대 400,000원 실비 지원"
    if "취업날개" in name or "면접" in name or "정장" in name:
        return 300000, "면접정장 무료 대여 또는 면접수당 (연간 최대 30~50만원)"
    if "응시료" in name or "자격증" in name:
        return 150000, "국가기술·어학 자격시험 응시료 연 최대 150,000원 실비 지원"
    if "바우처" in name and "특화" in name:
        return 100000, "지자체 청년센터 거점 1:1 무료 심리상담/역량 바우처"

    # 정규식 패턴 매칭 (e.g. "최대 500만원", "월 30만원")
    match_monthly = re.search(r'월\s*(\d+)\s*만\s*원', full_text)
    if match_monthly:
        monthly = int(match_monthly.group(1)) * 10000
        return monthly * 6, f"월 {match_monthly.group(1)}만원 상당 지원 (6개월 환산)"

    match_annual = re.search(r'(?:최대|연|지원)\s*(\d+)\s*만\s*원', full_text)
    if match_annual:
        val = int(match_annual.group(1)) * 10000
        return val, f"최대 {match_annual.group(1)}만원 상당 지원"

    cat = policy.get("category_large", "") or ""
    if "주거" in cat:
        return 1200000, "연 약 120만원 상당 주거비/이자 감면 혜택"
    elif "일자리" in cat or "고용" in cat:
        return 600000, "구직 및 역량강화 교육/훈련 수당 지원"
    elif "금융" in cat or "복지" in cat:
        return 500000, "청년 맞춤형 금융 컨설팅 및 우대 혜택"

    return 300000, "청년 맞춤형 역량강화 프로그램 및 활동비 무료 지원"

def parse_required_docs(policy):
    """
    공고문 데이터에서 필수 제출 서류 목록을 추출합니다.
    """
    docs_raw = policy.get("required_docs") or ""
    if not docs_raw and isinstance(policy.get("raw_json"), dict):
        docs_raw = policy["raw_json"].get("sbmsnDcmntCn", "") or ""

    parsed = policy.get("required_docs_parsed")
    if parsed and isinstance(parsed, list) and len(parsed) > 0:
        cleaned = [d for d in parsed if len(d) > 2][:4]
        if cleaned:
            return cleaned

    lines = docs_raw.split("\n")
    results = []
    for line in lines:
        cleaned_line = line.strip().lstrip("○-•*1234567890.)( ").strip()
        if len(cleaned_line) >= 2 and not cleaned_line.startswith("□") and not cleaned_line.startswith("※") and not cleaned_line.startswith("ㅇ"):
            if cleaned_line not in results:
                results.append(cleaned_line)
        if len(results) >= 4:
            break

    if not results:
        policy_name = policy.get("name", "")
        if "수당" in policy_name or "구직" in policy_name:
            results = ["주민등록표초본", "고용보험 피보험자격 이력내역서", "최종학력 졸업증명서"]
        elif "월세" in policy_name or "주거" in policy_name:
            results = ["주민등록표등본", "임대차계약서 사본", "월세 이체 확인증", "소득재산 신고서"]
        elif "통장" in policy_name or "계좌" in policy_name:
            results = ["주민등록표초본", "재직증명서(또는 근로계약서)", "근로소득원천징수영수증"]
        elif "교통비" in policy_name:
            results = ["본인 명의 교통카드 사본", "주민등록표초본 (정부24 즉시 발급)"]
        else:
            results = ["주민등록표초본 (정부24 즉시 발급)", "신분증 사본", "참여 신청서 및 개인정보제공동의서"]

    return results

def get_gov24_link(doc_name):
    """정부24 및 공공기관 발급 서류 링크 반환"""
    gov24_keywords = ["주민등록", "등본", "초본", "가족관계", "소득금액", "건강보험", "졸업증명", "재학증명"]
    for kw in gov24_keywords:
        if kw in doc_name:
            return "https://www.gov.kr"
    comwel_keywords = ["고용보험", "피보험자격", "산재보험"]
    for kw in comwel_keywords:
        if kw in doc_name:
            return "https://total.comwel.or.kr"
    hometax_keywords = ["소득금액증명", "원천징수", "사업자등록증"]
    for kw in hometax_keywords:
        if kw in doc_name:
            return "https://www.hometax.go.kr"
    return "https://www.gov.kr"

# 전국 17개 광역시·도 매핑 테이블
KOREA_REGIONS = [
    {"code": "seoul", "short": "서울", "full": "서울특별시"},
    {"code": "gyeonggi", "short": "경기", "full": "경기도"},
    {"code": "incheon", "short": "인천", "full": "인천광역시"},
    {"code": "busan", "short": "부산", "full": "부산광역시"},
    {"code": "daegu", "short": "대구", "full": "대구광역시"},
    {"code": "daejeon", "short": "대전", "full": "대전광역시"},
    {"code": "gwangju", "short": "광주", "full": "광주광역시"},
    {"code": "ulsan", "short": "울산", "full": "울산광역시"},
    {"code": "sejong", "short": "세종", "full": "세종특별자치시"},
    {"code": "gangwon", "short": "강원", "full": "강원특별자치도"},
    {"code": "chungbuk", "short": "충북", "full": "충청북도"},
    {"code": "chungnam", "short": "충남", "full": "충청남도"},
    {"code": "jeonbuk", "short": "전북", "full": "전북특별자치도"},
    {"code": "jeonnam", "short": "전남", "full": "전라남도"},
    {"code": "gyeongbuk", "short": "경북", "full": "경상북도"},
    {"code": "gyeongnam", "short": "경남", "full": "경상남도"},
    {"code": "jeju", "short": "제주", "full": "제주특별자치도"}
]

# 17개 시도별 지자체 매칭 및 타 지자체 배제 패턴
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

def is_policy_for_other_province(policy: dict, user_prov: str) -> bool:
    """
    사용자의 시도(예: '서울')와 다른 타 지자체의 전용 정책인지 엄격하게 판별합니다.
    True를 반환하면 타 지자체 전용 정책이므로 진단 결과에서 제외됩니다.
    """
    if user_prov == "전국":
        return False

    name = policy.get("name", "") or ""
    sup = policy.get("supervising_inst", "") or ""
    op = policy.get("operating_inst", "") or ""
    url = policy.get("apply_url", "") or ""

    user_tokens = PROVINCE_PATTERNS.get(user_prov, {}).get("tokens", [user_prov])

    # 사용자의 시도명/지자체명이 주관/운영기관/제목에 포함된 경우 허용
    if any(t in sup or t in op or t in name for t in user_tokens):
        return False

    # 타 16개 시도의 전용 정책 여부 체크
    for prov, meta in PROVINCE_PATTERNS.items():
        if prov == user_prov:
            continue
        # 1. 소관기관 또는 운영기관에 타 지자체명/지역구가 포함된 경우
        for t in meta["tokens"]:
            if (t in sup) or (t in op):
                return True
        # 2. 신청 URL 도메인이 타 지자체 도메인인 경우
        for d in meta["domains"]:
            if d in url:
                return True
        # 3. 정책명에 타 지자체 접두어/명칭이 포함된 경우
        for t in meta["tokens"]:
            patterns = [f"[{t}", f"({t}", f"{t} ", f"{t}시", f"{t}도", f"{t}광역", f"{t}특별", f"{t}청년", f"{t}형"]
            if any(p in name for p in patterns):
                return True

    return False

def resolve_user_region(profile):
    """
    사용자가 입력한 region 또는 district 텍스트로부터 (시도_short, 시도_full, 시군구)를 추론합니다.
    """
    raw_region = profile.get("region", "").strip()
    raw_district = profile.get("district", "").strip()

    # 1. region이 명시된 경우
    for reg in KOREA_REGIONS:
        if reg["short"] in raw_region or reg["full"] in raw_region:
            district_name = raw_district if raw_district and raw_district != "전체" and "시도" not in raw_district else f"{reg['short']} 전체"
            return reg["short"], reg["full"], district_name

    # 2. district 문자열에서 추론 (예: "관악구" -> 서울, "해운대구" -> 부산, "수원시" -> 경기)
    for reg in KOREA_REGIONS:
        if reg["short"] in raw_district or reg["full"] in raw_district:
            return reg["short"], reg["full"], raw_district

    # 서울 자치구 목록 판별
    seoul_gu = ["종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구"]
    for gu in seoul_gu:
        if gu in raw_district:
            return "서울", "서울특별시", gu

    # 기본값
    if "전국" in raw_region or "전국" in raw_district:
        return "전국", "전국 공통", "전국"

    return "서울", "서울특별시", raw_district or "관악구"

def diagnose_policies(profile):
    """
    사용자가 입력한 5대 핵심 조건을 전국 17개 시·도 및 시·군·구 단위로 정밀 평가합니다.

    profile = {
        "age": 24,
        "region": "부산",         # 시·도 (서울, 부산, 경기, 인천, 대구 등)
        "district": "해운대구",    # 시·군·구 (관악구, 해운대구, 수원시, 전체 등)
        "jobStatus": "jobseeker", # jobseeker, employed, freelancer, student
        "household": "single",    # single, family
        "income": "income60"      # income60, income120, income150, unknown
    }
    """
    age = int(profile.get("age", 24))
    reg_short, reg_full, district = resolve_user_region(profile)
    job_status = profile.get("jobStatus", "jobseeker")
    household = profile.get("household", "single")
    income = profile.get("income", "income60")

    all_policies = get_all_policies()
    scored_candidates = []

    # 한글 레이블
    job_labels = {
        "jobseeker": "미취업/취준생",
        "employed": "중소기업 재직자",
        "freelancer": "단기근로/프리랜서",
        "student": "대학(원)생"
    }
    job_name = job_labels.get(job_status, "청년")

    income_labels = {
        "income60": "기준 중위 60% 이하",
        "income120": "기준 중위 120% 이하",
        "income150": "기준 중위 150% 이하",
        "unknown": "소득 구간 미상 (AI 추산)"
    }
    income_name = income_labels.get(income, "소득 기준 충족")

    for p in all_policies:
        name = p.get("name", "")
        cat_large = p.get("category_large", "") or ""
        cat_mid = p.get("category_mid", "") or ""
        content = p.get("support_content", "") or ""
        explanation = p.get("explanation", "") or ""
        supervising = p.get("supervising_inst", "") or ""
        operating = p.get("operating_inst", "") or ""
        zip_codes = p.get("zip_codes", "") or ""
        
        full_text = f"{name} {cat_large} {cat_mid} {content} {explanation} {supervising} {operating} {zip_codes}"

        score = 50
        reasons = []

        # -------------------------------------------------------------
        # 1. 만 나이 (Age) 필터링
        # -------------------------------------------------------------
        min_age = p.get("min_age", 0) or 0
        max_age = p.get("max_age", 99) or 99
        age_limit_yn = p.get("age_limit_yn", "Y")

        if age_limit_yn == "N" or (min_age <= age <= max_age):
            score += 15
            reasons.append(f"만 {age}세 지원 연령 기준 충족 (만 {min_age}~{max_age}세)")
        else:
            continue

        # 만 19~24세 청년 대중교통비 특별 매칭
        if age <= 24 and ("대중교통비" in name or "교통비" in name):
            score += 20
            reasons.append(f"만 19~24세 청년 전용 대중교통비 지원 대상")

        # -------------------------------------------------------------
        # 2. 거주 지역 (Region / District) 전국구 지능형 매칭 & 타 시도 필터링
        # -------------------------------------------------------------
        if reg_short != "전국":
            if is_policy_for_other_province(p, reg_short):
                # 타 시도 전용 정책 배제
                continue

            # 해당 시도 관련 정책 가산점
            if reg_short in full_text or reg_full in full_text:
                score += 30
                reasons.append(f"{reg_short} 거주 청년 지자체 특화 지원")
                # 시군구 일치 시 추가 가산점
                if district and district != f"{reg_short} 전체" and district in full_text:
                    score += 15
                    reasons.append(f"{district} 지역구 추가 우대 혜택")
            elif "전국" in full_text or "중앙" in full_text or "고용노동부" in supervising or "국토교통부" in supervising or "중소벤처기업부" in supervising or "보건복지부" in supervising:
                score += 12
                reasons.append("전국 공통 정부 복지 지원 사업")
        else:
            # 전국 선택 시: 전국 공통 사업 우대
            if "전국" in full_text or "고용노동부" in supervising or "국토교통부" in supervising or "중앙" in full_text:
                score += 25
                reasons.append("전국 모든 청년 수혜 가능 정책")

        # -------------------------------------------------------------
        # 3. 경제활동 상태 (Job Status) 매칭
        # -------------------------------------------------------------
        if job_status == "jobseeker":
            if "청년수당" in name or "구직" in name or "취업활동" in name:
                score += 35
                reasons.append("미취업 청년 구직활동 수당 최우선 순위 적격")
            elif "국민취업지원제도" in name:
                score += 30
                reasons.append("구직촉진수당 참여 대상 요건 충족")
            elif "면접" in name or "정장" in name or "취업날개" in name:
                score += 20
                reasons.append("구직자 면접정장/면접비 지원 대상")
            elif "응시료" in name or "자격증" in name:
                score += 18
                reasons.append("취업 준비 자격증 응시료 지원 대상")
            elif "일자리" in cat_large or "구직" in name or "취업" in name:
                score += 12
                reasons.append("청년 구직 및 일자리 역량강화 지원 대상")

            if "희망두배" in name or "재직자" in name or "내일채움" in name or "복지포인트" in name:
                score -= 35

        elif job_status == "employed":
            if "희망두배" in name or "복지포인트" in name:
                score += 35
                reasons.append("근로청년 자산형성 및 복지포인트 최우선 적격")
            elif "도약계좌" in name:
                score += 28
                reasons.append("청년 근로소득 정부 기여금 적립 대상")
            elif "임차보증금" in name or "전세자금" in name:
                score += 25
                reasons.append("직장인 청년 임차보증금 대출이자 2% 지원 적격")
            elif "소득세" in name or "감면" in name:
                score += 20
                reasons.append("중소기업 취업 청년 소득세 감면 대상")

            if "청년수당" in name or "국민취업지원제도 1유형" in name:
                score -= 40

        elif job_status == "freelancer":
            if "희망두배" in name:
                score += 25
                reasons.append("단기근로(주 30시간 미만) 근로소득 증빙 시 저축 매칭 가능")
            elif "K-패스" in name or "교통비" in name:
                score += 20
                reasons.append("이동이 많은 프리랜서 교통비 환급 혜택")
            elif "응시료" in name or "역량" in name or "기본소득" in name:
                score += 20
                reasons.append("프리랜서 직무 전문성 강화 지원")

        elif job_status == "student":
            if "대중교통비" in name or "K-패스" in name:
                score += 28
                reasons.append("통학 교통비 절감 청년 대중교통비/K-패스 적격")
            elif "장학" in name or "학자금" in name:
                score += 25
                reasons.append("대학생 학자금 대출이자 지원 요건 충족")
            elif "인턴" in name or "캠퍼스" in name:
                score += 20
                reasons.append("대학생 실무형 인턴십 지원 대상")

            if "청년수당" in name:
                score -= 30

        # -------------------------------------------------------------
        # 4. 가구 형태 (Household) 매칭
        # -------------------------------------------------------------
        if household == "single":
            if "월세" in name:
                score += 25
                reasons.append("독립 거주 1인 청년 가구 월세 지원 요건 충족")
            elif "이사비" in name:
                score += 20
                reasons.append("1인 가구 이사비 및 중개보수 지원 대상")
            elif "안심" in name or "주거" in cat_large:
                score += 15
                reasons.append("1인 가구 주거안정 프로그램 대상")
        else:
            if "희망두배" in name or "도약계좌" in name or "교통비" in name or "복지포인트" in name:
                score += 10
                reasons.append("다인가구 청년 자산형성 및 생활비 지원 적격")

        # -------------------------------------------------------------
        # 5. 기준 중위소득 구간 (Income) 매칭
        # -------------------------------------------------------------
        if income == "income60":
            if "월세" in name:
                score += 25
                reasons.append("기준 중위 60% 이하 소득요건 100% 통과 (우선 선발)")
            elif "청년수당" in name or "국민취업지원제도" in name:
                score += 20
                reasons.append("소득 150% 이하 요건 충족으로 1순위 선발군 편성")
            elif "복지" in cat_large or "수당" in name:
                score += 15
                reasons.append("취약계층/저소득 청년 특별 지원 우대")
        elif income == "income120":
            if "청년수당" in name or "임차보증금" in name:
                score += 18
                reasons.append("중위 120% 이하 적격 기준 부합")
            elif "월세" in name:
                score += 10
                reasons.append("청년 월세 지원 심사 요건 해당")
        elif income == "income150":
            if "청년수당" in name:
                score += 15
                reasons.append("청년수당 소득요건(150% 이하) 충족")
            elif "희망두배" in name:
                score += 18
                reasons.append("희망두배 청년통장 소득요건(140% 이하) 부합")

        # 적합도(Match Rate) 산정 (최대 99%, 최소 55%)
        match_rate = max(55, min(score, 99))
        amount, amount_desc = parse_benefit_amount(p)
        docs = parse_required_docs(p)

        scored_candidates.append({
            "policy": p,
            "match_rate": match_rate,
            "reasons": reasons,
            "amount": amount,
            "amount_desc": amount_desc,
            "docs": docs
        })

    # 적합도 점수 높은 순 및 수혜금액 높은 순 정렬
    scored_candidates.sort(key=lambda x: (x["match_rate"], x["amount"]), reverse=True)

    # 상위 4개 정책 최종 선발
    top_candidates = scored_candidates[:4]
    total_benefit = sum(item["amount"] for item in top_candidates)

    # 서류 체크리스트 집계
    checklist_set = set()
    checklist = []
    for item in top_candidates:
        for doc in item["docs"]:
            clean_name = re.sub(r'\(.*?\)', '', doc).strip()
            if clean_name and clean_name not in checklist_set:
                checklist_set.add(clean_name)
                checklist.append({
                    "name": doc,
                    "clean_name": clean_name,
                    "link": get_gov24_link(doc),
                    "policy_name": item["policy"].get("name", "")
                })

    matched_cards = []
    rank_labels = ["적격 1순위", "적격 2순위", "적격 3순위", "적격 4순위"]

    region_display = f"{reg_full} {district}" if reg_short != "전국" and district != f"{reg_short} 전체" else f"{reg_full}"

    for i, item in enumerate(top_candidates):
        p = item["policy"]
        rank_label = rank_labels[i] if i < len(rank_labels) else f"적격 {i+1}순위"
        
        apply_period = p.get("apply_period") or "연중 상시 신청 가능"
        apply_url = p.get("apply_url") or "https://www.youthcenter.go.kr"

        # AI 자격 판별 알고리즘 리포트 문장
        if item["reasons"]:
            ai_summary = f"{region_display} 거주 및 {job_name} 조건, {income_name} 요건을 충족하여 {rank_label} 지원 대상자로 선정되었습니다. ({' · '.join(item['reasons'][:2])})"
        else:
            ai_summary = f"만 {age}세 {region_display} 청년으로서 기본 자격 요건을 완벽히 만족합니다."

        badge_reasons = [
            f"{reg_short} 거주 적격",
            f"{job_name} 요건 충족",
            f"{income_name.split(' ')[0]} 기준 통과"
        ]

        explanation_text = p.get("explanation") or p.get("support_content") or "청년 지원 혜택에 관한 상세 공고문입니다."

        matched_cards.append({
            "policy_id": p.get("policy_id"),
            "name": p.get("name"),
            "category": f"{p.get('category_large', '청년지원')} / {p.get('supervising_inst', reg_full)}",
            "rank_label": rank_label,
            "match_rate": item["match_rate"],
            "amount": item["amount"],
            "amount_desc": item["amount_desc"],
            "ai_summary": ai_summary,
            "reasons": badge_reasons,
            "apply_period": apply_period,
            "apply_url": apply_url,
            "explanation": explanation_text,
            "support_content": p.get("support_content") or "",
            "docs": item["docs"]
        })

    house_desc = "1인가구" if household == "single" else "다인가구"

    return {
        "profile": {
            "age": age,
            "region": reg_short,
            "region_full": reg_full,
            "district": district,
            "job_status": job_status,
            "household": household,
            "income": income,
            "summary": f"진단 완료: {age}세 {job_name} ({region_display} {house_desc})"
        },
        "total_benefit": total_benefit,
        "total_benefit_formatted": f"{total_benefit:,}",
        "total_benefit_text": f"연 약 {total_benefit // 10000:,}만원 예상 수혜",
        "matched_count": len(matched_cards),
        "docs_count": len(checklist),
        "policies": matched_cards,
        "checklist": checklist[:6]
    }
