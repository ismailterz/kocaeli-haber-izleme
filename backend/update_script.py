import re

with open("/Users/ismailuslu/Desktop/yazlab1/kocaeli-haber-izleme/backend/scraper/base_scraper.py", "r") as f:
    content = f.read()

pattern = r"        def _get_with_uc\(\):.*?return None"
# The fetch in fetch_page
replacement = '''        def _get_with_uc():
            try:
                from curl_cffi import requests as crequests
                resp = crequests.get(url, impersonate="chrome110", timeout=20)
                if resp.status_code == 200 and "Just a moment" not in resp.text and "Bir dakika" not in resp.text:
                    resp.encoding = resp.apparent_encoding
                    return resp.text
            except Exception as e:
                print(f"Curl_cffi error in fetch_page: {e}")
            return None'''

# We already replaced the one in fetch_text, we just need to replace the second one.
parts = content.split("        def _get_with_uc():")
if len(parts) == 3:
    # First part is before first _get_with_uc, second part is fetch_text's _get_with_uc, third part is fetch_page's _get_with_uc
    content = parts[0] + "        def _get_with_uc():" + parts[1] + replacement + parts[2][parts[2].find("        last_err = None"):]

    with open("/Users/ismailuslu/Desktop/yazlab1/kocaeli-haber-izleme/backend/scraper/base_scraper.py", "w") as f:
        f.write(content)
