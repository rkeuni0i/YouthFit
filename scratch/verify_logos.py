import os

web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
html_files = [f for f in os.listdir(web_dir) if f.endswith(".html")]

print(f"Found {len(html_files)} HTML files: {html_files}")

all_passed = True
for f in sorted(html_files):
    filepath = os.path.join(web_dir, f)
    with open(filepath, "r", encoding="utf-8") as fp:
        content = fp.read()
    
    has_favicon = "favicon.ico" in content and "youthfit-icon.svg" in content
    # admin.html has inline SVG text logo, other user-facing pages have img logos
    has_logo = ("YouthFit-Logo/svg/youthfit-logo-primary.svg" in content and "YouthFit-Logo/svg/youthfit-logo-darkbg.svg" in content) or ("YouthFit" in content and f == "admin.html")

    status = "OK" if (has_favicon and has_logo) else "FAIL"
    print(f"[{status}] {f}: favicon={has_favicon}, logo={has_logo}")
    if status != "OK":
        all_passed = False

if all_passed:
    print("\nALL HTML PAGES SUCCESSFULLY VERIFIED WITH ACTIVE ICONS & LOGOS!")
else:
    print("\nSOME PAGES FAILED CHECKS.")
