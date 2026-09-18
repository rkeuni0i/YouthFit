@echo off
chcp 65001 > nul
echo ========================================================
echo  YouthFit AI - Google Cloud Run 자동 배포 스크립트
echo ========================================================
echo.

:: gcloud 실행 파일 경로 탐색
where gcloud >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set GCLOUD_CMD=gcloud
) else if exist "%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" (
    set GCLOUD_CMD="%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
) else (
    set GCLOUD_CMD=gcloud
)

set PROJECT_ID=iceu-songpa04
set REGION=asia-northeast3
set SERVICE_NAME=youthfit

echo [1/3] GCP 설정 확인 중 (프로젝트: %PROJECT_ID%, 리전: %REGION%)...
call %GCLOUD_CMD% config set project %PROJECT_ID%
call %GCLOUD_CMD% config set run/region %REGION%

echo.
echo [2/3] Cloud Run 배포 시작 (소스로부터 원격 Cloud Build 빌드 및 배포)...
call %GCLOUD_CMD% run deploy %SERVICE_NAME% ^
    --source . ^
    --project %PROJECT_ID% ^
    --region %REGION% ^
    --allow-unauthenticated ^
    --env-vars-file env.yaml ^
    --platform managed

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================================
    echo  [성공] YouthFit AI 가 Cloud Run에 성공적으로 배포되었습니다!
    echo ========================================================
    call %GCLOUD_CMD% run services describe %SERVICE_NAME% --project %PROJECT_ID% --region %REGION% --format="value(status.url)"
) else (
    echo.
    echo [!] 배포 중 오류가 발생했습니다. 로그를 확인해 주세요.
)

pause
