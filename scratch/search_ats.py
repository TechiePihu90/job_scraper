import json

with open("companies.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for c in data.get("companies", []):
    if c.get("ats_type") in ["zoho_recruit", "successfactors", "clearcompany", "jazzhr"]:
        print(f"Company: {c.get('name')}, ATS: {c.get('ats_type')}, Identifier: {c.get('identifier')}, Base URL: {c.get('base_url')}")
