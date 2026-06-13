"""Dedup companies.json: drop exact duplicates, and for names that already work
under one ATS, drop the redundant non-working guesses for the same name.
"""
import json
from collections import defaultdict

doc = json.load(open("companies.json", encoding="utf-8"))
companies = doc["companies"] if isinstance(doc, dict) else doc
audit = {(a["name"], a["ats"]): a["status"] for a in json.load(open("scratch/audit_report.json"))}

before = len(companies)

# 1) Remove exact (name, ats_type, identifier) duplicates.
seen = set()
stage1 = []
for c in companies:
    key = (c.get("name"), c.get("ats_type"), c.get("identifier"))
    if key in seen:
        continue
    seen.add(key)
    stage1.append(c)

# 2) For each name, if any entry audited OK, keep only OK entries; drop the rest.
by_name = defaultdict(list)
for c in stage1:
    by_name[c.get("name")].append(c)

kept = []
dropped = []
for name, entries in by_name.items():
    ok = [c for c in entries if audit.get((name, c.get("ats_type"))) == "OK"]
    if ok:
        kept.extend(ok)
        dropped.extend([c for c in entries if c not in ok])
    else:
        kept.append(entries[0])              # keep one to research later
        dropped.extend(entries[1:])

if isinstance(doc, dict):
    doc["companies"] = kept
else:
    doc = kept

json.dump(doc, open("companies.json", "w", encoding="utf-8"), indent=2)

print(f"before: {before}  after: {len(kept)}  removed: {len(dropped)}")
print("\nsample removed (redundant/duplicate):")
for c in dropped[:20]:
    print(f"   {c.get('ats_type'):12} {c.get('name')[:24]:24} {c.get('identifier')!r}")
