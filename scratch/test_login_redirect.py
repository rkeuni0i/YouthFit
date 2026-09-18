import requests

test_cases = [
    ('admin', 'admin1234!'),
    ('admin@youthfit.kr', 'admin1234!'),
    ('admin', 'admin'),
    ('admin', 'admin1234'),
    ('user@youthfit.kr', 'user1234!'),
]

for email, password in test_cases:
    res = requests.post('http://127.0.0.1:8000/api/auth/login', json={'email': email, 'password': password})
    print(f"Test '{email}' / '{password}': Status {res.status_code}")
    if res.status_code == 200:
        data = res.json()['data']
        print(f"   -> ID: {data.get('id')}, Email: {data.get('email')}, Role: {data.get('role')}")
    else:
        print(f"   -> Error: {res.text}")
