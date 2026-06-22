# -*- coding: utf-8 -*-
"""
Definition der 5 Test-Segmente (je 20.000 USD) fuer das Musterdepot-Experiment.
Jedes Segment ist ein Korb von Tickern, innerhalb gleichgewichtet.
"""

SEGMENT_CAPITAL = 20_000.0  # USD pro Segment

SEGMENTS = {
    "1_Risiko_Picks": {
        "name": "Eigene Risiko-Picks (Trading-System)",
        "tickers": ["AFL", "LNT", "CTAS"],
    },
    "2_Republikaner": {
        "name": "Republikaner (MAGA-ETF)",
        "tickers": ["MAGA"],
    },
    "3_Demokraten": {
        "name": "Demokraten (DEMZ-ETF)",
        "tickers": ["DEMZ"],
    },
    "4_Trump_nah": {
        "name": "Trump-nah (Trump-Scanner)",
        "tickers": ["DJT", "PLTR", "COIN", "XOM", "LMT"],
    },
    "5_Benchmark": {
        "name": "Benchmark breiter Markt (SPY)",
        "tickers": ["SPY"],
    },
}
