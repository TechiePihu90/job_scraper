import json
from collections import Counter

with open("companies.json", "r") as f:
    data = json.load(f)

companies = data.get("companies", [])
print(f"Total companies in companies.json: {len(companies)}")

ats_counts = Counter(c.get("ats_type") for c in companies)
print("\nATS type distribution:")
for ats, count in ats_counts.items():
    print(f"  - {ats}: {count}")

print("\nFirst 5 companies:")
for c in companies[:5]:
    print(f"  - {c}")
