import json
import os

WORKDAY_COMPANIES = [
    {"company": "Adobe",              "base_url": "https://adobe.wd5.myworkdayjobs.com",        "company_id": "adobe",        "job_board_id": "external_experienced"},
    {"company": "HP Inc",             "base_url": "https://hp.wd5.myworkdayjobs.com",            "company_id": "hp",           "job_board_id": "ExternalCareerSite"},
    {"company": "Salesforce",         "base_url": "https://salesforce.wd12.myworkdayjobs.com",   "company_id": "salesforce",   "job_board_id": "External_Career_Site"},
    {"company": "Workday",            "base_url": "https://workday.wd5.myworkdayjobs.com",       "company_id": "workday",      "job_board_id": "Workday"},
    {"company": "Autodesk",           "base_url": "https://autodesk.wd1.myworkdayjobs.com",      "company_id": "autodesk",     "job_board_id": "Ext"},
    {"company": "Cisco",              "base_url": "https://cisco.wd5.myworkdayjobs.com",         "company_id": "cisco",        "job_board_id": "Cisco_Careers"},
    {"company": "Intel",              "base_url": "https://intel.wd1.myworkdayjobs.com",         "company_id": "intel",        "job_board_id": "External"},
    {"company": "HPE",                "base_url": "https://hpe.wd5.myworkdayjobs.com",           "company_id": "hpe",          "job_board_id": "jobsathpe"},
    {"company": "Dell Technologies",  "base_url": "https://dell.wd1.myworkdayjobs.com",          "company_id": "dell",         "job_board_id": "External"},
    {"company": "Qualcomm",           "base_url": "https://qualcomm.wd12.myworkdayjobs.com",     "company_id": "qualcomm",     "job_board_id": "External"},
    {"company": "Verizon",            "base_url": "https://verizon.wd12.myworkdayjobs.com",      "company_id": "verizon",      "job_board_id": "verizon-careers"},
    {"company": "Motorola Solutions", "base_url": "https://motorolasolutions.wd5.myworkdayjobs.com","company_id": "motorolasolutions","job_board_id": "Careers"},
    {"company": "Bank of America",    "base_url": "https://ghr.wd1.myworkdayjobs.com",           "company_id": "ghr",          "job_board_id": "Lateral-US"},
    {"company": "Wells Fargo",        "base_url": "https://wd1.myworkdaysite.com",               "company_id": "wf",           "job_board_id": "WellsFargoJobs"},
    {"company": "Citigroup",          "base_url": "https://citi.wd5.myworkdayjobs.com",          "company_id": "citi",         "job_board_id": "2"},
    {"company": "Morgan Stanley",     "base_url": "https://ms.wd5.myworkdayjobs.com",            "company_id": "ms",           "job_board_id": "External"},
    {"company": "Northern Trust",     "base_url": "https://ntrs.wd1.myworkdayjobs.com",          "company_id": "ntrs",         "job_board_id": "northerntrust"},
    {"company": "Walmart",            "base_url": "https://walmart.wd5.myworkdayjobs.com",       "company_id": "walmart",      "job_board_id": "WalmartExternal"},
    {"company": "Target",             "base_url": "https://target.wd5.myworkdayjobs.com",        "company_id": "target",       "job_board_id": "targetcareers"},
    {"company": "Nordstrom",          "base_url": "https://nordstrom.wd501.myworkdayjobs.com",   "company_id": "nordstrom",    "job_board_id": "nordstrom_careers"},
    {"company": "Nike",               "base_url": "https://nike.wd1.myworkdayjobs.com",          "company_id": "nike",         "job_board_id": "nke"},
    {"company": "Lowe's",             "base_url": "https://lowes.wd5.myworkdayjobs.com",         "company_id": "lowes",        "job_board_id": "LWS_External_CS"},
    {"company": "Kohl's",             "base_url": "https://kohls.wd1.myworkdayjobs.com",         "company_id": "kohls",        "job_board_id": "kohlscareers"},
    {"company": "Humana",             "base_url": "https://humana.wd5.myworkdayjobs.com",        "company_id": "humana",       "job_board_id": "Humana_External_Career_Site"},
    {"company": "Cigna",              "base_url": "https://cigna.wd5.myworkdayjobs.com",         "company_id": "cigna",        "job_board_id": "cignacareers"},
    {"company": "Johnson & Johnson",  "base_url": "https://jj.wd5.myworkdayjobs.com",            "company_id": "jj",           "job_board_id": "JJ"},
    {"company": "Pfizer",             "base_url": "https://pfizer.wd1.myworkdayjobs.com",        "company_id": "pfizer",       "job_board_id": "PfizerCareers"},
    {"company": "Abbott",             "base_url": "https://abbott.wd5.myworkdayjobs.com",        "company_id": "abbott",       "job_board_id": "abbottcareers"},
    {"company": "Medtronic",          "base_url": "https://medtronic.wd1.myworkdayjobs.com",     "company_id": "medtronic",    "job_board_id": "MedtronicCareers"},
    {"company": "Raytheon (RTX)",     "base_url": "https://globalhr.wd5.myworkdayjobs.com",      "company_id": "globalhr",     "job_board_id": "REC_RTX_Ext_Gateway"},
    {"company": "Northrop Grumman",   "base_url": "https://ngc.wd1.myworkdayjobs.com",           "company_id": "ngc",          "job_board_id": "Northrop_Grumman_External_Site"},
    {"company": "General Motors",     "base_url": "https://generalmotors.wd5.myworkdayjobs.com", "company_id": "generalmotors","job_board_id": "Careers_GM"},
    {"company": "UPS",                "base_url": "https://hcmportal.wd5.myworkdayjobs.com",     "company_id": "hcmportal",    "job_board_id": "Search"},
    {"company": "Comcast",            "base_url": "https://comcast.wd5.myworkdayjobs.com",       "company_id": "comcast",      "job_board_id": "Comcast_Careers"},
    {"company": "Warner Bros Discovery","base_url": "https://warnerbros.wd5.myworkdayjobs.com",  "company_id": "warnerbros",   "job_board_id": "global"},
    {"company": "Accenture",          "base_url": "https://accenture.wd103.myworkdayjobs.com",   "company_id": "accenture",    "job_board_id": "AccentureCareers"},
    {"company": "PwC",                "base_url": "https://pwc.wd3.myworkdayjobs.com",           "company_id": "pwc",          "job_board_id": "Global_Campus_Careers"},
    {"company": "Caterpillar",        "base_url": "https://cat.wd5.myworkdayjobs.com",           "company_id": "cat",          "job_board_id": "CaterpillarCareers"},
    {"company": "3M",                 "base_url": "https://3m.wd1.myworkdayjobs.com",            "company_id": "3m",           "job_board_id": "Search"},
    {"company": "Johnson Controls",   "base_url": "https://jci.wd5.myworkdayjobs.com",           "company_id": "jci",          "job_board_id": "JCI"},
    {"company": "SC Johnson",         "base_url": "https://scj.wd5.myworkdayjobs.com",           "company_id": "scj",          "job_board_id": "External_Career_Site"},
    {"company": "JLL",                "base_url": "https://jll.wd1.myworkdayjobs.com",           "company_id": "jll",          "job_board_id": "jllcareers"},
    {"company": "AstraZeneca US",     "base_url": "https://astrazeneca.wd3.myworkdayjobs.com",   "company_id": "astrazeneca",  "job_board_id": "Careers"},
    {"company": "Nvidia", "base_url": "https://nvidia.wd5.myworkdayjobs.com", "company_id": "nvidia", "job_board_id": "NVIDIAExternalCareerSite"},
    {"company": "Broadcom", "base_url": "https://broadcom.wd1.myworkdayjobs.com", "company_id": "broadcom", "job_board_id": "External_Career"},
    {"company": "Zoom", "base_url": "https://zoom.wd5.myworkdayjobs.com", "company_id": "zoom", "job_board_id": "Zoom"},
    {"company": "Centene", "base_url": "https://centene.wd5.myworkdayjobs.com", "company_id": "centene", "job_board_id": "Centene_External"},
    {"company": "ConocoPhillips", "base_url": "https://conocophillips.wd1.myworkdayjobs.com", "company_id": "conocophillips", "job_board_id": "External"},
]

GREENHOUSE_COMPANIES = [
    "stripe", "airbnb", "coinbase", "dropbox", "discord",
    "notion", "figma", "robinhood", "databricks", "openai",
    "reddit", "asana", "affirm", "instacart", "gusto",
    "plaid", "brex", "rippling", "zapier", "flexport",
    "segment", "benchling", "scaleai", "cruise", "niantic",
    "lever", "greenhouse", "checkr", "samsara", "hashicorp",
    "cloudflare", "twilio", "okta", "zendesk", "intercom",
    "canva", "atlassian", "shopify", "square", "block",
    "coursera", "udemy", "duolingo", "khanacademy",
    "evernote", "mozilla", "automattic"
]

LEVER_COMPANIES = [
    "netflix", "shopify", "tesla", "unity", "yelp",
    "pinterest", "eventbrite", "hackerone", "lever",
    "gitlab", "circleci", "docker", "postman",
    "algolia", "contentful", "sendgrid", "mux",
    "patreon", "calendly", "webflow", "retool",
    "loom", "figma", "notion", "linear",
    "superhuman", "frontendmasters", "carta",
    "angelist", "wellfound", "heap", "fullstory",
    "amplitude", "mixpanel", "segment",
    "snyk", "datadog", "newrelic"
]

def merge():
    with open('companies.json', 'r') as f:
        config = json.load(f)
    
    existing = {(c['ats_type'], c['identifier']): c for c in config['companies']}
    
    new_companies = []
    
    # Process Workday
    for c in WORKDAY_COMPANIES:
        name = c['company']
        identifier = f"{c['company_id']}/{c['job_board_id']}"
        ats_type = 'workday'
        base_url = c['base_url']
        
        if (ats_type, identifier) not in existing:
            new_companies.append({
                "name": name,
                "ats_type": ats_type,
                "identifier": identifier,
                "base_url": base_url
            })
            existing[(ats_type, identifier)] = True

    # Process Greenhouse
    for name in GREENHOUSE_COMPANIES:
        identifier = name.lower()
        ats_type = 'greenhouse'
        if (ats_type, identifier) not in existing:
            new_companies.append({
                "name": name.capitalize(),
                "ats_type": ats_type,
                "identifier": identifier
            })
            existing[(ats_type, identifier)] = True

    # Process Lever
    for name in LEVER_COMPANIES:
        identifier = name.lower()
        ats_type = 'lever'
        if (ats_type, identifier) not in existing:
            new_companies.append({
                "name": name.capitalize(),
                "ats_type": ats_type,
                "identifier": identifier
            })
            existing[(ats_type, identifier)] = True

    config['companies'].extend(new_companies)
    
    with open('companies.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Added {len(new_companies)} new companies.")

if __name__ == "__main__":
    merge()
