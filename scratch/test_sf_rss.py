import urllib.request

urls = [
    "https://jobs.sap.com/search/?q=&feed=rss",
    "https://jobs.sap.com/search/?q=&feed=xml",
    "https://jobs.sap.com/testingsitemap.xml",
    "https://jobs.sap.com/sitemap.xml",
    "https://jobs.sap.com/feed/",
]

for url in urls:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
        print(f"Success: {url} -> Content Length: {len(content)}")
        print("Preview:")
        print(content[:500])
        print("---")
    except Exception as e:
        print(f"Failed: {url} -> {e}")
