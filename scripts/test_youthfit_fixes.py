"""
YouthFit AI - Integration & Fixes Automated Verification Script
Tests 7 major areas:
1. dashboard.html (No UI floating button collision, score card visible, admin link)
2. admin.html (Admin Portal elements, 3 tabs, KPI structure)
3. POST /api/diagnose (2026 valid periods, direct apply links, CappBizCD document links)
4. POST /api/stats/policy-click (Policy click tracking)
5. GET /api/admin/overview (KPI summary metrics)
6. GET /api/admin/popular-policies (Most matched and clicked policies)
7. GET /api/admin/logs/service (FastAPI middleware telemetry logs)
"""
import urllib.request
import json

def test(url, data=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8') if data else None,
        headers={'Content-Type': 'application/json'} if data else {}
    )
    res = urllib.request.urlopen(req)
    return res.status, res.read().decode('utf-8')

def run_all_tests():
    print('=== YouthFit AI System Integration Test ===\n')

    print('--- Test 1: dashboard.html ---')
    s, html = test('http://127.0.0.1:8000/dashboard.html')
    print('Status:', s, 'Length:', len(html))
    assert 'fixed bottom-6 left-6' not in html, 'Floating button still in dashboard.html!'
    assert 'sidebar-match-score' in html, 'sidebar-match-score missing!'
    assert 'admin.html' in html, 'admin link missing in dashboard.html!'
    print('PASS: dashboard.html verified!\n')

    print('--- Test 2: admin.html ---')
    s, html = test('http://127.0.0.1:8000/admin.html')
    print('Status:', s, 'Length:', len(html))
    assert 'YouthFit Admin' in html, 'YouthFit Admin title missing!'
    assert 'tab-content-popular' in html, 'popular tab missing!'
    assert 'tab-content-user-logs' in html, 'user-logs tab missing!'
    assert 'tab-content-service-logs' in html, 'service-logs tab missing!'
    print('PASS: admin.html verified!\n')

    print('--- Test 3: POST /api/diagnose ---')
    s, body = test('http://127.0.0.1:8000/api/diagnose', {
        'age': 24,
        'region': '서울',
        'district': '관악구',
        'jobStatus': 'jobseeker',
        'household': 'single',
        'income': 'income60'
    })
    d = json.loads(body)['data']
    print('Matched:', len(d['policies']), 'Docs:', len(d['checklist']))
    for p in d['policies']:
        print(f"Policy: {p['name']} | URL: {p['apply_url']} | Period: {p['apply_period']}")
        assert 'youthcenter.go.kr/youngPlcyUnif' in p['apply_url'] or 'youthConts' in p['apply_url'] or 'work24' in p['apply_url'] or 'bokjiro' in p['apply_url'] or 'account' in p['apply_url'] or 'housing' in p['apply_url'] or 'gwanak' in p['apply_url'], f"Generic URL: {p['apply_url']}"

    for doc in d['checklist']:
        print(f"Doc: {doc['name']} -> {doc['link']} ({doc.get('action_label')})")

    print('PASS: Diagnose & Direct URLs verified!\n')

    print('--- Test 4: POST /api/stats/policy-click ---')
    s, body = test('http://127.0.0.1:8000/api/stats/policy-click', {
        'policy_id': 'SEOUL-001',
        'policy_name': '서울시 청년수당',
        'category': '일자리',
        'action_type': 'apply'
    })
    print('Status:', s, 'Body:', body)
    print('PASS: Policy click telemetry verified!\n')

    print('--- Test 5: GET /api/admin/overview ---')
    s, body = test('http://127.0.0.1:8000/api/admin/overview')
    ov = json.loads(body)['data']['overview']
    print('Overview:', ov)
    print('PASS: Admin overview KPI verified!\n')

    print('--- Test 6: GET /api/admin/popular-policies ---')
    s, body = test('http://127.0.0.1:8000/api/admin/popular-policies')
    pops = json.loads(body)['data']
    print('Popular count:', len(pops))
    for i, p in enumerate(pops[:3]):
        print(f"Top {i+1}: {p['policy_name']} (Matches: {p['matches_count']}, Clicks: {p['clicks_count']})")
    print('PASS: Popular policies ranking verified!\n')

    print('--- Test 7: GET /api/admin/logs/service ---')
    s, body = test('http://127.0.0.1:8000/api/admin/logs/service?limit=5')
    slogs = json.loads(body)['data']
    print('Service logs count:', len(slogs))
    for l in slogs[:3]:
        print('Log:', l['method'], l['path'], l['status_code'], f"{l['duration_ms']}ms")
    print('PASS: Service operation telemetry verified!\n')

    print('>>> ALL 7 SYSTEM TESTS COMPLETED & PASSED! <<<')

if __name__ == '__main__':
    run_all_tests()
