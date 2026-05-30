import asyncio
import json
import re

candidate_companies = [
    {"name": "Burlington Stores", "base_url": "https://careers-burlington.icims.com"},
    {"name": "Select Medical", "base_url": "https://careers-selectmedical.icims.com"},
    {"name": "Dana-Farber Cancer Institute", "base_url": "https://careers-danafarber.icims.com"},
    {"name": "Piedmont Healthcare", "base_url": "https://careers-piedmont.icims.com"},
    {"name": "BJC HealthCare", "base_url": "https://careers-bjc.icims.com"},
    {"name": "Allied Universal", "base_url": "https://careers-aus.icims.com"},
    {"name": "AmTrust Financial Services", "base_url": "https://careers-amtrust.icims.com"},
    {"name": "Sidley Austin", "base_url": "https://careers-sidley.icims.com"},
    {"name": "Enterprise Holdings", "base_url": "https://careers-enterprise.icims.com"},
    {"name": "Peraton", "base_url": "https://careers-peraton.icims.com"},
    {"name": "Advanced Micro Devices", "base_url": "https://careers-amd.icims.com"},
    {"name": "Pure Storage", "base_url": "https://careers-purestorage.icims.com"},
    {"name": "Hackensack Meridian Health", "base_url": "https://careers-hackensackmeridianhealth.icims.com"},
    {"name": "Ryder System", "base_url": "https://careers-ryder.icims.com"},
    {"name": "Emory Healthcare", "base_url": "https://careers-emoryhealthcare.icims.com"},
    {"name": "Aimbridge Hospitality", "base_url": "https://careers-aimbridge.icims.com"},
    {"name": "Sherwin-Williams", "base_url": "https://careers-sherwin.icims.com"},
    {"name": "The Cheesecake Factory", "base_url": "https://careers-thecheesecakefactory.icims.com"},
    {"name": "Tractor Supply Company", "base_url": "https://careers-tractorsupply.icims.com"},
    {"name": "LabCorp", "base_url": "https://careers-labcorp.icims.com"},
    {"name": "Leidos", "base_url": "https://careers-leidos.icims.com"},
    {"name": "CACI International", "base_url": "https://careers-caci.icims.com"},
    {"name": "SAIC", "base_url": "https://careers-saic.icims.com"},
    {"name": "Galls", "base_url": "https://careers-galls.icims.com"},
    {"name": "Gentiva Health Services", "base_url": "https://careers-gentiva.icims.com"},
    {"name": "Corewell Health", "base_url": "https://careers-corewellhealth.icims.com"},
    {"name": "Novant Health", "base_url": "https://careers-novanthealth.icims.com"},
    {"name": "Trinity Health", "base_url": "https://careers-trinityhealth.icims.com"},
    {"name": "Advocate Aurora Health", "base_url": "https://careers-advocateaurora.icims.com"},
    {"name": "UC Health", "base_url": "https://careers-uchealth.icims.com"},
    {"name": "NYU Langone Health", "base_url": "https://careers-nyulangone.icims.com"},
    {"name": "Mount Sinai Health System", "base_url": "https://careers-mountsinai.icims.com"},
    {"name": "Northwell Health", "base_url": "https://careers-northwell.icims.com"},
    {"name": "Tufts Medicine", "base_url": "https://careers-tuftsmedicine.icims.com"},
    {"name": "Mass General Brigham", "base_url": "https://careers-massgeneralbrigham.icims.com"},
    {"name": "Yale New Haven Health", "base_url": "https://careers-ynhh.icims.com"},
    {"name": "Spectrum Health", "base_url": "https://careers-spectrumhealth.icims.com"},
    {"name": "Banner Health", "base_url": "https://careers-bannerhealth.icims.com"},
    {"name": "Intermountain Healthcare", "base_url": "https://careers-intermountain.icims.com"},
    {"name": "Providence Health", "base_url": "https://careers-providence.icims.com"},
    {"name": "Sutter Health", "base_url": "https://careers-sutterhealth.icims.com"},
    {"name": "CommonSpirit Health", "base_url": "https://careers-commonspirit.icims.com"},
    {"name": "Ascension", "base_url": "https://careers-ascension.icims.com"},
    {"name": "Cleveland Clinic", "base_url": "https://careers-clevelandclinic.icims.com"},
    {"name": "Mayo Clinic", "base_url": "https://careers-mayoclinic.icims.com"},
    {"name": "Geisinger", "base_url": "https://careers-geisinger.icims.com"},
    {"name": "Jefferson Health", "base_url": "https://careers-jefferson.icims.com"},
    {"name": "Temple University Health", "base_url": "https://careers-temple.icims.com"},
    {"name": "Penn Medicine", "base_url": "https://careers-pennmedicine.icims.com"},
    {"name": "UPMC", "base_url": "https://careers-upmc.icims.com"},
    {"name": "Allegheny Health Network", "base_url": "https://careers-ahn.icims.com"},
    {"name": "Wawa", "base_url": "https://careers-wawa.icims.com"},
    {"name": "Sheetz", "base_url": "https://careers-sheetz.icims.com"},
    {"name": "Casey's", "base_url": "https://careers-caseys.icims.com"},
    {"name": "Pilot Flying J", "base_url": "https://careers-pilotflyingj.icims.com"},
    {"name": "Love's Travel Stops", "base_url": "https://careers-loves.icims.com"},
    {"name": "QuikTrip", "base_url": "https://careers-quiktrip.icims.com"},
    {"name": "Cumberland Farms", "base_url": "https://careers-cumberlandfarms.icims.com"},
    {"name": "Kroger", "base_url": "https://careers-kroger.icims.com"},
    {"name": "Albertsons", "base_url": "https://careers-albertsons.icims.com"},
    {"name": "H-E-B", "base_url": "https://careers-heb.icims.com"},
    {"name": "Publix", "base_url": "https://careers-publix.icims.com"},
    {"name": "Hy-Vee", "base_url": "https://careers-hy-vee.icims.com"},
    {"name": "Wegmans", "base_url": "https://careers-wegmans.icims.com"},
    {"name": "Meijer", "base_url": "https://careers-meijer.icims.com"},
    {"name": "Aldi", "base_url": "https://careers-aldi.icims.com"},
    {"name": "Amentum", "base_url": "https://careers-amentum.icims.com"},
    {"name": "DynCorp", "base_url": "https://careers-dyncorp.icims.com"},
    {"name": "Vectrus", "base_url": "https://careers-vectrus.icims.com"},
    {"name": "Vencore", "base_url": "https://careers-vencore.icims.com"},
    {"name": "KeyW", "base_url": "https://careers-keyw.icims.com"},
    {"name": "Engility", "base_url": "https://careers-engility.icims.com"},
    {"name": "Sotera", "base_url": "https://careers-sotera.icims.com"},
    {"name": "Salient CRGT", "base_url": "https://careers-salientcrgt.icims.com"},
    {"name": "ECS Federal", "base_url": "https://careers-ecsfederal.icims.com"},
    {"name": "ManTech", "base_url": "https://careers-mantech.icims.com"},
    {"name": "SRI International", "base_url": "https://careers-sri.icims.com"},
    {"name": "MITRE", "base_url": "https://careers-mitre.icims.com"},
    {"name": "Battelle", "base_url": "https://careers-battelle.icims.com"},
    {"name": "Aerospace Corporation", "base_url": "https://careers-aerospace.icims.com"},
    {"name": "Rand Corporation", "base_url": "https://careers-rand.icims.com"},
    {"name": "CNA Corporation", "base_url": "https://careers-cna.icims.com"},
    {"name": "LMI", "base_url": "https://careers-lmi.icims.com"},
    {"name": "Noblis", "base_url": "https://careers-noblis.icims.com"},
    {"name": "Perspecta", "base_url": "https://careers-perspecta.icims.com"},
    {"name": "NCI Information Systems", "base_url": "https://careers-nci.icims.com"},
    {"name": "System One", "base_url": "https://careers-systemone.icims.com"},
    {"name": "Genesis10", "base_url": "https://careers-genesis10.icims.com"},
    {"name": "Kforce", "base_url": "https://careers-kforce.icims.com"},
    {"name": "Robert Half", "base_url": "https://careers-roberthalf.icims.com"},
    {"name": "TEKsystems", "base_url": "https://careers-teksystems.icims.com"},
    {"name": "Apex Systems", "base_url": "https://careers-apexsystems.icims.com"},
    {"name": "Insight Global", "base_url": "https://careers-insightglobal.icims.com"},
    {"name": "Collabera", "base_url": "https://careers-collabera.icims.com"},
    {"name": "Signature Consultants", "base_url": "https://careers-sigconsult.icims.com"},
    {"name": "Diversified Search", "base_url": "https://careers-divsearch.icims.com"},
    {"name": "Heidrick & Struggles", "base_url": "https://careers-heidrick.icims.com"},
    {"name": "Korn Ferry", "base_url": "https://careers-kornferry.icims.com"},
    {"name": "Spencer Stuart", "base_url": "https://careers-spencerstuart.icims.com"},
    {"name": "Russell Reynolds", "base_url": "https://careers-russellreynolds.icims.com"},
]

async def check_portal(sem, company):
    name = company["name"]
    base_url = company["base_url"]
    # HCSG corp works best with careers-hcsgcorp.icims.com
    # We want to check: can we fetch it using C:\Windows\System32\curl.exe without headers?
    url = f"{base_url.rstrip('/')}/jobs/search?pr=0&in_iframe=1"
    
    async with sem:
        try:
            proc = await asyncio.create_subprocess_exec(
                "C:\\Windows\\System32\\curl.exe", "-s", "-L", url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            text = stdout.decode('utf-8', errors='ignore')
            
            if proc.returncode == 0 and len(text) > 5000:
                if "Human Verification" in text or "gokuProps" in text:
                    return {"name": name, "base_url": base_url, "status": "WAF_BLOCKED", "count": 0}
                
                # Try to count jobs
                cards = text.split('<li class="iCIMS_JobCardItem">')[1:]
                if cards:
                    return {"name": name, "base_url": base_url, "status": "OK", "count": len(cards)}
                elif "container-fluid iCIMS_JobsTable" in text or "iCIMS_JobCardItem" in text:
                    return {"name": name, "base_url": base_url, "status": "EMPTY_BOARD", "count": 0}
                else:
                    # Let's check if it's actually an iCIMS page at all or 404
                    if "iCIMS" in text or "icims" in text:
                        return {"name": name, "base_url": base_url, "status": "OK_NO_CARDS", "count": 0}
                    else:
                        return {"name": name, "base_url": base_url, "status": "NOT_ICIMS_PAGE", "count": 0}
            else:
                return {"name": name, "base_url": base_url, "status": f"FAILED_HTTP_OR_SHORT_RESP (len={len(text)}, code={proc.returncode})", "count": 0}
        except Exception as e:
            return {"name": name, "base_url": base_url, "status": f"ERROR ({type(e).__name__})", "count": 0}

async def main():
    sem = asyncio.Semaphore(15)
    tasks = [check_portal(sem, c) for c in candidate_companies]
    results = await asyncio.gather(*tasks)
    
    ok_companies = [r for r in results if r["status"] in ("OK", "OK_NO_CARDS", "EMPTY_BOARD")]
    print(f"\nSuccessfully verified portals: {len(ok_companies)}")
    for r in ok_companies:
        print(f"  - {r['name']}: {r['base_url']} (status: {r['status']}, jobs on page 1: {r['count']})")
        
    print("\nFailed portals stats:")
    failed_by_status = {}
    for r in results:
        if r["status"] not in ("OK", "OK_NO_CARDS", "EMPTY_BOARD"):
            failed_by_status[r["status"]] = failed_by_status.get(r["status"], 0) + 1
    for status, count in failed_by_status.items():
        print(f"  - {status}: {count}")

    # Save successful ones to verified_icims.json
    with open("scratch/verified_icims.json", "w") as f:
        json.dump(ok_companies, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
