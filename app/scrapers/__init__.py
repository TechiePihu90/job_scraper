# ATS Scrapers
from app.scrapers.greenhouse import GreenhouseScraper
from app.scrapers.lever import LeverScraper
from app.scrapers.workday import WorkdayScraper
from app.scrapers.icims import ICIMSScraper
from app.scrapers.taleo import TaleoScraper
from app.scrapers.successfactors import SuccessFactorsScraper
from app.scrapers.smartrecruiters import SmartRecruitersScraper
from app.scrapers.jobvite import JobviteScraper
from app.scrapers.bamboohr import BambooHRScraper
from app.scrapers.jazzhr import JazzHRScraper
from app.scrapers.zoho_recruit import ZohoRecruitScraper
from app.scrapers.clearcompany import ClearCompanyScraper
from app.scrapers.usajobs import USAJobsScraper
from app.scrapers.dayforce import DayforceScraper
from app.scrapers.ashby import AshbyScraper

SCRAPER_REGISTRY: dict[str, type] = {
    "greenhouse": GreenhouseScraper,
    "lever": LeverScraper,
    "ashby": AshbyScraper,
    "workday": WorkdayScraper,
    "icims": ICIMSScraper,
    "taleo": TaleoScraper,
    "successfactors": SuccessFactorsScraper,
    "smartrecruiters": SmartRecruitersScraper,
    "jobvite": JobviteScraper,
    "bamboohr": BambooHRScraper,
    "jazzhr": JazzHRScraper,
    "zoho_recruit": ZohoRecruitScraper,
    "clearcompany": ClearCompanyScraper,
    "usajobs": USAJobsScraper,
    "dayforce": DayforceScraper,
}
