"""
Immobilien-Scraper Module für verschiedene Quellen
"""

try:
    from .immoscout import run_sync as scrape_immoscout24
    from .immonet import run_sync as scrape_immonet
    from .sparkasse import run_sync as scrape_sparkasse
    from .volksbank import run_sync as scrape_volksbank
    from .kl_immobilien import scrape_kl_immobilien
except ImportError:
    pass

__all__ = [
    "scrape_immoscout24",
    "scrape_immonet",
    "scrape_sparkasse",
    "scrape_volksbank",
    "scrape_kl_immobilien",
]
