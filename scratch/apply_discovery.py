"""Apply discovered re-points to companies.json — but only high-confidence ones.

Acceptance rules:
  * STRONG slug match required: found_id must equal the full-name slug (all chars)
    or the significant-words slug. First-word/generic partial matches are rejected.
  * greenhouse + smartrecruiters: ADDITIONALLY verify the board's company name
    fuzzy-matches our company name (catches same-slug-different-company).
  * ashby + lever: accept strong matches (no name field exposed; slugs distinctive).

Everything not auto-applied is written to scratch/needs_manual.json for review.
"""
import asyncio
import json
import re
import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=25)
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, */*"}
SUFFIXES = {"inc", "llc", "ltd", "corp", "corporation", "technologies", "technology",
            "labs", "lab", "group", "holdings", "co", "company", "the", "software",
            "systems", "ai", "io", "hq"}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def slug_forms(name):
    n = name.lower().replace("&", " and ")
    n = re.sub(r"[.,'!()/]", "", n)
    words = n.split()
    core = [w for w in words if w not in SUFFIXES] or words
    return {norm(name), "".join(words), "".join(core)}


def is_strong(name, found_id):
    fid = norm(found_id)
    forms = {norm(f) for f in slug_forms(name)}
    if fid in forms:
        return True
    # single significant word company → its slug is the word
    words = [w for w in re.sub(r"[.,'!()/&]", " ", name.lower()).split() if w not in SUFFIXES]
    return len(words) <= 1 and fid == norm("".join(words))


async def board_name(session, ats, ident):
    try:
        if ats == "greenhouse":
            async with session.get(f"https://boards-api.greenhouse.io/v1/boards/{ident}",
                                   headers=HEADERS, timeout=TIMEOUT) as r:
                if r.status == 200:
                    return (await r.json(content_type=None)).get("name")
        elif ats == "smartrecruiters":
            async with session.get(f"https://api.smartrecruiters.com/v1/companies/{ident}/postings?limit=1",
                                   headers=HEADERS, timeout=TIMEOUT) as r:
                if r.status == 200:
                    c = (await r.json(content_type=None)).get("content") or [{}]
                    return (c[0].get("company") or {}).get("name")
    except Exception:
        return None
    return None


def name_matches(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


async def main():
    doc = json.load(open("companies.json", encoding="utf-8"))
    companies = doc["companies"] if isinstance(doc, dict) else doc
    found = json.load(open("scratch/discovery_report.json"))["found"]

    applied, flagged = [], []
    async with aiohttp.ClientSession() as session:
        for r in found:
            name, ats, ident = r["name"], r["found_ats"], r["found_id"]
            if not is_strong(name, ident):
                flagged.append({**r, "reason": "weak slug match (partial/generic)"})
                continue
            if ats in ("greenhouse", "smartrecruiters"):
                bn = await board_name(session, ats, ident)
                if not bn or not name_matches(name, bn):
                    flagged.append({**r, "reason": f"name mismatch (board='{bn}')"})
                    continue
            applied.append(r)

    # Apply to companies.json
    amap = {a["name"]: (a["found_ats"], a["found_id"]) for a in applied}
    for c in companies:
        if c.get("name") in amap:
            c["ats_type"], c["identifier"] = amap[c["name"]]
            c.pop("base_url", None)  # old base_url belongs to the old ATS
    json.dump(doc, open("companies.json", "w", encoding="utf-8"), indent=2)
    json.dump({"applied": applied, "flagged": flagged},
              open("scratch/apply_report.json", "w", encoding="utf-8"), indent=2)
    json.dump(flagged, open("scratch/needs_manual.json", "w", encoding="utf-8"), indent=2)

    from collections import Counter
    print(f"APPLIED {len(applied)} verified re-points: {Counter(a['found_ats'] for a in applied)}")
    for a in sorted(applied, key=lambda x: -x["jobs"])[:40]:
        print(f"   {a['name'][:24]:24} {a['old_ats']}/{a['old_id']!r} -> {a['found_ats']}/{a['found_id']!r} ({a['jobs']})")
    print(f"\nFLAGGED {len(flagged)} for manual review (not applied):")
    for f in flagged[:30]:
        print(f"   {f['name'][:24]:24} -> {f['found_ats']}/{f['found_id']!r} ({f['jobs']})  [{f['reason']}]")


if __name__ == "__main__":
    asyncio.run(main())
