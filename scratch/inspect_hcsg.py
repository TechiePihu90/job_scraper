import re

with open("scratch/hcsg_page.html", "r", encoding="utf-8") as f:
    html = f.read()

print(f"HTML length: {len(html)}")

# Find all job links
# Typically, iCIMS job links look like: https://careers-hcsgcorp.icims.com/jobs/12345/job-title/job
# or relative links: /jobs/12345/job-title/job
job_links = re.findall(r'href="([^"]*/jobs/\d+/[^"/]+/job[^"]*)"', html)
print(f"Found {len(job_links)} job links:")
for link in job_links[:10]:
    print(f"  {link}")

# Let's print out the block around one of the job links to see class names
if job_links:
    first_link = job_links[0]
    pos = html.find(first_link)
    if pos != -1:
        start = max(0, pos - 500)
        end = min(len(html), pos + 1000)
        print("\nContext around first job link:")
        print(html[start:end])
