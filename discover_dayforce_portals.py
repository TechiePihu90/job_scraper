"""Debug script to discover and test actual Dayforce portals."""
import asyncio
import aiohttp
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# List of known Dayforce portal URL patterns and companies
KNOWN_DAYFORCE_PORTALS = [
    # Format: (company_name, subdomain_or_domain, url_pattern)
    ("Accenture", "accenture", "https://accenture.dayforcehcm.com"),
    ("UKG (Ultimate Kronos)", "ukg", "https://ukg.dayforcehcm.com"),
    ("Ceridian", "ceridian", "https://ceridian.dayforcehcm.com"),
]


async def test_url_exists(session, url, timeout=5):
    """Test if a URL is reachable and returns data."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            return resp.status, await resp.text()[:200]
    except asyncio.TimeoutError:
        return None, "Timeout"
    except aiohttp.ClientError as e:
        return None, f"Connection Error: {str(e)[:100]}"
    except Exception as e:
        return None, f"Error: {str(e)[:100]}"


async def discover_dayforce_endpoints():
    """Try to discover working Dayforce endpoints."""
    print("\n" + "="*80)
    print("DISCOVERING DAYFORCE PORTALS")
    print("="*80 + "\n")
    
    connector = aiohttp.TCPConnector(limit=20, limit_per_host=5)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Test known portals
        print("Testing known Dayforce portals:\n")
        
        for company, subdomain, base_url in KNOWN_DAYFORCE_PORTALS:
            print(f"Testing {company}:")
            print(f"  URL: {base_url}")
            
            # Test main page
            status, content = await test_url_exists(session, base_url)
            print(f"  Main Page Status: {status}")
            
            # Test common API endpoints
            endpoints = [
                "/CandidatePortal/api/jobs",
                "/api/jobs",
                "/jobs",
                "/api/v1/jobs",
            ]
            
            for endpoint in endpoints:
                full_url = base_url.rstrip('/') + endpoint
                status, content = await test_url_exists(session, full_url)
                indicator = "✓" if status and status < 400 else "✗"
                print(f"    {indicator} {endpoint}: {status} - {content[:60] if status else content}")
            
            print()


async def test_real_dayforce_companies():
    """Try to find companies with actual accessible Dayforce portals."""
    print("\n" + "="*80)
    print("SEARCHING FOR ACCESSIBLE DAYFORCE PORTALS")
    print("="*80 + "\n")
    
    # These are companies known to use Dayforce based on public information
    potential_companies = {
        "accenture": "Accenture",
        "ukg": "UKG (Formerly Kronos)",
        "ceridian": "Ceridian (Dayforce Creator)",
        "mcdonalds": "McDonald's",
        "starbucks": "Starbucks",
        "walmart": "Walmart",
        "target": "Target",
        "bestbuy": "Best Buy",
        "homedepot": "Home Depot",
        "lowes": "Lowe's",
    }
    
    connector = aiohttp.TCPConnector(limit=20, limit_per_host=5)
    accessible_portals = []
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for subdomain, company_name in potential_companies.items():
            base_url = f"https://{subdomain}.dayforcehcm.com"
            
            status, _ = await test_url_exists(session, base_url, timeout=3)
            
            if status and status < 400:
                print(f"✓ FOUND: {company_name}")
                print(f"  URL: {base_url}")
                accessible_portals.append((company_name, subdomain, base_url))
            else:
                print(f"✗ Not accessible: {company_name} ({base_url})")
        
        print()
    
    if accessible_portals:
        print(f"\n✓ Found {len(accessible_portals)} accessible Dayforce portals:")
        for company, subdomain, url in accessible_portals:
            print(f"  • {company}: {url}")
    else:
        print("\n⚠️  No accessible Dayforce portals found with standard URL patterns")
    
    return accessible_portals


async def test_alternative_dayforce_urls():
    """Test alternative URL structures for Dayforce portals."""
    print("\n" + "="*80)
    print("TESTING ALTERNATIVE DAYFORCE URL STRUCTURES")
    print("="*80 + "\n")
    
    # Dayforce portals may use different domain structures
    alternatives = [
        "https://careers.accenture.com",
        "https://accenture.myworkdayjobs.com",  # Some use Workday-like URLs
        "https://accenture-careers.dayforcehcm.com",
        "https://accenture.hrms.dayforcehcm.com",
    ]
    
    connector = aiohttp.TCPConnector(limit=20, limit_per_host=5)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for url in alternatives:
            status, content = await test_url_exists(session, url, timeout=3)
            indicator = "✓" if status and status < 400 else "✗"
            print(f"{indicator} {url}: {status if status else 'Not reachable'}")
    
    print()


async def main():
    """Run all discovery tests."""
    await discover_dayforce_endpoints()
    await test_real_dayforce_companies()
    await test_alternative_dayforce_urls()
    
    print("="*80)
    print("DIAGNOSIS SUMMARY")
    print("="*80)
    print("""
The issue is that Dayforce career portal URLs follow specific naming conventions:
- Pattern: https://{subdomain}.dayforcehcm.com/CandidatePortal/
- The subdomain must match the actual company Dayforce instance
- Many companies use their legal/brand name as subdomain

To fix the scraper:
1. Use actual company Dayforce subdomains
2. Verify URLs are publicly accessible
3. Update the API endpoint paths if needed
4. Consider implementing a fallback to web scraping if APIs are restricted

Recommended next steps:
- Verify each company actually uses Dayforce
- Find their actual Dayforce subdomain (often available in job posting links)
- Update companies.json with correct identifiers
- Test a subset of known working portals first
    """)


if __name__ == "__main__":
    asyncio.run(main())
