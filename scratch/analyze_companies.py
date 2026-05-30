import json
from collections import Counter

with open("companies.json", "r") as f:
    data = json.load(f)

companies = data.get("companies", [])
print(f"Total companies in companies.json: {len(companies)}")

ats_counter = Counter(c.get("ats_type") for c in companies)
print("\nATS Type Counts:")
for ats, count in ats_counter.most_common():
    print(f"  {ats:<20}: {count}")

print("\nCurrent iCIMS Companies:")
for c in companies:
    if c.get("ats_type") == "icims":
        print(f"  Name: {c.get('name')}, Identifier: {c.get('identifier')}, Base URL: {c.get('base_url')}")
