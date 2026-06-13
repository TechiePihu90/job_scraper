"""Cross-ATS discovery: for every broken company, probe its name-derived slug
across all public JSON ATS APIs to find where it actually has a live board.
Accepts only verified boards that return jobs. Output: scratch/discovery_report.json
"""
import asyncio
import json
import re
import aiohttp

CONCURRENCY = 8
TIMEOUT = aiohttp.ClientTimeout(total=30)
MAX_TRIES = 3
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
           "Accept": "application/json, */*"}
SUFFIXES = {"inc", "inc.", "llc", "ltd", "corp", "corporation", "technologies",
            "technology", "labs", "lab", "group", "holdings", "co", "company",
            "the", "software", "systems", "ai", "io", "hq"}


def slugs(name):
    n = name.lower().replace("&", " and ")
    n = re.sub(r"[.,'!()/]", "", n)
    words = n.split()
    core = [w for w in words if w not in SUFFIXES] or words
    out = []
    for s in ["".join(words), "".join(core), "-".join(core), "-".join(words),
              core[0] if core else "", re.sub(r"[^a-z0-9]", "", n)]:
        s = s.strip("-")
        if s and s not in out:
            out.append(s)
    return out


async def req(session, method, url, **kw):
    last = None
    for a in range(MAX_TRIES):
        try:
            async with session.request(method, url, headers=HEADERS, timeout=TIMEOUT, **kw) as r:
                if r.status != 200:
                    return None
                try:
                    return await r.json(content_type=None)
                except Exception:
                    return None
        except (aiohttp.ClientConnectionError, aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
            last = e
            await asyncio.sleep(1.0 * (a + 1))
    return None


async def probe_all_ats(session, slug):
    """Return list of (ats, slug, count) where this slug has a live board."""
    hits = []
    # greenhouse
    b = await req(session, "GET", f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    if isinstance(b, dict) and b.get("jobs"):
        hits.append(("greenhouse", slug, len(b["jobs"])))
    # lever
    b = await req(session, "GET", f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=50")
    if isinstance(b, list) and b:
        hits.append(("lever", slug, len(b)))
    # ashby
    b = await req(session, "GET", f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if isinstance(b, dict) and b.get("jobs"):
        hits.append(("ashby", slug, len(b["jobs"])))
    # smartrecruiters
    b = await req(session, "GET", f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=10")
    if isinstance(b, dict) and b.get("totalFound", 0) > 0:
        hits.append(("smartrecruiters", slug, b["totalFound"]))
    return hits


async def discover(session, sem, comp):
    async with sem:
        name = comp.get("name", "")
        for s in slugs(name):
            hits = await probe_all_ats(session, s)
            if hits:
                hits.sort(key=lambda h: -h[2])  # most jobs first
                ats, slug, n = hits[0]
                return {"name": name, "old_ats": comp.get("ats_type"), "old_id": comp.get("identifier"),
                        "found_ats": ats, "found_id": slug, "jobs": n,
                        "all_hits": hits}
        return {"name": name, "old_ats": comp.get("ats_type"), "old_id": comp.get("identifier"),
                "found_ats": None, "found_id": None, "jobs": 0, "all_hits": []}


async def main():
    doc = json.load(open("companies.json", encoding="utf-8"))
    companies = doc["companies"] if isinstance(doc, dict) else doc
    audit = {(a["name"], a["ats"]): a["status"] for a in json.load(open("scratch/audit_report.json"))}

    broken = [c for c in companies if audit.get((c.get("name"), c.get("ats_type"))) != "OK"]
    print(f"Probing {len(broken)} broken companies across greenhouse/lever/ashby/smartrecruiters...\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(discover(session, sem, c) for c in broken))

    found = [r for r in results if r["found_ats"]]
    notfound = [r for r in results if not r["found_ats"]]
    json.dump({"found": found, "not_found": notfound},
              open("scratch/discovery_report.json", "w", encoding="utf-8"), indent=2)

    from collections import Counter
    print(f"DISCOVERED a live board for {len(found)} companies:")
    for r in sorted(found, key=lambda r: -r["jobs"]):
        change = "" if (r["found_ats"] == r["old_ats"] and r["found_id"] == r["old_id"]) else "  <-- RE-POINT"
        print(f"   {r['name'][:24]:24} {r['old_ats']}/{r['old_id']!r} -> {r['found_ats']}/{r['found_id']!r} ({r['jobs']} jobs){change}")
    print(f"\nfound by ATS: {Counter(r['found_ats'] for r in found)}")
    print(f"\nNO live board found: {len(notfound)} (likely Workday/private/custom)")


if __name__ == "__main__":
    asyncio.run(main())
