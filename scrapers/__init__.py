# To add a new source: import it here and append an instance to SCRAPER_REGISTRY.
from scrapers.openrouter import OpenRouterScraper
from scrapers.swebench import SWEBenchScraper
from scrapers.artificialanalysis import ArtificialAnalysisScraper
from scrapers.aider import AiderScraper
from scrapers.huggingface import HuggingFaceScraper

SCRAPER_REGISTRY = [
    OpenRouterScraper(),
    SWEBenchScraper(),
    ArtificialAnalysisScraper(),
    AiderScraper(),
    HuggingFaceScraper(),
]
