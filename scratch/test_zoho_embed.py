import urllib.request
import json

url = "https://recruit.zoho.com/ats/EmbedResult.hr?jodigest=zoho&rawdata=json"

try:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    )
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('utf-8')
    print("Content length:", len(content))
    print("Content preview:")
    print(content[:1000])
    
    # Try parsing as JSON
    data = json.loads(content)
    print("Parsed JSON keys:", data.keys() if isinstance(data, dict) else type(data))
except Exception as e:
    print("Error:", e)
