import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Test the regional screening logic
sys.path.insert(0, "c:/Users/2003g/Documents/Project_sesac/YouthFit")
from services.diagnosis_engine import diagnose_policies

# Test with a user from Seoul Nowon-gu
profile = {
    "age": 24,
    "region": "서울",
    "district": "노원구",
    "jobStatus": "jobseeker",
    "household": "single",
    "income": "income60"
}

res = diagnose_policies(profile)
print("Keys:", res.keys())
top_policies = res.get("policies", [])
print(f"Total top recommendations for Seoul Nowon-gu: {len(top_policies)}")
leaked = []
for p in top_policies:
    name = p.get("name", "")
    sup = p.get("supervising_inst", "")
    op = p.get("operating_inst", "")
    print(f"Policy: {name} | Sup: {sup}")
    if "전남" in name or "광주" in name or "전남" in sup or "광주" in sup or "화순" in sup or "경기" in name:
        leaked.append((name, sup))

if leaked:
    print("LEAK DETECTED with current engine:")
    for item in leaked:
        print(" -", item)
else:
    print("NO LEAK DETECTED.")
