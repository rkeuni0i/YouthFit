import os

web_dir = r"c:\Users\2003g\Documents\Project_sesac\YouthFit\web"
html_files = [f for f in os.listdir(web_dir) if f.endswith(".html")]

print(f"Found {len(html_files)} HTML files: {html_files}")

all_passed = True
for f in sorted(html_files):
    filepath = os.path.join(web_dir, f)
    with open(filepath, "r", encoding="utf-8") as fp:
        content = fp.read()
    
    has_favicon = "favicon.ico" in content and "youthfit-icon.svg" in content
    has_primary_logo = "assets/logo/svg/youthfit-logo-primary.svg" in content and "dark:hidden" in content
    has_darkbg_logo = "assets/logo/svg/youthfit-logo-darkbg.svg" in content and ("hidden dark:block" in content or "dark:block" in content)

    status = "OK" if (has_favicon and has_primary_logo and has_darkbg_logo) else "FAIL"
    print(f"[{status}] {f}: favicon={has_favicon}, primary_logo={has_primary_logo}, darkbg_logo={has_darkbg_logo}")
    if status != "OK":
        all_passed = False

if all_passed:
    print("\nALL 6 PAGES SUCCESSFULLY VERIFIED WITH ADAPTIVE LIGHT/DARK LOGOS & FAVICON!")
else:
    print("\nSOME PAGES FAILED CHECKS.")
