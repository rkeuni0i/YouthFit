FROM python:3.10-slim

WORKDIR /app

# 기본 환경변수 설정 (Python 버퍼링 해제 및 Cloud Run 기본 포트)
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# 시스템 라이브러리 설치 (psycopg2 빌드 의존성)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 의존성 설치 (캐시 레이어 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 전체 소스 복사
COPY . .

# 실행 포트 노출
EXPOSE 8080

# 컨테이너 시작 명령어 (Cloud Run의 $PORT 환경 변수 자동 반영)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
