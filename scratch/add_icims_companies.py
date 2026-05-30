import json
import re

def slugify(name):
    # Alphanumeric lowercase, no spaces
    return re.sub(r'[^a-z0-9]', '', name.lower())

def main():
    # 1. Load companies.json
    with open("companies.json", "r") as f:
        companies_data = json.load(f)
    
    companies_list = companies_data.get("companies", [])
    print(f"Initial companies count: {len(companies_list)}")
    
    # Track existing names and base URLs to avoid duplicates
    existing_urls = {c.get("base_url").rstrip('/') for c in companies_list if c.get("base_url")}
    existing_names = {c.get("name").lower() for c in companies_list}
    
    # 2. Load verified_icims.json
    with open("scratch/verified_icims.json", "r") as f:
        verified_list = json.load(f)
        
    print(f"Verified iCIMS companies available to add: {len(verified_list)}")
    
    added_count = 0
    for vc in verified_list:
        name = vc["name"]
        base_url = vc["base_url"].rstrip('/')
        
        # Skip if already exists
        if base_url in existing_urls or name.lower() in existing_names:
            print(f"  - Skipping '{name}' (already exists)")
            continue
            
        identifier = slugify(name)
        new_company = {
            "name": name,
            "ats_type": "icims",
            "identifier": identifier,
            "base_url": base_url + "/" # standard trailing slash
        }
        
        companies_list.append(new_company)
        added_count += 1
        
    print(f"\nAdded {added_count} new iCIMS companies.")
    companies_data["companies"] = companies_list
    
    # 3. Write back to companies.json
    with open("companies.json", "w") as f:
        json.dump(companies_data, f, indent=2)
        
    print(f"Updated companies.json. New total companies: {len(companies_list)}")

if __name__ == "__main__":
    main()
