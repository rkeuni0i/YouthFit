import os
import sys
import json
import time
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Query, HTTPException, Request, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from scripts import db_connection
from services.diagnosis_engine import diagnose_policies, get_all_policies
from services import admin_service, auth_service

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

# 웹 서비스 작동 로그 자동 수집 미들웨어
@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    # HTML, JS 파일 및 API 요청에 대해 브라우저 캐시 방지 헤더 설정
    if path.endswith(".html") or path.endswith(".js") or path == "/" or path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "127.0.0.1"
    response = None
    error_msg = None
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        error_msg = str(exc)
        raise exc
    finally:
        duration_ms = (time.time() - start_time) * 1000
        status_code = response.status_code if response else 500
        path = request.url.path
        # 정적 이미지/에셋 제외하고 웹 서비스 작동 및 API 요청만 기록
        if not any(path.startswith(p) for p in ["/css", "/js", "/assets", "/YouthFit-Logo", "/favicon.ico"]):
            admin_service.log_service_request(
                method=request.method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=client_ip,
                error_msg=error_msg
            )

# 1. 정적 에셋 서빙 마운트
web_dir = os.path.join(BASE_DIR, "web")
css_dir = os.path.join(web_dir, "css")
js_dir = os.path.join(web_dir, "js")
assets_dir = os.path.join(web_dir, "assets")
data_dir = os.path.join(BASE_DIR, "data")
logo_dir = os.path.join(BASE_DIR, "YouthFit-Logo")

if os.path.exists(css_dir):
    app.mount("/css", StaticFiles(directory=css_dir), name="css")
if os.path.exists(js_dir):
    app.mount("/js", StaticFiles(directory=js_dir), name="js")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
if os.path.exists(data_dir):
    app.mount("/data", StaticFiles(directory=data_dir), name="data")
if os.path.exists(logo_dir):
    app.mount("/YouthFit-Logo", StaticFiles(directory=logo_dir), name="YouthFit-Logo")

# 2. HTML 웹 페이지 및 정적 에셋 라우팅
@app.get("/favicon.ico")
async def serve_favicon():
    fav_path = os.path.join(web_dir, "favicon.ico")
    if os.path.exists(fav_path):
        return FileResponse(fav_path)
    return JSONResponse(status_code=404, content={"detail": "Favicon not found"})

app.mount("/web", StaticFiles(directory=web_dir, html=True), name="web")
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

@app.get("/admin")
@app.get("/admin.html")
async def serve_admin():
    return FileResponse(os.path.join(web_dir, "admin.html"))

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
async def api_diagnose(req: DiagnosisRequest, request: Request):
    """
    1분 맞춤 문진 데이터를 받아 AI 판별 및 수혜액/체크리스트 리포트를 반환합니다.
    """
    try:
        profile = req.model_dump()
        result = diagnose_policies(profile)
        
        # 사용자 활동 로그 및 인기 정책 매칭 통계 기록
        client_ip = request.client.host if request.client else "127.0.0.1"
        admin_service.log_user_activity(
            action="1분 맞춤진단 실행",
            details=f"연령: {profile.get('age')}세, 지역: {profile.get('region')} {profile.get('district')}, 직업: {profile.get('jobStatus')}, 소득: {profile.get('income')} (매칭 {result.get('matched_count', 0)}건)",
            user_name=f"{profile.get('region')} {profile.get('district')} 청년",
            ip_address=client_ip
        )
        
        for p in result.get("policies", []):
            admin_service.track_policy_match(
                policy_id=str(p.get("policy_id") or p.get("name")),
                policy_name=p.get("name", "청년 정책"),
                category=p.get("category", "청년지원")
            )

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
    credential: Optional[str] = None   # Google OAuth 2.0 / OIDC ID Token (JWT)
    access_token: Optional[str] = None # Google OAuth 2.0 Access Token
    email: Optional[str] = None
    name: Optional[str] = "구글 회원"
    google_id: Optional[str] = ""

class SaveDiagnosisRequest(BaseModel):
    user_id: int
    profile: Dict[str, Any]
    diagnosis_result: Dict[str, Any]

class UpdateProfileRequest(BaseModel):
    user_id: int
    profile: Dict[str, Any]

@app.get("/api/auth/google/config")
async def api_google_config():
    """Google OAuth 2.0 클라이언트 ID 및 설정 반환"""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    return JSONResponse(content={
        "status": "success",
        "client_id": client_id,
        "configured": bool(client_id)
    })

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
    """Google OAuth 2.0 소셜 로그인 / 회원가입 (Token 검증 지원)"""
    import urllib.request
    email = req.email
    name = req.name or "구글 회원"
    google_id = req.google_id or ""

    # 1. Google OAuth 2.0 ID Token (credential) 검증
    if req.credential:
        try:
            url = f"https://oauth2.googleapis.com/tokeninfo?id_token={req.credential}"
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    info = json.loads(resp.read().decode('utf-8'))
                    email = info.get("email", email)
                    name = info.get("name", name)
                    google_id = info.get("sub", google_id)
        except Exception as err:
            print(f"[!] Google tokeninfo verification warning: {err}")

    # 2. Google OAuth 2.0 Access Token 검증
    elif req.access_token:
        try:
            req_info = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {req.access_token}"}
            )
            with urllib.request.urlopen(req_info, timeout=5) as resp:
                if resp.status == 200:
                    info = json.loads(resp.read().decode('utf-8'))
                    email = info.get("email", email)
                    name = info.get("name", name)
                    google_id = info.get("sub", google_id)
        except Exception as err:
            print(f"[!] Google userinfo verification warning: {err}")

    if not email:
        raise HTTPException(status_code=400, detail="유효한 Google 이메일 정보를 확인할 수 없습니다.")

    try:
        res = authenticate_google_user(email, name, google_id)
        return JSONResponse(content={"status": "success", "data": res})
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google OAuth 2.0 로그인 처리 오류: {str(e)}")

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

# 4. 관리자 시스템 및 정책 트래킹 API
class PolicyClickRequest(BaseModel):
    policy_id: str
    policy_name: Optional[str] = ""
    category: Optional[str] = ""
    action_type: Optional[str] = "click" # 'click', 'apply', 'modal_open'

@app.post("/api/stats/policy-click")
async def api_track_policy_click(req: PolicyClickRequest, request: Request):
    """정책 모달 열기 또는 공식 사이트 신청하기 클릭 통계 저장"""
    try:
        admin_service.track_policy_click(
            policy_id=req.policy_id,
            policy_name=req.policy_name,
            category=req.category
        )
        client_ip = request.client.host if request.client else "127.0.0.1"
        action_desc = "공식 사이트 신청 이동" if req.action_type == "apply" else "정책 상세 모달 확인"
        admin_service.log_user_activity(
            action=action_desc,
            details=f"정책: '{req.policy_name}' (ID: {req.policy_id}, 분류: {req.category})",
            ip_address=client_ip
        )
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

# ==========================================
# 관리자 권한(RBAC) 가드 및 관리자 전용 API
# ==========================================

async def require_admin(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    /api/admin/* 엔드포인트 보호용 RBAC 의존성 가드
    요청 헤더 'Authorization: Bearer <token>'을 추출하고 검증하여
    role == 'admin'인 관리자만 접근을 허용합니다.
    """
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="인증 토큰이 누락되었습니다. 관리자 계정으로 로그인해 주세요."
        )
    
    token = authorization.replace("Bearer ", "").strip()
    admin_user = auth_service.verify_admin_token(token)
    if not admin_user:
        raise HTTPException(
            status_code=403, 
            detail="접근 권한이 없습니다. 관리자(admin) 계정만 접속할 수 있습니다."
        )
    return admin_user

@app.get("/api/admin/overview", dependencies=[Depends(require_admin)])
async def api_admin_overview():
    """관리자 종합 지표 (진단수, 사용자수, API호출수, 인기정책 TOP10, 최근로그)"""
    try:
        data = admin_service.get_admin_dashboard_data()
        return JSONResponse(content={"status": "success", "data": data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/logs/user", dependencies=[Depends(require_admin)])
async def api_admin_user_logs(limit: int = Query(50, ge=1, le=500), filter: Optional[str] = None):
    """사용자 활동 로그 조회"""
    try:
        logs = admin_service.get_user_activity_logs(limit=limit, action_filter=filter)
        return JSONResponse(content={"status": "success", "data": logs})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/logs/service", dependencies=[Depends(require_admin)])
async def api_admin_service_logs(limit: int = Query(50, ge=1, le=500), status: Optional[str] = None):
    """웹 서비스 작동 로그 조회"""
    try:
        logs = admin_service.get_service_operation_logs(limit=limit, status_filter=status)
        return JSONResponse(content={"status": "success", "data": logs})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/popular-policies", dependencies=[Depends(require_admin)])
async def api_admin_popular_policies(limit: int = Query(30, ge=1, le=100)):
    """많이 찾는 정책 데이터 및 랭킹 조회"""
    try:
        policies = admin_service.get_popular_policies(limit=limit)
        return JSONResponse(content={"status": "success", "data": policies})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/users", dependencies=[Depends(require_admin)])
async def api_admin_users(limit: int = Query(100, ge=1, le=500)):
    """가입된 전체 회원 목록 및 역할 DB 조회"""
    try:
        users = admin_service.get_all_users(limit=limit)
        return JSONResponse(content={"status": "success", "data": users})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원 목록 조회 오류: {str(e)}")

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



