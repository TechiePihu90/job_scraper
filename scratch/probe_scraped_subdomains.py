import asyncio
import json

subdomains = [
    {"name": "HERE Technologies", "base_url": "https://careers-here.icims.com"},
    {"name": "Cotiviti", "base_url": "https://careers-cotiviti.icims.com"},
    {"name": "Clinton Health Access Initiative", "base_url": "https://careers-chai.icims.com"},
    {"name": "Teleperformance Engineering", "base_url": "https://careerseng-teleperformance.icims.com"},
    {"name": "IDC Careers (IDG)", "base_url": "https://idccareers-idg.icims.com"},
    {"name": "DMI Inc", "base_url": "https://careers-dminc.icims.com"},
    {"name": "FDM Field Services", "base_url": "https://careers-fdmfieldservices.icims.com"},
    {"name": "Expleo IE", "base_url": "https://expleo-jobs-ie-en.icims.com"},
    {"name": "ERMCO ECI", "base_url": "https://careers-french-ermcoeci.icims.com"},
    {"name": "ISHPI Information Technologies", "base_url": "https://careers-ishpi.icims.com"},
    {"name": "Astoria", "base_url": "https://careers-astoria.icims.com"},
    {"name": "Teleperformance US", "base_url": "https://careersus-teleperformance.icims.com"},
    {"name": "Benaroya Research Institute", "base_url": "https://careers-benaroyaresearch.icims.com"},
    {"name": "Anduril Industries", "base_url": "https://careers-anduril.icims.com"},
    {"name": "Paramount (ViacomCBS)", "base_url": "https://paramount-viacomcbs.icims.com"},
    {"name": "Hyland Software", "base_url": "https://careers-hyland.icims.com"},
    {"name": "Newmarket", "base_url": "https://careers-newmarket.icims.com"},
    {"name": "AIR DC", "base_url": "https://jobs-airdc.icims.com"},
    {"name": "Appalachian Regional Healthcare", "base_url": "https://careers-arh.icims.com"},
    {"name": "SAS Institute", "base_url": "https://globalcareers-sas.icims.com"},
    {"name": "WinCo Foods", "base_url": "https://careers-winco.icims.com"},
    {"name": "Spence and Partners", "base_url": "https://spenceandpartnerscareers-3173.icims.com"},
    {"name": "URS Corporation", "base_url": "https://careers-urs.icims.com"},
    {"name": "Maximus", "base_url": "https://external-maximus.icims.com"},
    {"name": "University of St. Thomas", "base_url": "https://studentemployment-stthomas.icims.com"},
    {"name": "Sunrise Senior Living", "base_url": "https://uscareers-sunriseseniorliving.icims.com"},
    {"name": "Advanced Drainage Systems", "base_url": "https://careers-adspipe.icims.com"},
    {"name": "The CDM Group", "base_url": "https://thecdmgroup.icims.com"},
    {"name": "Omnicom Health Group", "base_url": "https://omnicomhealthgroup.icims.com"},
    {"name": "DNDi", "base_url": "https://careers-dndi.icims.com"},
    {"name": "Marvin", "base_url": "https://careers-marvin.icims.com"},
    {"name": "CommonSpirit Health", "base_url": "https://commonspirit.icims.com"},
    {"name": "Uber University", "base_url": "https://university-uber.icims.com"},
    {"name": "Princeton Plasma Physics Lab", "base_url": "https://pppl-princeton.icims.com"},
    {"name": "BMC Jacksonville", "base_url": "https://external-bmcjax.icims.com"},
    {"name": "Ecumen", "base_url": "https://careers-ecumen.icims.com"},
    {"name": "Accelerate Physical Therapy", "base_url": "https://accelerate-pt-tptp.icims.com"},
    {"name": "At Home Health", "base_url": "https://careers-athomehealth.icims.com"},
    {"name": "Centric Brands", "base_url": "https://careers-centricbrands.icims.com"},
    {"name": "Rural King", "base_url": "https://careers-ruralking.icims.com"},
    {"name": "Prime Healthcare", "base_url": "https://careers-primehealthcare.icims.com"},
    {"name": "Oriental Trading Company", "base_url": "https://careers-orientaltrading.icims.com"},
    {"name": "Utah State University", "base_url": "https://careers-usu.icims.com"},
    {"name": "Intrastaff (Johns Hopkins)", "base_url": "https://careers-intrastaff.icims.com"},
    {"name": "SOS Children's Villages", "base_url": "https://careers-sos-kd.icims.com"},
    {"name": "CFA Supply", "base_url": "https://careers-cfasupply.icims.com"},
    {"name": "Peel Region", "base_url": "https://careers-peelregion.icims.com"},
    {"name": "VRI", "base_url": "https://careers-vri.icims.com"},
    {"name": "Electronic Therapy", "base_url": "https://careers-electronic-therapy.icims.com"},
    {"name": "CHI Health at Home", "base_url": "https://careers-chihealthathome.icims.com"},
    {"name": "VHC Health", "base_url": "https://careers-vhchealth.icims.com"},
    {"name": "Highgate", "base_url": "https://careershub-highgate.icims.com"},
    {"name": "Lowes Foods", "base_url": "https://careers-lowesfoods.icims.com"},
    {"name": "OHSU", "base_url": "https://careersat-ohsu.icims.com"},
    {"name": "Bassett Healthcare", "base_url": "https://learningexperiences-bassett.icims.com"},
    {"name": "Thunder Bay", "base_url": "https://internalen-thunderbay.icims.com"},
    {"name": "Connections Health Solutions", "base_url": "https://careers-connectionshs.icims.com"},
    {"name": "Oak View Group", "base_url": "https://teamwork-ovg.icims.com"},
    {"name": "Ed Morse Automotive Group", "base_url": "https://careers-edmorse.icims.com"},
    {"name": "RS Components", "base_url": "https://careers-rs.icims.com"},
    {"name": "BrightSpring Health Services", "base_url": "https://careers-brightspring.icims.com"},
    {"name": "Ampact", "base_url": "https://servicesite-ampact.icims.com"},
    {"name": "Lennox India", "base_url": "https://indiacareers-lennox.icims.com"},
    {"name": "Artemis Gold", "base_url": "https://careers-artemisgoldinc.icims.com"},
    {"name": "Cajun Industries", "base_url": "https://careers-cajunusa.icims.com"},
    {"name": "Penn Entertainment", "base_url": "https://careersapply-pennentertainment.icims.com"},
    {"name": "Cherokee Nation", "base_url": "https://jobs-cherokeenation.icims.com"},
    {"name": "Omni Interactions", "base_url": "https://omniinteractions.icims.com"},
    {"name": "CoralTree Hospitality", "base_url": "https://careers-coraltreehospitality.icims.com"},
    {"name": "Austin Texas EMS", "base_url": "https://careers-austintexasems.icims.com"},
    {"name": "7-Eleven", "base_url": "https://careers-7-eleven.icims.com"},
    {"name": "Aramark", "base_url": "https://allcareers-aramark.icims.com"},
    {"name": "Amerisafe", "base_url": "https://careers-amerisafe.icims.com"},
    {"name": "Healthcare Services Group", "base_url": "https://careers-hcsgcorp.icims.com"},
    {"name": "Piedmont Healthcare", "base_url": "https://careers-piedmont.icims.com"},
    {"name": "Peraton", "base_url": "https://careers-peraton.icims.com"},
    {"name": "SRI International", "base_url": "https://careers-sri.icims.com"},
    {"name": "LMI", "base_url": "https://careers-lmi.icims.com"},
    {"name": "TEKsystems", "base_url": "https://careers-teksystems.icims.com"},
    {"name": "Sutter Health", "base_url": "https://careers-sutterhealth.icims.com"},
    {"name": "Ascension", "base_url": "https://careers-ascension.icims.com"},
    {"name": "Sidley Austin", "base_url": "https://careers-sidley.icims.com"},
    {"name": "Ryder System", "base_url": "https://careers-ryder.icims.com"},
    {"name": "Aimbridge Hospitality", "base_url": "https://careers-aimbridge.icims.com"},
    {"name": "Vencore", "base_url": "https://careers-vencore.icims.com"},
    {"name": "Korn Ferry", "base_url": "https://careers-kornferry.icims.com"}
]

async def check_portal(sem, company):
    name = company["name"]
    base_url = company["base_url"]
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
                
                # Count jobs
                cards = text.split('<li class="iCIMS_JobCardItem">')[1:]
                if cards:
                    return {"name": name, "base_url": base_url, "status": "OK", "count": len(cards)}
                elif "container-fluid iCIMS_JobsTable" in text or "iCIMS_JobCardItem" in text:
                    return {"name": name, "base_url": base_url, "status": "EMPTY_BOARD", "count": 0}
                else:
                    if "iCIMS" in text or "icims" in text:
                        return {"name": name, "base_url": base_url, "status": "OK_NO_CARDS", "count": 0}
                    else:
                        return {"name": name, "base_url": base_url, "status": "NOT_ICIMS_PAGE", "count": 0}
            else:
                return {"name": name, "base_url": base_url, "status": f"SHORT_RESPONSE (len={len(text)})", "count": 0}
        except Exception as e:
            return {"name": name, "base_url": base_url, "status": f"ERROR ({type(e).__name__})", "count": 0}

async def main():
    sem = asyncio.Semaphore(15)
    tasks = [check_portal(sem, c) for c in subdomains]
    results = await asyncio.gather(*tasks)
    
    ok_companies = [r for r in results if r["status"] in ("OK", "OK_NO_CARDS", "EMPTY_BOARD")]
    print(f"\nTotal portals verified: {len(results)}")
    print(f"Successfully verified working portals: {len(ok_companies)}")
    for r in ok_companies:
        print(f"  - {r['name']}: {r['base_url']} (status: {r['status']}, jobs on page 1: {r['count']})")
        
    # Save active verified ones to verified_icims.json
    with open("scratch/verified_icims.json", "w") as f:
        json.dump(ok_companies, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
