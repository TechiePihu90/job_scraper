import urllib.request

subdomain = "woggleconsulting"
# Wait, let's also try "technomap" or others
subdomains = ["woggleconsulting", "technomap", "al-fahad"]

paths = [
    "/rss",
]

for sub in subdomains:
    for path in paths:
        url = f"https://{sub}.zohorecruit.com{path}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')
            print(f"Success: {url} -> Content Length: {len(content)}")
            print("Preview:")
            print(content[:500])
            break
        except Exception as e:
            pass
            # print(f"Failed: {url} -> {e}")
