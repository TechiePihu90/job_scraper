"""Audit every company in companies.json: probe its ATS list endpoint and classify.

Output: scratch/audit_report.json (per-company status) + printed summary.
Lightweight (list endpoint only, no detail enrichment, no DB writes).
"""
import asyncio
import json
import aiohttp

CONCURRENCY = 8
TIMEOUT = aiohttp.ClientTimeout(total=30)
MAX_TRIES = 4
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
}


def load_companies():
    d = json.load(open("companies.json", encoding="utf-8"))
    return d if isinstance(d, list) else d.get("companies", [])


async def _json(session, method, url, **kw):
    """Request with retries for transient connection/DNS/timeout failures."""
    last_exc = None
    for attempt in range(MAX_TRIES):
        try:
            async with session.request(method, url, headers=HEADERS, timeout=TIMEOUT, **kw) as r:
                status = r.status
                try:
                    body = await r.json(content_type=None)
                except Exception:
                    body = await r.text()
                return status, body
        except (aiohttp.ClientConnectionError, aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
            last_exc = e
            await asyncio.sleep(1.5 * (attempt + 1))
    raise last_exc


async def probe(session, c):
    """Return (status_label, count, detail)."""
    ats = c.get("ats_type")
    ident = c.get("identifier", "")
    base = (c.get("base_url") or "").rstrip("/")
    try:
        if ats == "greenhouse":
            tok = ident.split("/")[-1]
            s, b = await _json(session, "GET", f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs")
            if s == 404:
                return "404", 0, "board not found"
            if s != 200:
                return f"HTTP{s}", 0, ""
            n = len(b.get("jobs", [])) if isinstance(b, dict) else 0
            return ("OK" if n else "EMPTY"), n, ""

        if ats == "lever":
            tok = ident.split("/")[-1]
            s, b = await _json(session, "GET", f"https://api.lever.co/v0/postings/{tok}?mode=json&limit=20")
            if s == 404:
                return "404", 0, "account not found"
            if s != 200:
                return f"HTTP{s}", 0, ""
            n = len(b) if isinstance(b, list) else 0
            return ("OK" if n else "EMPTY"), n, ""

        if ats == "workday":
            parts = ident.split("/", 1)
            if len(parts) != 2 or not base:
                return "BADCONFIG", 0, "need tenant/site + base_url"
            tenant, site = parts
            s, b = await _json(session, "POST", f"{base}/wday/cxs/{tenant}/{site}/jobs",
                               json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
            if s == 404:
                return "404", 0, ""
            if s != 200:
                return f"HTTP{s}", 0, ""
            n = int(b.get("total", 0)) if isinstance(b, dict) else 0
            return ("OK" if n else "EMPTY"), n, ""

        if ats == "ashby":
            s, b = await _json(session, "GET", f"https://api.ashbyhq.com/posting-api/job-board/{ident}")
            if s == 404:
                return "404", 0, "board not found"
            if s != 200:
                return f"HTTP{s}", 0, ""
            n = len(b.get("jobs", [])) if isinstance(b, dict) else 0
            return ("OK" if n else "EMPTY"), n, ""

        if ats == "smartrecruiters":
            s, b = await _json(session, "GET", f"https://api.smartrecruiters.com/v1/companies/{ident}/postings?limit=10")
            if s == 404:
                return "404", 0, "company not found"
            if s != 200:
                return f"HTTP{s}", 0, ""
            n = b.get("totalFound", 0) if isinstance(b, dict) else 0
            return ("OK" if n else "EMPTY"), n, ""

        if ats == "bamboohr":
            sub = ident
            s, b = await _json(session, "GET", f"https://{sub}.bamboohr.com/careers/list")
            if s == 404:
                return "404", 0, "subdomain not found"
            if s != 200:
                return f"HTTP{s}", 0, ""
            res = b.get("result", []) if isinstance(b, dict) else []
            n = len(res)
            return ("OK" if n else "EMPTY"), n, ""

        if ats == "dayforce":
            s, b = await _json(session, "POST", f"https://jobs.dayforcehcm.com/api/geo/{ident}/jobposting/search",
                               json={"clientNamespace": ident, "jobBoardCode": "CANDIDATEPORTAL",
                                     "cultureCode": "en-US", "distanceUnit": 0, "paginationStart": 0})
            if s == 404:
                return "404", 0, "namespace not found"
            if s != 200:
                return f"HTTP{s}", 0, ""
            n = len(b.get("jobPostings", [])) if isinstance(b, dict) else 0
            return ("OK" if n else "EMPTY"), n, ""

        if ats == "jazzhr":
            s, b = await _json(session, "GET", f"https://{ident}.applytojob.com/apply")
            if s == 404:
                return "404", 0, ""
            txt = b if isinstance(b, str) else ""
            n = txt.count("/apply/jobs/") + txt.lower().count("list-group-item")
            return ("OK" if n else "EMPTY"), n, "html"

        if ats == "clearcompany":
            s, b = await _json(session, "GET", f"https://{ident}.clearcompany.com/careers/jobs")
            if s == 404:
                return "404", 0, ""
            txt = b if isinstance(b, str) else ""
            n = txt.count("/careers/jobs/")
            return ("OK" if n else "EMPTY"), n, "html"

        if ats == "jobvite":
            s, b = await _json(session, "GET", f"https://api.jobvite.com/v1/jobs?company={ident}")
            if s == 200 and isinstance(b, dict):
                n = len(b.get("requisitions", []) or b.get("jobs", []))
                return ("OK" if n else "EMPTY"), n, "api"
            return f"HTTP{s}", 0, "api needs auth?"

        if ats == "successfactors":
            url = f"{base or ('https://api' + ident + '.successfactors.com')}/odata/v2/JobRequisition?$format=json&$top=5"
            s, b = await _json(session, "GET", url)
            if s == 404:
                return "404", 0, ""
            if s != 200:
                return f"HTTP{s}", 0, ""
            return "OK", 1, ""

        if ats == "taleo":
            if not base:
                return "BADCONFIG", 0, "need base_url"
            s, b = await _json(session, "POST", f"{base}/careersection/rest/jobboard/searchjobs?portal={ident}",
                               json={"multilineEnabled": False, "sortingSelection": {"ascendingSortingOrder": "false", "sortBySelectionParam": "3"},
                                     "fieldData": {}, "filterSelectionParam": {}, "advancedSearchFiltersSelectionParam": {},
                                     "pageNo": 1})
            if s == 404:
                return "404", 0, ""
            if s != 200:
                return f"HTTP{s}", 0, ""
            return "OK", 1, ""

        if ats == "usajobs":
            return "NEEDS_KEY", 0, "set JOBSCRAPER_USAJOBS_API_KEY"

        if ats == "icims":
            return "NEEDS_BROWSER", 0, "playwright-based scraper"

        return "UNKNOWN_ATS", 0, ats
    except asyncio.TimeoutError:
        return "TIMEOUT", 0, ""
    except Exception as e:
        return "ERROR", 0, f"{type(e).__name__}: {e}"


async def main():
    companies = load_companies()
    sem = asyncio.Semaphore(CONCURRENCY)
    results = []

    async with aiohttp.ClientSession() as session:
        async def run(c):
            async with sem:
                label, n, detail = await probe(session, c)
                results.append({"name": c.get("name"), "ats": c.get("ats_type"),
                                "identifier": c.get("identifier"), "status": label,
                                "count": n, "detail": detail})

        await asyncio.gather(*(run(c) for c in companies))

    json.dump(results, open("scratch/audit_report.json", "w", encoding="utf-8"), indent=2)

    # Summary
    from collections import Counter
    by_status = Counter(r["status"] for r in results)
    print(f"\n==== AUDIT of {len(results)} companies ====")
    for st, cnt in by_status.most_common():
        print(f"  {st:14}: {cnt}")

    print("\n==== Per-ATS: OK vs broken ====")
    ats_stats = {}
    for r in results:
        d = ats_stats.setdefault(r["ats"], {"ok": 0, "broken": 0})
        d["ok" if r["status"] == "OK" else "broken"] += 1
    for ats, d in sorted(ats_stats.items(), key=lambda x: -(x[1]["ok"] + x[1]["broken"])):
        print(f"  {ats:16} OK={d['ok']:4}  broken={d['broken']:4}")

    print("\nReport written to scratch/audit_report.json")


if __name__ == "__main__":
    asyncio.run(main())
