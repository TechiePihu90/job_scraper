import urllib.request
import re

url = "https://woggleconsulting.zohorecruit.com/jobs/Careers"

try:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    )
    with urllib.request.urlopen(req) as response:
        html_content = response.read().decode('utf-8')
    print("Fetched successfully. Content length:", len(html_content))
    print("HTML Content:")
    print(html_content[:2000])

except Exception as e:
    print("Error:", e)
