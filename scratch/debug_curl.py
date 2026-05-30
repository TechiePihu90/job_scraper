import asyncio

async def test_curl(cmd):
    print(f"\nRunning command: {' '.join(cmd)}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    print(f"Return code: {proc.returncode}")
    text = stdout.decode('utf-8', errors='ignore')
    print(f"Length of response: {len(text)}")
    print(f"Response preview: {text[:200]}")
    if "Human Verification" in text:
        print("  -> Result: BLOCKED BY WAF")
    else:
        print("  -> Result: SUCCESS")

async def main():
    url = "https://careers-hcsgcorp.icims.com/jobs/search?pr=0&in_iframe=1"
    
    # Test 1: C:\Windows\System32\curl.exe without custom headers
    await test_curl(["C:\\Windows\\System32\\curl.exe", "-s", "-L", url])
    
    # Test 2: C:\Windows\System32\curl.exe with -A User-Agent
    await test_curl(["C:\\Windows\\System32\\curl.exe", "-s", "-L", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", url])

if __name__ == "__main__":
    asyncio.run(main())
