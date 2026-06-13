"""Auto-fix broken greenhouse/lever identifiers by deriving candidates from the
company name and VERIFYING each against the live API. Only verified hits (that
actually return jobs) are accepted — nothing is fabricated.

Writes corrected companies.json (after backing up the original) and a ledger.
"""
import asyncio
import json
import re
import aiohttp

CONCURRENCY = 8
TIMEOUT = aiohttp.ClientTimeout(total=30)
MAX_TRIES = 4
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
           "Accept": "application/json, */*"}

SUFFIXES = ["inc", "inc.", "llc", "ltd", "ltd.", "corp", "corp.", "corporation",
            "technologies", "technology", "labs", "lab", "group", "holdings",
            "co", "company", "the", "&", "software", "systems", "ai"]


def candidates(name, current):
    """Generate candidate identifier slugs from a company name."""
    n = name.lower().strip()
    n = n.replace("&", " and ")
    n = re.sub(r"[.,'!()/]", "", n)
    words = [w for w in n.split() if w not in SUFFIXES]
    base = "".join(words)
    cands = [
        base,                              # janestreet
        "".join(name.lower().split()),     # janestreet (keep suffixes)
        "-".join(words),                   # jane-street
        words[0] if words else base,       # jane
        re.sub(r"[^a-z0-9]", "", n),       # raw alnum
        (current or "").split("/")[-1].lower(),
    ]
    seen, out = set(), []
    for c in cands:
        c = c.strip("-")
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


async def req(session, method, url, **kw):
    last = None
    for a in range(MAX_TRIES):
        try:
            async with session.request(method, url, headers=HEADERS, timeout=TIMEOUT, **kw) as r:
                try:
                    body = await r.json(content_type=None)
                except Exception:
                    body = None
                return r.status, body
        except (aiohttp.ClientConnectionError, aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
            last = e
            await asyncio.sleep(1.2 * (a + 1))
    raise last


async def verify(session, ats, cand):
    """Return job count if `cand` is a valid identifier for `ats`, else -1."""
    try:
        if ats == "greenhouse":
            s, b = await req(session, "GET", f"https://boards-api.greenhouse.io/v1/boards/{cand}/jobs")
            if s == 200 and isinstance(b, dict):
                return len(b.get("jobs", []))
        elif ats == "lever":
            s, b = await req(session, "GET", f"https://api.lever.co/v0/postings/{cand}?mode=json&limit=20")
            if s == 200 and isinstance(b, list):
                return len(b)
    except Exception:
        return -1
    return -1


async def fix_company(session, sem, comp, audit_status):
    async with sem:
        ats, name, cur = comp["ats_type"], comp.get("name", ""), comp.get("identifier", "")
        for cand in candidates(name, cur):
            if cand == cur:
                continue
            n = await verify(session, ats, cand)
            if n > 0:
                return {"name": name, "ats": ats, "old": cur, "new": cand, "jobs": n}
        return {"name": name, "ats": ats, "old": cur, "new": None, "jobs": 0}


async def main():
    doc = json.load(open("companies.json", encoding="utf-8"))
    companies = doc["companies"] if isinstance(doc, dict) else doc
    audit = {(a["name"], a["ats"]): a["status"] for a in json.load(open("scratch/audit_report.json"))}

    targets = [c for c in companies
               if c.get("ats_type") in ("greenhouse", "lever")
               and audit.get((c.get("name"), c.get("ats_type"))) == "404"]
    print(f"Attempting to fix {len(targets)} broken greenhouse/lever companies...\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(fix_company(session, sem, c, audit) for c in targets))

    fixed = [r for r in results if r["new"]]
    still = [r for r in results if not r["new"]]

    # Apply fixes to companies.json (back up first, preserve wrapper structure)
    json.dump(doc, open("companies.json.bak", "w", encoding="utf-8"), indent=2)
    fixmap = {(r["name"], r["ats"]): r["new"] for r in fixed}
    for c in companies:
        key = (c.get("name"), c.get("ats_type"))
        if key in fixmap:
            c["identifier"] = fixmap[key]
    json.dump(doc, open("companies.json", "w", encoding="utf-8"), indent=2)

    json.dump({"fixed": fixed, "still_broken": still},
              open("scratch/fix_report.json", "w", encoding="utf-8"), indent=2)

    print(f"FIXED (verified, identifier corrected): {len(fixed)}")
    for r in fixed:
        print(f"   {r['ats']:10} {r['name'][:24]:24} {r['old']!r} -> {r['new']!r}  ({r['jobs']} jobs)")
    print(f"\nSTILL BROKEN (no working identifier found): {len(still)}")
    for r in still[:60]:
        print(f"   {r['ats']:10} {r['name'][:30]:30} (was {r['old']!r})")
    print("\ncompanies.json updated (backup: companies.json.bak)")


if __name__ == "__main__":
    asyncio.run(main())
