import re
import html

def parse_html(html_content):
    cards = html_content.split('<li class="iCIMS_JobCardItem">')[1:]
    jobs = []
    
    for card in cards:
        # End of card is usually </li> but let's just truncate at next card if needed or parse in its block
        # We can search for fields within the block
        
        # 1. Title and apply_url
        # <a href="..." class="iCIMS_Anchor" ...> ... <h3>Title</h3>
        url_match = re.search(r'href="([^"]*/jobs/(\d+)/[^"/]+/job[^"]*)"', card)
        if not url_match:
            continue
        apply_url, ext_id = url_match.groups()
        
        title_match = re.search(r'<h3\s*[^>]*>\s*(.*?)\s*</h3>', card, re.DOTALL)
        title = html.unescape(title_match.group(1).strip()) if title_match else "Unknown"
        
        # 2. Location
        # <span class="sr-only field-label">Job Locations</span>\s*<span\s*[^>]*>\s*(.*?)\s*</span>
        loc_match = re.search(r'Job Locations</span>\s*<span\s*[^>]*>\s*(.*?)\s*</span>', card, re.DOTALL)
        location = html.unescape(loc_match.group(1).strip()) if loc_match else ""
        # Clean location (remove newlines, double spaces)
        location = " ".join(location.split())
        
        # 3. Description
        # <div class="col-xs-12 description">\s*(.*?)\s*</div>
        desc_match = re.search(r'<div class="col-xs-12 description">\s*(.*?)\s*</div>', card, re.DOTALL)
        description = html.unescape(desc_match.group(1).strip()) if desc_match else ""
        description = re.sub(r"<[^>]+>", " ", description)
        description = " ".join(description.split())
        if len(description) > 2000:
            description = description[:2000] + "..."
            
        jobs.append({
            "ext_id": ext_id,
            "title": title,
            "location": location,
            "description": description,
            "apply_url": apply_url,
        })
        
    return jobs

with open("scratch/hcsg_page.html", "r", encoding="utf-8") as f:
    content = f.read()

jobs = parse_html(content)
print(f"Successfully parsed {len(jobs)} jobs:")
for idx, job in enumerate(jobs[:5], 1):
    print(f"\nJob {idx}:")
    print(f"  ID: {job['ext_id']}")
    print(f"  Title: {job['title']}")
    print(f"  Location: {job['location']}")
    print(f"  URL: {job['apply_url']}")
    print(f"  Description: {job['description'][:150]}...")
