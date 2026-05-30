#!/usr/bin/env python3
"""Debug ICIMS portals to reverse-engineer API endpoints."""

import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs


async def debug_icims_portal(portal_url: str):
    """Debug an ICIMS portal to find actual API endpoints."""
    print(f"\n{'='*60}")
    print(f"Debugging ICIMS Portal: {portal_url}")
    print(f"{'='*60}")
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Show browser for inspection
            page = await browser.new_page()
            
            # Intercept network requests
            network_requests = []
            
            async def handle_request(route):
                request = route.request
                network_requests.append({
                    "method": request.method,
                    "url": request.url,
                    "headers": dict(request.headers),
                    "post_data": request.post_data,
                })
                await route.continue_()
            
            await page.route("**/*", handle_request)
            
            # Navigate to the portal
            print(f"\n→ Loading portal...")
            await page.goto(portal_url, wait_until="networkidle")
            
            # Wait for potential infinite scroll
            print("→ Waiting for content to load...")
            try:
                await page.wait_for_selector(".job-posting, .job-card, [data-job-id], .position", timeout=5000)
            except:
                print("⚠️  No job listings found with common selectors")
            
            # Scroll to trigger more requests
            print("→ Scrolling to load more jobs...")
            for i in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
            
            # Check for API calls in network traffic
            print("\n" + "="*60)
            print("NETWORK REQUESTS DETECTED")
            print("="*60)
            
            api_calls = [r for r in network_requests if any(x in r["url"].lower() for x in ["api", "jobs", "search", "listing", "position"])]
            
            if not api_calls:
                api_calls = [r for r in network_requests if r["method"] in ["GET", "POST"]][:20]
            
            for i, req in enumerate(api_calls, 1):
                print(f"\n[{i}] {req['method']} {req['url']}")
                
                # Check for query parameters
                parsed = urlparse(req["url"])
                if parsed.query:
                    params = parse_qs(parsed.query)
                    print(f"    Query params: {json.dumps(params, indent=6)}")
                
                # Check for POST data
                if req["post_data"]:
                    try:
                        post_json = json.loads(req["post_data"])
                        print(f"    POST data: {json.dumps(post_json, indent=6)}")
                    except:
                        print(f"    POST data: {req['post_data'][:200]}")
                
                # Check for authorization headers
                auth_headers = {k: v for k, v in req["headers"].items() if "auth" in k.lower() or "token" in k.lower() or "bearer" in v.lower()}
                if auth_headers:
                    print(f"    Auth headers: {json.dumps(auth_headers, indent=6)}")
            
            # Extract job data from HTML
            print("\n" + "="*60)
            print("EXTRACTED JOB DATA")
            print("="*60)
            
            html = await page.content()
            
            # Try various extraction patterns
            patterns = {
                "data-job-id": r'data-job-id["\']?\s*[:=]\s*["\']?(\d+)',
                "jobId": r'"jobId"\s*[:=]\s*["\']?(\d+)',
                "job_id": r'"job_id"\s*[:=]\s*["\']?(\d+)',
                "title in script": r'"title"\s*[:=]\s*"([^"]{10,100})"',
            }
            
            found_data = {}
            for pattern_name, pattern in patterns.items():
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    found_data[pattern_name] = matches[:5]  # First 5 matches
            
            if found_data:
                print("Patterns found in HTML:")
                for pattern_name, matches in found_data.items():
                    print(f"  {pattern_name}: {matches}")
            else:
                print("⚠️  No obvious job data patterns found in HTML")
            
            # Check for embedded JSON in script tags
            print("\nSearching for embedded JSON...")
            script_patterns = [
                r'window\.__data__\s*=\s*({.*?})',
                r'window\.icims\s*=\s*({.*?})',
                r'"jobs"\s*:\s*(\[{.*?}\])',
            ]
            
            for pattern in script_patterns:
                matches = re.findall(pattern, html, re.DOTALL)
                if matches:
                    print(f"✓ Found embedded JSON with pattern: {pattern}")
                    try:
                        data = json.loads(matches[0][:1000])
                        print(f"  Sample: {json.dumps(data, indent=2)[:500]}")
                    except:
                        print(f"  (Could not parse JSON)")
            
            # Print recommendations
            print("\n" + "="*60)
            print("RECOMMENDATIONS")
            print("="*60)
            
            if api_calls:
                print("\n1. API Endpoint found!")
                print("   Copy the job-related API URL and update ICIMSScraper")
                print("   Look for URLs containing: /jobs, /search, /listings, /positions")
            
            if found_data:
                print("\n2. Job data is embedded in HTML")
                print("   Update HTML parsing patterns to extract job IDs and data")
            
            print("\n3. For more details:")
            print("   - Keep browser window open (headless=False) to inspect manually")
            print("   - Check DevTools → Network tab for API calls")
            print("   - Check DevTools → Console for any errors")
            
            # Keep browser open for manual inspection
            print("\n⏳ Keeping browser open for inspection (press Ctrl+C to close)...")
            try:
                await asyncio.sleep(300)  # 5 minutes
            except KeyboardInterrupt:
                print("\nClosed.")
            
            await browser.close()
    
    except Exception as e:
        print(f"✗ Debug failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main entry point."""
    print("=" * 60)
    print("🔍 ICIMS PORTAL DEBUGGER")
    print("=" * 60)
    
    # Get portal URL from user
    portal_url = input("\nEnter ICIMS portal URL (e.g., https://example.icims.com/jobs/search/results):\n> ").strip()
    
    if not portal_url.startswith("http"):
        portal_url = "https://" + portal_url
    
    if not await debug_icims_portal(portal_url):
        print("\n✗ Debugging failed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
