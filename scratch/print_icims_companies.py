import json

with open("companies.json", "r") as f:
    data = json.load(f)

icims_companies = [c for c in data.get("companies", []) if c.get("ats_type") == "icims"]
print(f"Current iCIMS companies ({len(icims_companies)}):")
for c in icims_companies:
    print(json.dumps(c, indent=2))
