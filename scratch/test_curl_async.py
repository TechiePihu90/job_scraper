import asyncio

async def fetch_url_with_curl(url: str) -> str:
    cmd = [
        "curl",
        "-s",
        "-L",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "-H", "Accept-Language: en-US,en;q=0.9",
        url
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise Exception(f"curl failed with code {proc.returncode}: {stderr.decode('utf-8', errors='ignore')}")
    return stdout.decode('utf-8', errors='ignore')

async def main():
    url = "https://careers-hcsgcorp.icims.com/jobs/search?pr=0&in_iframe=1"
    try:
        print(f"Fetching {url} using async curl subprocess...")
        html_content = await fetch_url_with_curl(url)
        print(f"Success! Fetched {len(html_content)} characters.")
        print(f"Preview: {html_content[:300]}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
