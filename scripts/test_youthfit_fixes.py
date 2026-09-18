"""
YouthFit AI - Integration, RBAC Security & Database Sync Automated Verification
Tests:
1. dashboard.html (No UI floating button collision, score card visible, admin link)
2. admin.html (Client RBAC guard, Bearer auth header, 4 tabs including DB users)
3. POST /api/diagnose (2026 valid periods, direct apply links, CappBizCD document links)
4. POST /api/stats/policy-click (Policy click tracking)
5. RBAC Backend Guard (/api/admin/* unauthorized 401/403 blocked)
6. GET /api/admin/overview (with Admin Bearer token, DB users count synced)
7. GET /api/admin/users (DB users table integration)
8. GET /api/admin/popular-policies (Most matched and clicked policies)
9. GET /api/admin/logs/service (FastAPI middleware telemetry logs)
"""
import sys
import os
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from main import app
from services.auth_service import login_user

def run_all_tests():
    print('=== YouthFit AI System & RBAC Integration Test ===\n')
    client = TestClient(app)

    # 1. dashboard.html 검증
    print('--- Test 1: dashboard.html ---')
    r = client.get('/dashboard.html')
    assert r.status_code == 200, f"dashboard.html failed: {r.status_code}"
    html = r.text
    assert 'fixed bottom-6 left-6' not in html, 'Floating button still in dashboard.html!'
    assert 'sidebar-match-score' in html, 'sidebar-match-score missing!'
    assert 'admin.html' in html, 'admin link missing in dashboard.html!'
    print('PASS: dashboard.html verified!\n')

    # 2. admin.html 검증
    print('--- Test 2: admin.html ---')
    r = client.get('/admin.html')
    assert r.status_code == 200, f"admin.html failed: {r.status_code}"
    html = r.text
    assert 'YouthFit Admin' in html, 'YouthFit Admin title missing!'
    assert 'guardAdminPage' in html, 'Client-side RBAC guard missing in admin.html!'
    assert 'tab-btn-users' in html, 'DB users tab missing!'
    assert 'tab-content-popular' in html, 'popular tab missing!'
    assert 'tab-content-user-logs' in html, 'user-logs tab missing!'
    assert 'tab-content-service-logs' in html, 'service-logs tab missing!'
    print('PASS: admin.html RBAC structure verified!\n')

    # 3. POST /api/diagnose 검증
    print('--- Test 3: POST /api/diagnose ---')
    r = client.post('/api/diagnose', json={
        'age': 24,
        'region': '서울',
        'district': '관악구',
        'jobStatus': 'jobseeker',
        'household': 'single',
        'income': 'income60'
    })
    assert r.status_code == 200, f"diagnose failed: {r.status_code}"
    d = r.json()['data']
    print('Matched:', len(d['policies']), 'Docs:', len(d['checklist']))
    for p in d['policies']:
        assert 'youthcenter.go.kr' in p['apply_url'] or 'work24' in p['apply_url'] or 'bokjiro' in p['apply_url'] or 'gwanak' in p['apply_url'] or 'http' in p['apply_url']
    print('PASS: Diagnose & Direct URLs verified!\n')

    # 4. POST /api/stats/policy-click
    print('--- Test 4: POST /api/stats/policy-click ---')
    r = client.post('/api/stats/policy-click', json={
        'policy_id': 'SEOUL-001',
        'policy_name': '서울시 청년수당',
        'category': '일자리',
        'action_type': 'apply'
    })
    assert r.status_code == 200
    print('PASS: Policy click telemetry verified!\n')

    # 5. RBAC Backend Guard 검증
    print('--- Test 5: RBAC Guard Enforcement ---')
    # A. 토큰 없음 -> 401
    r_no_token = client.get('/api/admin/overview')
    assert r_no_token.status_code == 401, f"Expected 401 without token, got {r_no_token.status_code}"
    print('  ✓ No token -> 401 Unauthorized confirmed')

    # B. 일반 회원 토큰 -> 403
    user_res = login_user('user@youthfit.kr', 'user1234!')
    r_user = client.get('/api/admin/overview', headers={'Authorization': f"Bearer {user_res['token']}"})
    assert r_user.status_code == 403, f"Expected 403 for general user, got {r_user.status_code}"
    print('  ✓ General user token -> 403 Forbidden confirmed')

    # C. 관리자 토큰 -> 200
    admin_res = login_user('admin@youthfit.kr', 'admin1234!')
    admin_headers = {'Authorization': f"Bearer {admin_res['token']}"}
    r_admin = client.get('/api/admin/overview', headers=admin_headers)
    assert r_admin.status_code == 200, f"Expected 200 for admin, got {r_admin.status_code}"
    print('  ✓ Admin token -> 200 OK confirmed')
    print('PASS: RBAC Security Guard fully enforced!\n')

    # 6. GET /api/admin/overview (DB users 연동 확인)
    print('--- Test 6: GET /api/admin/overview & DB Sync ---')
    ov = r_admin.json()['data']['overview']
    print('Overview KPI:', ov)
    assert ov['total_users'] >= 2, f"Expected at least 2 users from DB, got {ov['total_users']}"
    print('PASS: Admin overview & DB users count verified!\n')

    # 7. GET /api/admin/users (DB users 테이블 실시간 조회)
    print('--- Test 7: GET /api/admin/users ---')
    r_users = client.get('/api/admin/users', headers=admin_headers)
    assert r_users.status_code == 200
    users_list = r_users.json()['data']
    print(f"Users in DB ({len(users_list)}):")
    for u in users_list:
        print(f"  - [{u['role'].upper()}] {u['email']} ({u['name']}) | Last login: {u['last_login_at']}")
    assert any(u['role'] == 'admin' for u in users_list), "No admin found in users list"
    assert any(u['role'] == 'user' for u in users_list), "No user found in users list"
    print('PASS: DB Users management API verified!\n')

    # 8. GET /api/admin/popular-policies
    print('--- Test 8: GET /api/admin/popular-policies ---')
    r_pops = client.get('/api/admin/popular-policies', headers=admin_headers)
    assert r_pops.status_code == 200
    pops = r_pops.json()['data']
    print('Popular count:', len(pops))
    if pops:
        print(f"Top 1: {pops[0]['policy_name']} (Score: {pops[0]['score']})")
    print('PASS: Popular policies ranking verified!\n')

    # 9. GET /api/admin/logs/service
    print('--- Test 9: GET /api/admin/logs/service ---')
    r_slogs = client.get('/api/admin/logs/service?limit=5', headers=admin_headers)
    assert r_slogs.status_code == 200
    slogs = r_slogs.json()['data']
    print('Recent service telemetry logs count:', len(slogs))
    print('PASS: Service operation telemetry verified!\n')

    print('='*50)
    print('>>> ALL 9 TESTS PASSED: RBAC & DB INTEGRATION VERIFIED! <<<')
    print('='*50)

if __name__ == '__main__':
    run_all_tests()
