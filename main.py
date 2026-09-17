import os
import sys
import json
from typing import Optional, Dict, Any
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from scripts import db_connection
from services.diagnosis_engine import diagnose_policies, get_all_policies

app = FastAPI(
    title="YouthFit AI - 청년 복지 정책 AI 비서",
    description="온통청년 및 지자체 청년 정책 DB 기반 1분 맞춤 진단 및 서류 패키지 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. 정적 에셋 서빙 마운트
web_dir = os.path.join(BASE_DIR, "web")
css_dir = os.path.join(web_dir, "css")
js_dir = os.path.join(web_dir, "js")
data_dir = os.path.join(BASE_DIR, "data")

if os.path.exists(css_dir):
    app.mount("/css", StaticFiles(directory=css_dir), name="css")
if os.path.exists(js_dir):
    app.mount("/js", StaticFiles(directory=js_dir), name="js")
if os.path.exists(data_dir):
    app.mount("/data", StaticFiles(directory=data_dir), name="data")

# 2. HTML 웹 페이지 라우팅
@app.get("/")
@app.get("/index.html")
async def serve_index():
    return FileResponse(os.path.join(web_dir, "index.html"))

@app.get("/diagnosis")
@app.get("/diagnosis.html")
async def serve_diagnosis():
    return FileResponse(os.path.join(web_dir, "diagnosis.html"))

@app.get("/loading")
@app.get("/loading.html")
async def serve_loading():
    return FileResponse(os.path.join(web_dir, "loading.html"))

@app.get("/dashboard")
@app.get("/dashboard.html")
async def serve_dashboard():
    return FileResponse(os.path.join(web_dir, "dashboard.html"))

@app.get("/auth")
@app.get("/auth.html")
async def serve_auth():
    return FileResponse(os.path.join(web_dir, "auth.html"))

@app.get("/explorer")
@app.get("/explorer.html")
async def serve_explorer():
    return FileResponse(os.path.join(web_dir, "explorer.html"))

# 3. REST API 정의
class DiagnosisRequest(BaseModel):
    age: int = 24
    region: Optional[str] = "서울"
    regionFull: Optional[str] = "서울특별시"
    district: str = "관악구"
    jobStatus: str = "jobseeker"
    household: str = "single"
    income: str = "income60"

@app.post("/api/diagnose")
async def api_diagnose(req: DiagnosisRequest):
    """
    1분 맞춤 문진 데이터를 받아 AI 판별 및 수혜액/체크리스트 리포트를 반환합니다.
    """
    try:
        profile = req.model_dump()
        result = diagnose_policies(profile)
        return JSONResponse(content={"status": "success", "data": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

try:
    from services.auth_service import (
        signup_user, login_user, authenticate_google_user, 
        save_user_diagnosis, get_user_profile, update_user_profile
    )
except ImportError:
    pass

class SignupRequest(BaseModel):
    email: str
    name: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    email: str
    name: Optional[str] = "구글 회원"
    google_id: Optional[str] = ""

class SaveDiagnosisRequest(BaseModel):
    user_id: int
    profile: Dict[str, Any]
    diagnosis_result: Dict[str, Any]

class UpdateProfileRequest(BaseModel):
    user_id: int
    profile: Dict[str, Any]

@app.post("/api/auth/signup")
async def api_signup(req: SignupRequest):
    """이메일/비밀번호 신규 회원가입"""
    try:
        res = signup_user(req.email, req.name, req.password)
        return JSONResponse(content={"status": "success", "data": res})
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 처리 중 오류: {str(e)}")

@app.post("/api/auth/login")
async def api_login(req: LoginRequest):
    """이메일/비밀번호 로그인 인증"""
    try:
        res = login_user(req.email, req.password)
        return JSONResponse(content={"status": "success", "data": res})
    except ValueError as ve:
        raise HTTPException(status_code=401, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 처리 중 오류: {str(e)}")

@app.post("/api/auth/google")
async def api_google_auth(req: GoogleAuthRequest):
    """Google 소셜 계정 원클릭 로그인 / 회원가입"""
    try:
        res = authenticate_google_user(req.email, req.name, req.google_id)
        return JSONResponse(content={"status": "success", "data": res})
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google 로그인 처리 중 오류: {str(e)}")

@app.post("/api/user/save-diagnosis")
async def api_save_diagnosis(req: SaveDiagnosisRequest):
    """로그인한 회원의 최근 진단 결과 및 조건 저장"""
    try:
        success = save_user_diagnosis(req.user_id, req.profile, req.diagnosis_result)
        return JSONResponse(content={"status": "success", "saved": success})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"진단 저장 오류: {str(e)}")

@app.post("/api/user/update-profile")
async def api_update_profile(req: UpdateProfileRequest):
    """로그인한 회원의 프로필 조건 저장"""
    try:
        success = update_user_profile(req.user_id, req.profile)
        return JSONResponse(content={"status": "success", "saved": success})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프로필 저장 오류: {str(e)}")

@app.get("/api/user/profile")
async def api_get_profile(user_id: int = Query(...)):
    """로그인한 회원의 프로필 및 최근 진단 이력 조회"""
    try:
        data = get_user_profile(user_id)
        return JSONResponse(content={"status": "success", "data": data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프로필 조회 오류: {str(e)}")


@app.get("/api/policies")
async def api_get_policies(
    category: Optional[str] = Query(None, description="대분류 (예: 일자리, 주거, 금융･복지･문화, 교육･직업훈련)"),
    keyword: Optional[str] = Query(None, description="검색 키워드 (예: 월세, 면접, 수당)"),
    region: Optional[str] = Query(None, description="지역 필터 (예: 서울, 경기, 부산, 광주 등)"),
    age: Optional[int] = Query(None, description="만 나이 필터"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    적재된 데이터베이스로부터 정책 목록을 검색/페이징하여 반환합니다.
    """
    try:
        all_p = get_all_policies()
        filtered = []
        for p in all_p:
            if category and category != "전체" and category not in (p.get("category_large") or ""):
                continue
            if keyword:
                kw = keyword.lower()
                name = (p.get("name") or "").lower()
                content = (p.get("support_content") or "").lower()
                expl = (p.get("explanation") or "").lower()
                sup = (p.get("supervising_inst") or "").lower()
                op = (p.get("operating_inst") or "").lower()
                if kw not in name and kw not in content and kw not in expl and kw not in sup and kw not in op:
                    continue
            if region and region != "전체":
                reg_kw = region.lower()
                sup = (p.get("supervising_inst") or "").lower()
                op = (p.get("operating_inst") or "").lower()
                name = (p.get("name") or "").lower()
                zip_c = (p.get("zip_codes") or "").lower()
                if reg_kw not in sup and reg_kw not in op and reg_kw not in name and reg_kw not in zip_c:
                    continue
            if age is not None:
                min_a = p.get("min_age", 0) or 0
                max_a = p.get("max_age", 99) or 99
                lmt = p.get("age_limit_yn", "Y")
                if lmt == "Y" and (age < min_a or age > max_a):
                    continue
            filtered.append(p)

        total_count = len(filtered)
        paginated = filtered[offset:offset + limit]

        return JSONResponse(content={
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "policies": paginated
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/policies/{policy_id}")
async def api_get_policy_detail(policy_id: str):
    """
    정책 상세 정보를 조회합니다.
    """
    all_p = get_all_policies()
    for p in all_p:
        if str(p.get("policy_id")) == str(policy_id):
            return JSONResponse(content=p)
    raise HTTPException(status_code=404, detail=f"Policy ID '{policy_id}' not found")

@app.get("/api/stats")
async def api_get_stats():
    """
    전체 정책 통계 요약을 반환합니다.
    """
    all_p = get_all_policies()
    total = len(all_p)
    
    cat_counts: Dict[str, int] = {}
    for p in all_p:
        c = p.get("category_large") or "미분류"
        cat_counts[c] = cat_counts.get(c, 0) + 1

    return JSONResponse(content={
        "total_policies": total,
        "categories": cat_counts,
        "supported_age_group": "만 19세 ~ 34세 청년",
        "service": "유스핏 AI (YouthFit AI)"
    })

@app.get("/api/health")
async def api_health():
    """
    데이터베이스 연결 상태 및 서버 헬스체크
    """
    db_engine = "unknown"
    if db_connection:
        try:
            _, db_type = db_connection.get_connection(allow_sqlite_fallback=True)
            db_engine = db_type
        except Exception:
            db_engine = "disconnected"

    return JSONResponse(content={
        "status": "healthy",
        "db_engine": db_engine,
        "policies_loaded": len(get_all_policies())
    })

if __name__ == "__main__":
    import uvicorn
    # 로컬 실행 시 윈도우 브라우저에서 바로 클릭할 수 있도록 127.0.0.1 기본 적용
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    is_prod = os.getenv("ENVIRONMENT", "").lower() in ["production", "prod"]
    print("\n" + "="*60)
    print(f" [YouthFit AI] 서버가 성공적으로 시작되었습니다!")
    print(f" -> 브라우저 접속 주소: http://127.0.0.1:{port}")
    print(f" -> 또는 로컬 주소:   http://localhost:{port}")
    print("="*60 + "\n")
    uvicorn.run("main:app", host=host, port=port, reload=not is_prod)



