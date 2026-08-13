#!/usr/bin/env python3
"""Normalize an outbound CSV: names, companies, whitespace, locations.

Never overwrites source columns. Adds "Cleaned <X>" columns plus a
Normalization Flags column listing rows that need a human look.

Phone numbers are passed through completely untouched, on purpose: whatever
value exists (raw, enriched, reformatted later) stays exactly as-is, with no
new column and no reformatting.

Usage:
    python3 normalize.py --in leads.csv --out leads-clean.csv
    python3 normalize.py --in leads.csv --out clean.csv --report report.md
    python3 normalize.py --in leads.csv --out clean.csv --strip-the --strip-tagline
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
import unicodedata
from collections import Counter, OrderedDict

csv.field_size_limit(10_000_000)

# --------------------------------------------------------------------------
# Invisible / lookalike characters
# --------------------------------------------------------------------------

INVISIBLE = {
    " ": " ",  # non-breaking space
    " ": " ",  # narrow nbsp
    " ": " ",  # figure space
    " ": " ",  # thin space
    " ": " ",  # hair space
    "　": " ",  # ideographic space
    "​": "",   # zero-width space
    "‌": "",   # ZWNJ
    "‍": "",   # ZWJ
    "﻿": "",   # BOM
    "­": "",   # soft hyphen
    " ": " ",  # line separator
    " ": " ",  # paragraph separator
    "‘": "'", "’": "'", "‚": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "″": '"',
    "–": "-",  # en dash
    "—": "-",  # em dash
    "‒": "-", "―": "-", "−": "-",
    "…": "...",
}
_INVIS_RE = re.compile("|".join(map(re.escape, INVISIBLE)))

# Mojibake signatures from cp1252 bytes decoded as latin-1/utf-8 confusion.
MOJIBAKE_HINTS = ("Ã©", "Ã¨", "Ã¼", "Ã¶", "Ã±", "Ã¡", "Ã³", "Ã­", "â€™", "â€œ", "â€\x9d", "â€“", "Â ")

NULLISH = {
    "", "-", "--", "n/a", "na", "n.a.", "none", "null", "nil", "nan", "#n/a",
    "unknown", "not available", "not found", "tbd", "?", ".", "0", "false",
    "no data", "undefined", "#value!", "#ref!", "empty",
}

# Placeholders that are not real first names.
BAD_FIRST_NAMES = {
    "there", "team", "hi", "hello", "info", "sales", "support", "admin",
    "contact", "friend", "sir", "madam", "customer", "user", "guest", "test",
    "recruiter", "hiring", "owner", "manager", "founder", "ceo",
}

EMOJI_RE = re.compile(
    "[" "\U0001F000-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF" "\U00002B00-\U00002BFF" "\U0000FE00-\U0000FE0F"
    "\U0001F900-\U0001F9FF" "™®©✓✔✅❌⭐"
    "]+", flags=re.UNICODE,
)

# --------------------------------------------------------------------------
# Person name vocabulary
# --------------------------------------------------------------------------

HONORIFICS = {
    "mr", "mrs", "ms", "miss", "mx", "dr", "prof", "professor", "sir", "dame",
    "lord", "lady", "rev", "reverend", "fr", "father", "hon", "honorable",
    "capt", "captain", "col", "colonel", "gen", "general", "lt", "lieutenant",
    "sgt", "sergeant", "maj", "major", "cmdr", "adm", "eng", "engr", "er",
    "shri", "smt", "sri", "sh", "kum", "adv", "advocate", "justice", "judge",
    "ca", "cs", "cpa", "sr.", "sra", "srta", "herr", "frau", "monsieur",
    "madame", "mlle", "dott", "ing", "arch", "amb", "ambassador",
}

NAME_SUFFIXES = {
    "jr", "sr", "ii", "iii", "iv", "v", "vi", "phd", "ph.d", "md", "m.d",
    "mba", "cpa", "esq", "jd", "dds", "dvm", "rn", "np", "pa", "do", "edd",
    "psyd", "pmp", "cfa", "cissp", "cpm", "csm", "cscp", "cpc", "shrm",
    "sphr", "phr", "msc", "bsc", "ms", "ma", "ba", "bs", "beng", "meng",
    "llb", "llm", "bcom", "mcom", "bba", "acca", "fca", "aca", "ceng",
    "pe", "aia", "leed", "mph", "mha", "mfa", "dphil", "scd", "ret", "usa",
    "usn", "usaf", "cfp", "cfe", "cia", "cma", "cbap", "itil", "aws", "gcp",
    "cka", "ccna", "ccnp", "mcse", "six", "sigma", "prince2", "safe",
}

PRONOUN_RE = re.compile(
    r"[\(\[\{/]?\s*\b(?:he|him|his|she|her|hers|they|them|their|ze|zir|xe)\b"
    r"(?:\s*/\s*\b(?:he|him|his|she|her|hers|they|them|theirs|ze|zir|hir|xem)\b)+"
    r"\s*[\)\]\}/]?",
    re.IGNORECASE,
)

# LinkedIn-style banner text that gets pasted into name fields.
NAME_NOISE_RE = re.compile(
    r"\b(?:open to work|#opentowork|hiring|we'?re hiring|now hiring|is hiring|"
    r"actively hiring|looking for work|seeking|available|ex[- ](?:google|meta|amazon)|"
    r"let'?s connect|dm me|book a call|follow me|linkedin top voice|top voice|"
    r"speaker|author|investor|advisor|mentor|coach|building|helping|"
    r"i help|ex-|f\.?k\.?a\.?)\b.*$",
    re.IGNORECASE,
)

# Lowercase surname particles.
PARTICLES = {
    "van", "von", "der", "den", "de", "del", "dela", "della", "di", "da",
    "das", "dos", "du", "la", "le", "les", "ter", "ten", "af", "av", "bin",
    "binti", "binte", "ibn", "bint", "al", "el", "abu", "ben", "op", "aan",
    "'t", "in", "y", "e", "vander", "vande",
}

# --------------------------------------------------------------------------
# Company vocabulary
# --------------------------------------------------------------------------

# Ordered longest-first so multi-word suffixes win.
LEGAL_SUFFIXES = [
    "limited liability company", "limited liability partnership",
    "public limited company", "private limited company",
    "professional corporation", "professional association",
    "limited partnership", "general partnership", "sole proprietorship",
    "incorporated", "corporation", "companhia", "compagnie", "aktiengesellschaft",
    "gesellschaft mit beschrankter haftung", "besloten vennootschap",
    "naamloze vennootschap", "aktiebolag", "osakeyhtio", "societe anonyme",
    "sociedad anonima", "sociedade anonima", "private limited", "proprietary limited",
    "pvt. ltd.", "pvt ltd.", "pvt. ltd", "pvt ltd", "pte. ltd.", "pte ltd.",
    "pte. ltd", "pte ltd", "pty. ltd.", "pty ltd.", "pty. ltd", "pty ltd",
    "sdn. bhd.", "sdn bhd", "co., ltd.", "co. ltd.", "co ltd", "co.,ltd",
    "s.a. de c.v.", "sa de cv", "s. de r.l.", "s de rl", "s.r.l.", "s.r.o.",
    "sp. z o.o.", "sp z oo", "d.o.o.", "a.s.", "a/s", "k.k.", "y.k.",
    "s.a.s.", "s.a.r.l.", "sarl", "sas", "spa", "s.p.a.", "srl", "gmbh",
    "mbh", "ohg", "kgaa", "kg", "ug", "ag", "nv", "n.v.", "bv", "b.v.",
    "cv", "vof", "ab", "asa", "aps", "oyj", "oy", "kft", "zrt", "nyrt",
    "ltda", "ltda.", "eirl", "sac", "s.a.c.", "cia", "plc", "p.l.c.",
    "llc", "l.l.c.", "llp", "l.l.p.", "lllp", "pllc", "p.c.", "pc",
    "inc.", "inc", "corp.", "corp", "ltd.", "ltd", "limited", "l.p.", "lp",
    "s.a.", "sa", "p.a.", "trust", "gbr", "se", "ek", "ans", "hf", "ehf",
    "tbk", "pt", "jsc", "ojsc", "zao", "oao", "ooo", "pjsc", "fzco", "fze",
    "llc-fz", "dmcc", "wll", "qsc", "ksc", "bsc", "sae", "co.", "company",
    "the company", "and company", "& company", "co",
]

# Suffix tokens that must never be stripped when they are the whole name.
_SUFFIX_ALTS = "|".join(
    re.escape(s).replace(r"\ ", r"\s+") for s in sorted(LEGAL_SUFFIXES, key=len, reverse=True)
)
# Trailing "." / "," after the suffix is common: "Reyes Holdings, L.l.c."
LEGAL_SUFFIX_RE = re.compile(
    r"(?:[,\s]|^)(?:" + _SUFFIX_ALTS + r")[.,]?\s*$", re.IGNORECASE
)

# "Cora, a company of Blank" / ", a subsidiary of X" / "(an Acme company)"
DESCRIPTOR_RE = re.compile(
    r"""(?:
          \s*[,;|\-]\s*(?:an?|the)\s+[^,;|]{0,60}?\s*
              (?:company|business|brand|group|firm|venture|entity|subsidiary|
                 division|unit|portfolio\s+company|agency|studio|practice)\b.*$
        | \s*[,;|\-]\s*(?:an?|the)\s+
              (?:company|subsidiary|division|unit|brand|part|member|affiliate)\s+of\s+.*$
        | \s*[,;|\-]\s*(?:part|member|division|subsidiary|unit|affiliate)\s+of\s+.*$
        | \s*[,;|\-]\s*(?:owned|acquired|backed|operated|powered)\s+by\s+.*$
        | \s*[,;|\-]\s*(?:d/?b/?a|dba|doing\s+business\s+as|f/?k/?a|fka|
                          formerly\s+known\s+as|formerly|now|nee)\b.*$
        | \s*\(\s*(?:an?|the)\s+[^)]{0,60}?
              (?:company|subsidiary|division|brand|group|business)\s*\)\s*
        | \s*\(\s*(?:part|member|division|subsidiary|unit)\s+of\s+[^)]*\)\s*
        | \s*\(\s*(?:formerly|fka|f\.k\.a\.|dba|d/b/a|now|acquired\s+by)\b[^)]*\)\s*
      )""",
    re.IGNORECASE | re.VERBOSE,
)

# Only bracketed markers, or unambiguous ones pinned to the end of the string.
# Never bare mid-name words: "Old Dominion University" must survive intact.
QUALITY_MARKER_RE = re.compile(
    r"""(?:
          \s*[\(\[\{]\s*(?:dupe|duplicate|test|testing|inactive|do\s*not\s*use|
              dnu|obsolete|old|delete|deleted|invalid|sample|demo|placeholder|
              xxx|tbd|unverified|needs\s*review|check|archive[d]?)\s*[\)\]\}]\s*
        | [\s,;\-]+(?:dupe|duplicate|do\s*not\s*use|dnu|inactive|obsolete|
              deleted|placeholder|unverified|needs\s*review)\s*$
      )""",
    re.IGNORECASE | re.VERBOSE,
)

# Marketing tail after a separator: "Stripe | Payments Infrastructure".
TAGLINE_RE = re.compile(r"\s+[|•:]\s+.{4,}$")

ACRONYMS = {
    "IBM", "AT&T", "HP", "HPE", "GE", "3M", "BMW", "BASF", "SAP", "TCS",
    "HCL", "L&T", "ITC", "ONGC", "NTPC", "BPCL", "HDFC", "ICICI", "SBI",
    "IDFC", "RBL", "PNB", "LIC", "GIC", "NSE", "BSE", "KPMG", "PwC", "EY",
    "BCG", "IQVIA", "UBS", "HSBC", "BNP", "ING", "AXA", "AIG", "USAA",
    "CVS", "UPS", "FedEx", "DHL", "IKEA", "H&M", "C&A", "P&G", "J&J",
    "S&P", "M&T", "TD", "RBC", "BMO", "CIBC", "ANZ", "NAB", "DBS", "OCBC",
    "UOB", "NEC", "NTT", "KDDI", "LG", "SK", "GS", "CJ", "TSMC", "ASML",
    "AMD", "ARM", "NXP", "TI", "ST", "NVIDIA", "IBMi", "EMC", "SAS", "AWS",
    "GCP", "IT", "AI", "API", "SaaS", "B2B", "B2C", "CRM", "ERP", "HR",
    "PR", "UX", "UI", "VC", "PE", "REIT", "NGO", "NHS", "BBC", "CNN",
    "NBC", "ABC", "CBS", "ESPN", "MTV", "HBO", "AMC", "AAA", "AARP",
    "NASA", "NATO", "UN", "WHO", "IMF", "WWF", "YMCA", "MIT", "UCLA",
    "USC", "NYU", "LSE", "IIT", "IIM", "ISB", "BITS", "VIT", "SRM",
}

BRAND_CASE = {
    "ebay": "eBay", "iphone": "iPhone", "ipad": "iPad", "imac": "iMac",
    "paypal": "PayPal", "youtube": "YouTube", "linkedin": "LinkedIn",
    "github": "GitHub", "gitlab": "GitLab", "whatsapp": "WhatsApp",
    "tiktok": "TikTok", "snapchat": "Snapchat", "salesforce": "Salesforce",
    "hubspot": "HubSpot", "mailchimp": "Mailchimp", "quickbooks": "QuickBooks",
    "wordpress": "WordPress", "woocommerce": "WooCommerce", "bigcommerce": "BigCommerce",
    "shopify": "Shopify", "netsuite": "NetSuite", "servicenow": "ServiceNow",
    "workday": "Workday", "docusign": "DocuSign", "surveymonkey": "SurveyMonkey",
    "zoominfo": "ZoomInfo", "openai": "OpenAI", "deepmind": "DeepMind",
    "xai": "xAI", "dbt": "dbt", "n8n": "n8n", "youtrack": "YouTrack",
    "jetbrains": "JetBrains", "sendgrid": "SendGrid", "twilio": "Twilio",
    "stripe": "Stripe", "airbnb": "Airbnb", "doordash": "DoorDash",
    "grubhub": "Grubhub", "instacart": "Instacart", "lyft": "Lyft",
    "wework": "WeWork", "byjus": "BYJU'S", "byju's": "BYJU'S",
    "paytm": "Paytm", "phonepe": "PhonePe", "razorpay": "Razorpay",
    "freshworks": "Freshworks", "zoho": "Zoho", "postman": "Postman",
    "browserstack": "BrowserStack", "swiggy": "Swiggy", "zomato": "Zomato",
    "flipkart": "Flipkart", "myntra": "Myntra", "makemytrip": "MakeMyTrip",
    "oyo": "OYO", "olacabs": "Ola", "meesho": "Meesho", "cred": "CRED",
    "zerodha": "Zerodha", "upstox": "Upstox", "groww": "Groww",
    "xoxoday": "Xoxoday", "loylty": "Loylty", "empuls": "Empuls",
    "compass": "Compass", "plum": "Plum", "mcdonalds": "McDonald's",
    "mcdonald's": "McDonald's", "mckinsey": "McKinsey", "mcafee": "McAfee",
    "o'reilly": "O'Reilly", "oreilly": "O'Reilly", "l'oreal": "L'Oreal",
    "3m": "3M", "7-eleven": "7-Eleven", "23andme": "23andMe",
}

# Lowercase inside a title-cased company name.
COMPANY_STOPWORDS = {"of", "and", "the", "for", "in", "on", "at", "to", "by", "de", "la", "von", "van"}

# Short words that are real words, not acronyms. When an ALL-CAPS company name
# is re-cased, any short token NOT in this set is assumed to be an acronym and
# kept uppercase, so "FMFE, CPA" survives but "OLD WORLD" becomes "Old World".
COMMON_SHORT_WORDS = {
    "the", "and", "for", "our", "you", "all", "new", "old", "one", "two", "six",
    "ten", "top", "key", "pro", "max", "web", "net", "sun", "sky", "box", "bay",
    "oak", "red", "big", "way", "car", "air", "gas", "oil", "law", "tax", "pay",
    "buy", "get", "run", "fit", "eat", "joy", "art", "ace", "age", "aim", "arm",
    "bar", "bed", "bit", "bus", "cap", "cat", "cup", "cut", "day", "dog", "ear",
    "egg", "end", "eye", "fan", "far", "few", "fly", "fun", "gap", "gym", "hat",
    "hit", "hot", "ice", "ink", "jar", "job", "kid", "lab", "lap", "leg", "lid",
    "log", "lot", "low", "man", "map", "men", "mix", "now", "nut", "odd", "off",
    "out", "own", "pan", "pen", "pet", "pie", "pig", "pin", "pit", "pot", "pub",
    "raw", "rib", "rim", "row", "rug", "sea", "set", "she", "sit", "ski", "son",
    "tab", "tag", "tan", "tap", "tea", "tie", "tin", "tip", "toe", "ton", "toy",
    "try", "use", "van", "war", "wax", "wet", "win", "zip", "inn", "eco", "bio",
    "real", "test", "best", "care", "home", "life", "work", "tech", "data",
    "food", "bank", "city", "east", "west", "gold", "high", "land", "main",
    "next", "open", "park", "plus", "pure", "road", "safe", "star", "true",
    "view", "wave", "wise", "zero", "blue", "bold", "core", "edge", "fast",
    "fine", "fire", "free", "good", "grow", "help", "idea", "king", "lead",
    "link", "live", "look", "love", "mind", "move", "nova", "only", "path",
    "peak", "plan", "play", "rise", "rock", "sage", "seed", "ship", "site",
    "soft", "solo", "span", "spot", "sure", "team", "time", "tree", "unit",
    "vast", "well", "wide", "wild", "wood", "yard", "your", "auto", "with",
    "from", "into", "over", "more", "less", "each", "both", "some", "such",
}

# --------------------------------------------------------------------------
# Location vocabulary
# --------------------------------------------------------------------------

COUNTRY_CANON = {
    "us": "United States", "usa": "United States", "u.s.": "United States",
    "u.s.a.": "United States", "united states of america": "United States",
    "america": "United States", "united states": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "britain": "United Kingdom",
    "great britain": "United Kingdom", "england": "United Kingdom",
    "scotland": "United Kingdom", "wales": "United Kingdom",
    "northern ireland": "United Kingdom", "united kingdom": "United Kingdom",
    "uae": "United Arab Emirates", "u.a.e.": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates", "emirates": "United Arab Emirates",
    "india": "India", "bharat": "India", "republic of india": "India",
    "germany": "Germany", "deutschland": "Germany",
    "netherlands": "Netherlands", "holland": "Netherlands", "the netherlands": "Netherlands",
    "south korea": "South Korea", "korea": "South Korea", "republic of korea": "South Korea",
    "russia": "Russia", "russian federation": "Russia",
    "czechia": "Czech Republic", "czech republic": "Czech Republic",
    "turkiye": "Turkey", "turkey": "Turkey", "türkiye": "Turkey",
    "ivory coast": "Cote d'Ivoire", "cote d'ivoire": "Cote d'Ivoire",
    "burma": "Myanmar", "myanmar": "Myanmar",
    "swaziland": "Eswatini", "eswatini": "Eswatini",
    "macedonia": "North Macedonia", "north macedonia": "North Macedonia",
    "vietnam": "Vietnam", "viet nam": "Vietnam",
    "philippines": "Philippines", "the philippines": "Philippines",
    "brasil": "Brazil", "brazil": "Brazil",
    "mexico": "Mexico", "méxico": "Mexico",
    "china": "China", "prc": "China", "mainland china": "China",
    "hong kong": "Hong Kong", "hong kong sar": "Hong Kong", "hongkong": "Hong Kong",
    "taiwan": "Taiwan", "republic of china": "Taiwan",
    "japan": "Japan", "nippon": "Japan",
    "spain": "Spain", "españa": "Spain", "espana": "Spain",
    "italy": "Italy", "italia": "Italy",
    "france": "France", "switzerland": "Switzerland", "schweiz": "Switzerland",
    "sweden": "Sweden", "sverige": "Sweden", "ireland": "Ireland", "eire": "Ireland",
    "canada": "Canada", "australia": "Australia", "new zealand": "New Zealand",
    "singapore": "Singapore", "malaysia": "Malaysia", "indonesia": "Indonesia",
    "thailand": "Thailand", "saudi arabia": "Saudi Arabia", "ksa": "Saudi Arabia",
    "south africa": "South Africa", "rsa": "South Africa",
    "poland": "Poland", "polska": "Poland", "portugal": "Portugal",
    "belgium": "Belgium", "austria": "Austria", "österreich": "Austria",
    "denmark": "Denmark", "norway": "Norway", "finland": "Finland",
    "israel": "Israel", "egypt": "Egypt", "nigeria": "Nigeria", "kenya": "Kenya",
    "argentina": "Argentina", "chile": "Chile", "colombia": "Colombia",
    "peru": "Peru", "romania": "Romania", "greece": "Greece", "hungary": "Hungary",
    "ukraine": "Ukraine", "pakistan": "Pakistan", "bangladesh": "Bangladesh",
    "sri lanka": "Sri Lanka", "nepal": "Nepal", "qatar": "Qatar",
    "kuwait": "Kuwait", "bahrain": "Bahrain", "oman": "Oman", "jordan": "Jordan",
    "luxembourg": "Luxembourg", "monaco": "Monaco", "malta": "Malta",
    "estonia": "Estonia", "latvia": "Latvia", "lithuania": "Lithuania",
    "iceland": "Iceland", "croatia": "Croatia", "slovenia": "Slovenia",
    "slovakia": "Slovakia", "bulgaria": "Bulgaria", "serbia": "Serbia",
}

COUNTRY_ISO2 = {
    "United States": "US", "United Kingdom": "GB", "India": "IN", "Canada": "CA",
    "Australia": "AU", "Germany": "DE", "France": "FR", "Spain": "ES",
    "Italy": "IT", "Netherlands": "NL", "Belgium": "BE", "Switzerland": "CH",
    "Austria": "AT", "Sweden": "SE", "Norway": "NO", "Denmark": "DK",
    "Finland": "FI", "Ireland": "IE", "Poland": "PL", "Portugal": "PT",
    "Czech Republic": "CZ", "Romania": "RO", "Greece": "GR", "Hungary": "HU",
    "Ukraine": "UA", "Russia": "RU", "Turkey": "TR", "Israel": "IL",
    "United Arab Emirates": "AE", "Saudi Arabia": "SA", "Qatar": "QA",
    "Kuwait": "KW", "Bahrain": "BH", "Oman": "OM", "Jordan": "JO",
    "Egypt": "EG", "Nigeria": "NG", "Kenya": "KE", "South Africa": "ZA",
    "Brazil": "BR", "Mexico": "MX", "Argentina": "AR", "Chile": "CL",
    "Colombia": "CO", "Peru": "PE", "China": "CN", "Hong Kong": "HK",
    "Taiwan": "TW", "Japan": "JP", "South Korea": "KR", "Singapore": "SG",
    "Malaysia": "MY", "Indonesia": "ID", "Thailand": "TH", "Vietnam": "VN",
    "Philippines": "PH", "Pakistan": "PK", "Bangladesh": "BD",
    "Sri Lanka": "LK", "Nepal": "NP", "New Zealand": "NZ", "Luxembourg": "LU",
    "Monaco": "MC", "Malta": "MT", "Estonia": "EE", "Latvia": "LV",
    "Lithuania": "LT", "Iceland": "IS", "Croatia": "HR", "Slovenia": "SI",
    "Slovakia": "SK", "Bulgaria": "BG", "Serbia": "RS", "Myanmar": "MM",
    "Eswatini": "SZ", "North Macedonia": "MK", "Cote d'Ivoire": "CI",
}

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia", "PR": "Puerto Rico",
}
US_STATE_BY_NAME = {v.lower(): k for k, v in US_STATES.items()}

CITY_CANON = {
    "bangalore": "Bengaluru", "bengaluru": "Bengaluru", "blr": "Bengaluru",
    "bombay": "Mumbai", "mumbai": "Mumbai", "calcutta": "Kolkata",
    "kolkata": "Kolkata", "madras": "Chennai", "chennai": "Chennai",
    "gurgaon": "Gurugram", "gurugram": "Gurugram", "poona": "Pune",
    "pune": "Pune", "trivandrum": "Thiruvananthapuram", "cochin": "Kochi",
    "baroda": "Vadodara", "mysore": "Mysuru", "noida": "Noida",
    "new delhi": "New Delhi", "delhi": "Delhi", "ncr": "Delhi",
    "hyderabad": "Hyderabad", "ahmedabad": "Ahmedabad",
    "nyc": "New York", "new york city": "New York", "new york": "New York",
    "sf": "San Francisco", "san fran": "San Francisco", "frisco": "San Francisco",
    "la": "Los Angeles", "l.a.": "Los Angeles", "philly": "Philadelphia",
    "d.c.": "Washington", "washington dc": "Washington", "washington d.c.": "Washington",
    "peking": "Beijing", "beijing": "Beijing", "canton": "Guangzhou",
    "saigon": "Ho Chi Minh City", "ho chi minh": "Ho Chi Minh City",
    "kiev": "Kyiv", "kyiv": "Kyiv", "constantinople": "Istanbul",
    "istanbul": "Istanbul", "rangoon": "Yangon",
}

# Not places. Route these out of the location columns.
NON_LOCATIONS = {
    "remote", "fully remote", "remote - us", "worldwide", "global",
    "anywhere", "distributed", "work from home", "wfh", "hybrid",
    "emea", "apac", "apj", "amer", "americas", "latam", "nam", "na",
    "north america", "europe", "asia", "asia pacific", "middle east",
    "mena", "dach", "benelux", "nordics", "anz", "sea", "gcc",
}

_ISO2_TO_COUNTRY = {v: k for k, v in COUNTRY_ISO2.items()}

# --------------------------------------------------------------------------
# Column detection
# --------------------------------------------------------------------------

COLUMN_ALIASES = OrderedDict([
    ("full_name", ["full name", "fullname", "name", "contact name", "person name",
                   "lead name", "prospect name", "display name", "full_name"]),
    ("first_name", ["first name", "firstname", "fname", "first", "given name",
                    "forename", "first_name", "givenname"]),
    ("last_name", ["last name", "lastname", "lname", "last", "surname",
                   "family name", "last_name", "familyname"]),
    ("company", ["company", "company name", "companyname", "organization",
                 "organisation", "org", "account", "account name", "employer",
                 "company name for emails", "current company", "company_name",
                 "business name", "firm", "employer name"]),
    ("city", ["city", "town", "company city", "locality", "person city"]),
    ("state", ["state", "province", "region", "state/province", "company state",
               "state or province", "person state"]),
    ("country", ["country", "company country", "nation", "person country",
                 "country/region"]),
    ("location", ["location", "address", "full address", "geo", "place",
                  "company address", "hq", "headquarters", "hq location",
                  "based in", "company location", "person location"]),
    ("email", ["email", "email address", "e-mail", "work email", "primary email",
               "business email", "email_address"]),
    ("title", ["title", "job title", "position", "role", "designation",
               "job_title", "current title"]),
])


def norm_header(h):
    h = _INVIS_RE.sub(lambda m: INVISIBLE[m.group()], h or "")
    h = re.sub(r"[^a-z0-9]+", " ", h.lower()).strip()
    return h


def detect_columns(headers):
    """Map logical role -> actual header. First match wins per role."""
    found = {}
    normed = [(i, norm_header(h), h) for i, h in enumerate(headers)]
    for role, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            a = norm_header(alias)
            for _, nh, orig in normed:
                if nh == a and orig not in found.values():
                    found[role] = orig
                    break
            if role in found:
                break
    return found


# --------------------------------------------------------------------------
# Whitespace / text hygiene
# --------------------------------------------------------------------------

def fix_mojibake(s):
    if not s or not any(h in s for h in MOJIBAKE_HINTS):
        return s
    try:
        return s.encode("cp1252", errors="strict").decode("utf-8", errors="strict")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def clean_ws(s, drop_emoji=False):
    """Normalize whitespace, invisibles, smart punctuation. Never drops letters."""
    if s is None:
        return ""
    s = str(s)
    s = fix_mojibake(s)
    s = unicodedata.normalize("NFC", s)
    s = _INVIS_RE.sub(lambda m: INVISIBLE[m.group()], s)
    s = s.replace("&amp;", "&").replace("&nbsp;", " ").replace("&quot;", '"')
    s = s.replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
    if drop_emoji:
        s = EMOJI_RE.sub(" ", s)
    s = re.sub(r"[\t\r\n\f\v]+", " ", s)
    s = re.sub(r" {2,}", " ", s)
    s = re.sub(r"\s+([,;:.!?])", r"\1", s)
    s = re.sub(r"([(\[])\s+", r"\1", s)
    s = re.sub(r"\s+([)\]])", r"\1", s)
    return s.strip()


def is_nullish(s):
    return clean_ws(s).strip(" .-_").lower() in NULLISH


def strip_wrapping_quotes(s):
    for _ in range(3):
        t = s.strip()
        if len(t) > 1 and t[0] == t[-1] and t[0] in "\"'":
            s = t[1:-1]
        else:
            break
    return s.strip()


def is_all_caps(s):
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters) and len(letters) > 1


def is_all_lower(s):
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and all(c.islower() for c in letters)


def needs_recase(s):
    """Only re-case strings that are uniformly cased. Mixed case is intentional."""
    return is_all_caps(s) or is_all_lower(s)


# --------------------------------------------------------------------------
# Person names
# --------------------------------------------------------------------------

def _case_name_token(tok):
    if not tok:
        return tok
    low = tok.lower().strip(".")
    if low in PARTICLES:
        return tok.lower()
    parts = re.split(r"([-'’])", tok)
    out = []
    for p in parts:
        if p in "-'’":
            out.append(p)
            continue
        if not p:
            continue
        # Initials: "j.r." -> "J.R."
        if re.fullmatch(r"(?:[a-z]\.){1,4}", p.lower()):
            out.append(p.upper())
            continue
        p = p[:1].upper() + p[1:].lower()
        if re.fullmatch(r"Mc[a-z]{3,}", p):
            p = "Mc" + p[2:3].upper() + p[3:]
        out.append(p)
    res = "".join(out)
    # Apostrophe surnames: O'brien -> O'Brien (but not "D'".. single letter guard ok)
    res = re.sub(r"\b([A-Z]')([a-z])", lambda m: m.group(1) + m.group(2).upper(), res)
    return res


def case_person_name(s):
    if not needs_recase(s):
        return s
    return " ".join(_case_name_token(t) for t in s.split(" ") if t)


def clean_person_name(raw):
    """Return (clean_name, flags)."""
    flags = []
    s = clean_ws(raw, drop_emoji=True)
    s = strip_wrapping_quotes(s)
    if not s or is_nullish(s):
        return "", ["name_empty"] if raw and str(raw).strip() else []

    if s[:1] in ("=", "+", "@") or "!" in s and re.search(r"[A-Z]+\d+", s):
        return "", ["formula_injection_blocked"]
    if "@" in s and re.search(r"[\w.+-]+@[\w-]+\.\w+", s):
        flags.append("name_looks_like_email")
    if re.search(r"https?://|linkedin\.com/", s, re.I):
        flags.append("name_contains_url")
        s = re.sub(r"https?://\S+", " ", s)

    s = PRONOUN_RE.sub(" ", s)
    s = NAME_NOISE_RE.sub(" ", s)
    # Nickname in quotes or parens: John "Jack" Smith
    if re.search(r"[\"'“(].{1,20}[\"'”)]", s):
        nick = re.search(r"[\"“(]\s*([^\"”)]{1,20})\s*[\"”)]", s)
        if nick:
            flags.append("nickname_removed:" + nick.group(1).strip())
        s = re.sub(r"\s*[\"“(][^\"”)]{1,20}[\"”)]\s*", " ", s)
    s = re.sub(r"\s*[|/•·]+\s*.*$", " ", s)  # trailing banner after separator
    s = clean_ws(s)

    # "Smith, John" -> "John Smith", but only if the tail is not a credential.
    if s.count(",") == 1:
        head, tail = [p.strip() for p in s.split(",")]
        tail_tokens = [t.strip(". ").lower() for t in re.split(r"[\s]+", tail) if t.strip(". ")]
        if tail_tokens and not any(t in NAME_SUFFIXES for t in tail_tokens) \
                and len(tail_tokens) <= 2 and head and len(head.split()) <= 3:
            s = tail + " " + head
            flags.append("name_uninverted")

    s = re.sub(r"[,;]+", " ", s)
    tokens = [t for t in clean_ws(s).split(" ") if t]

    # Strip leading honorifics.
    while tokens and tokens[0].strip(".").lower() in HONORIFICS:
        tokens.pop(0)
    # Strip trailing credentials / generational suffixes.
    dropped = []
    while tokens and tokens[-1].strip(".,").lower() in NAME_SUFFIXES:
        dropped.append(tokens.pop())
    if dropped:
        flags.append("suffix_removed:" + ",".join(reversed(dropped)))

    tokens = [t for t in tokens if t.strip(".,-'")]
    if not tokens:
        return "", flags + ["name_empty_after_clean"]

    name = case_person_name(" ".join(tokens))
    if len(tokens) == 1:
        flags.append("mononym")
    if tokens[0].lower().strip(".") in BAD_FIRST_NAMES:
        flags.append("placeholder_first_name")
    if len(tokens) > 4:
        flags.append("name_unusually_long")
    if not re.search(r"[A-Za-zÀ-ɏЀ-ӿऀ-ॿ]", name):
        flags.append("name_no_letters")
    return name, flags


def split_name(full):
    """First = leading token. Last = the rest (keeps particles and compounds intact)."""
    toks = [t for t in full.split(" ") if t]
    if not toks:
        return "", ""
    if len(toks) == 1:
        return toks[0], ""
    return toks[0], " ".join(toks[1:])


# --------------------------------------------------------------------------
# Companies
# --------------------------------------------------------------------------

def _case_company_token(tok, first, src_all_caps=False):
    low = tok.lower()
    if low in BRAND_CASE:
        return BRAND_CASE[low]
    up = tok.upper()
    for a in ACRONYMS:
        if a.upper() == up:
            return a
    if low in COMPANY_STOPWORDS and not first:
        return low
    # Short all-caps token that is not an ordinary word: treat as an acronym.
    core = low.strip(".,&-'")
    if src_all_caps and 1 < len(core) <= 4 and core.isalnum() \
            and any(c.isalpha() for c in core) and core not in COMMON_SHORT_WORDS:
        return tok.upper()
    if re.fullmatch(r"[0-9]+[a-z]*", low):
        return low.upper() if len(low) <= 3 else tok
    parts = re.split(r"([-'&./])", tok)
    out = []
    for p in parts:
        if p in "-'&./" or not p:
            out.append(p)
            continue
        pl = p.lower()
        if pl in BRAND_CASE:
            out.append(BRAND_CASE[pl])
            continue
        c = p[:1].upper() + p[1:].lower()
        if re.fullmatch(r"Mc[a-z]{3,}", c):
            c = "Mc" + c[2:3].upper() + c[3:]
        out.append(c)
    return "".join(out)


def case_company(s):
    if not needs_recase(s):
        return s
    caps = is_all_caps(s)
    toks = [t for t in s.split(" ") if t]
    return " ".join(_case_company_token(t, i == 0, caps) for i, t in enumerate(toks))


def clean_company(raw, strip_the=False, strip_tagline=False, strip_geo=False):
    """Return (clean_company, flags)."""
    flags = []
    s = clean_ws(raw, drop_emoji=True)
    s = strip_wrapping_quotes(s)
    if not s or is_nullish(s):
        return "", ["company_empty"] if raw and str(raw).strip() else []

    original = s

    if QUALITY_MARKER_RE.search(s):
        flags.append("quality_marker_removed")
        s = QUALITY_MARKER_RE.sub(" ", s)

    # Bare domain in the company column.
    if re.fullmatch(r"(?:https?://)?(?:www\.)?[a-z0-9-]+(?:\.[a-z]{2,}){1,2}/?", s, re.I):
        host = re.sub(r"^(?:https?://)?(?:www\.)?", "", s, flags=re.I).rstrip("/")
        s = host.split(".")[0].replace("-", " ")
        flags.append("derived_from_domain")

    if DESCRIPTOR_RE.search(s):
        flags.append("descriptor_removed")
        s = DESCRIPTOR_RE.sub(" ", s)

    if strip_tagline and TAGLINE_RE.search(s):
        flags.append("tagline_removed")
        s = TAGLINE_RE.sub("", s)

    # Parentheticals: drop geo/notes only when asked, else keep.
    if strip_geo:
        s2 = re.sub(r"\s*\([^)]{1,25}\)\s*$", " ", s)
        if s2.strip() != s.strip():
            flags.append("parenthetical_removed")
            s = s2

    s = clean_ws(s)

    # Strip stacked legal suffixes, longest first, never to empty.
    for _ in range(4):
        m = LEGAL_SUFFIX_RE.search(s)
        if not m:
            break
        candidate = clean_ws(s[: m.start()]).strip(" ,.-&/")
        # "The Limited" / "Company" must not collapse to "The" or "".
        residue = [t for t in candidate.lower().split() if t not in COMPANY_STOPWORDS]
        if not candidate or not residue or not re.search(r"[A-Za-zÀ-ɏ]", candidate):
            flags.append("suffix_is_whole_name_kept")
            break
        s = candidate
        flags.append("legal_suffix_removed")

    s = clean_ws(s).strip(" ,;:.-|/&")

    if strip_the and re.match(r"^the\s+", s, re.I) and len(s.split()) > 1:
        s = s[4:].strip()
        flags.append("leading_the_removed")

    # "Johnson and Johnson" -> "Johnson & Johnson"
    s = re.sub(r"(?<=\w)\s+and\s+(?=[A-Z])", " & ", s)
    s = re.sub(r"\s*&\s*", " & ", s)
    s = clean_ws(s)
    s = case_company(s)

    if not s:
        flags.append("company_empty_after_clean")
        return clean_ws(original), flags
    if len(s) > 60:
        flags.append("company_unusually_long")
    if re.search(r"[<>{}\\]|\bhttp", s, re.I):
        flags.append("company_has_markup")
    if s.lower() != original.lower() and "legal_suffix_removed" not in flags and not flags:
        pass
    return s, sorted(set(flags))


# --------------------------------------------------------------------------
# Locations
# --------------------------------------------------------------------------

def canon_country(value, in_country_column=True):
    """Return (country_name, iso2, flags)."""
    flags = []
    v = clean_ws(value)
    if not v or is_nullish(v):
        return "", "", []
    low = v.strip(". ").lower()

    if low in NON_LOCATIONS:
        return "", "", ["not_a_country:" + low]

    if low in COUNTRY_CANON:
        name = COUNTRY_CANON[low]
        if low in ("england", "scotland", "wales", "northern ireland"):
            flags.append("uk_constituent_mapped:" + low)
        return name, COUNTRY_ISO2.get(name, ""), flags

    up = v.strip(". ").upper()
    if len(up) == 2:
        # "CA" is California in a state column, Canada in a country column.
        if up == "CA" and not in_country_column:
            return "", "", ["ambiguous_ca_treated_as_state"]
        if up in _ISO2_TO_COUNTRY:
            return _ISO2_TO_COUNTRY[up], up, flags
    if len(up) == 3:
        three = {"USA": "US", "GBR": "GB", "IND": "IN", "CAN": "CA", "AUS": "AU",
                 "DEU": "DE", "FRA": "FR", "SGP": "SG", "ARE": "AE", "JPN": "JP"}
        if up in three:
            return _ISO2_TO_COUNTRY[three[up]], three[up], flags

    return v.title() if needs_recase(v) else v, "", ["country_unmapped"]


def canon_state(value, country_iso2=""):
    flags = []
    v = clean_ws(value)
    if not v or is_nullish(v):
        return "", "", []
    up = v.strip(". ").upper()
    low = v.strip(". ").lower()
    if low in NON_LOCATIONS:
        return "", "", ["not_a_state:" + low]
    if len(up) == 2 and up in US_STATES:
        return US_STATES[up], up, flags
    if low in US_STATE_BY_NAME:
        return v.title() if needs_recase(v) else v, US_STATE_BY_NAME[low], flags
    out = v.title() if needs_recase(v) else v
    # Only US/CA states have a code table here; elsewhere a plain name is fine.
    return out, "", (["state_unmapped"] if country_iso2 in ("US", "CA") else [])


def canon_city(value):
    flags = []
    v = clean_ws(value)
    if not v or is_nullish(v):
        return "", []
    low = v.strip(". ").lower()
    if low in NON_LOCATIONS:
        return "", ["not_a_city:" + low]
    # LinkedIn style: "Greater Boston Area", "Bengaluru Area, India"
    m = re.match(r"^(?:greater\s+)?(.*?)\s+(?:metropolitan\s+)?area$", low)
    if m:
        low = m.group(1).strip()
        v = low
        flags.append("area_suffix_removed")
    low = re.sub(r"\s+(?:bay|metro|metropolitan|region|district)$", "", low).strip()
    if low in CITY_CANON:
        return CITY_CANON[low], flags
    v = clean_ws(v)
    return (v.title() if needs_recase(v) else v), flags


def parse_location(value, known_country=""):
    """Split a free-text location into (city, state, country, flags).

    known_country: the row's Country column value, if it came from its own
    column rather than being parsed out of this same string. When present, a
    trailing two-letter token is resolved as a US state before it is ever
    considered a country code — several state abbreviations collide with ISO2
    country codes (CA/Canada, IN/India, GA/Georgia, DE/Germany, VA/Vatican),
    and a Country column that already has a real value settles the question.
    """
    flags = []
    v = clean_ws(value)
    if not v or is_nullish(v):
        return "", "", "", []
    if v.strip().lower() in NON_LOCATIONS:
        return "", "", "", ["non_geographic_location:" + v.strip().lower()]

    v = re.sub(r"\b\d{4,6}(?:-\d{4})?\b\s*$", "", v).strip(" ,")  # trailing postal code
    parts = [p.strip() for p in re.split(r"\s*,\s*", v) if p.strip()]

    city = state = country = ""
    if len(parts) >= 3:
        city, state, country = parts[0], parts[-2], parts[-1]
        if len(parts) > 3:
            flags.append("location_extra_parts_dropped")
    elif len(parts) == 2:
        a, b = parts
        if known_country and b.strip(". ").upper() in US_STATES:
            city, state = a, b
        else:
            cn, iso, _ = canon_country(b, in_country_column=True)
            if iso or cn in COUNTRY_ISO2:
                city, country = a, b
            else:
                city, state = a, b
    elif len(parts) == 1:
        one = parts[0]
        cn, iso, _ = canon_country(one, in_country_column=True)
        if iso:
            country = one
            if cn in ("Singapore", "Hong Kong", "Monaco", "Luxembourg", "Malta"):
                city = cn
                flags.append("city_state_country")
        elif one.strip(". ").upper() in US_STATES:
            state, country = one, "United States"
        else:
            city = one
    return city, state, country, flags


# --------------------------------------------------------------------------
# CSV reading
# --------------------------------------------------------------------------

def read_csv_smart(path):
    """Return (headers, rows, meta) tolerating encoding, delimiter, preamble rows."""
    with open(path, "rb") as fh:
        raw = fh.read()
    meta = {}
    encoding = "utf-8-sig"
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            from charset_normalizer import from_bytes
            best = from_bytes(raw).best()
            encoding = (best.encoding if best else "cp1252")
            text = raw.decode(encoding, errors="replace")
        except Exception:
            encoding = "cp1252"
            text = raw.decode("cp1252", errors="replace")
    meta["encoding"] = encoding

    sample = text[:65536]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delim = dialect.delimiter
    except csv.Error:
        counts = {d: sample.count(d) for d in ",;\t|"}
        delim = max(counts, key=counts.get) if max(counts.values()) else ","
    meta["delimiter"] = repr(delim)

    all_rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    all_rows = [r for r in all_rows if any(c.strip() for c in r)]
    if not all_rows:
        raise SystemExit("No data rows found in " + path)

    # Header row = first row whose filled-cell count matches the modal width
    # and that has no obviously duplicated blanks. Handles preamble/title rows.
    widths = Counter(sum(1 for c in r if c.strip()) for r in all_rows[:50])
    modal = widths.most_common(1)[0][0]
    hdr_idx = 0
    # A single-column file has no fill-count signal to separate a preamble row
    # from the real header (every row has exactly 1 filled cell), so any row
    # that happens to parse into 2+ fields — e.g. an unquoted comma inside one
    # value — would otherwise be mistaken for the header. Trust row 0 instead.
    if modal > 1:
        for i, r in enumerate(all_rows[:20]):
            filled = sum(1 for c in r if c.strip())
            if filled >= max(2, modal - 1):
                hdr_idx = i
                break
    if hdr_idx:
        meta["preamble_rows_skipped"] = hdr_idx

    headers = [clean_ws(h) for h in all_rows[hdr_idx]]
    seen = {}
    for i, h in enumerate(headers):
        if not h:
            headers[i] = "Column {}".format(i + 1)
        if headers[i] in seen:
            seen[headers[i]] += 1
            headers[i] = "{} ({})".format(headers[i], seen[headers[i]])
        else:
            seen[headers[i]] = 0

    width = len(headers)
    rows, ragged = [], 0
    for r in all_rows[hdr_idx + 1:]:
        if len(r) != width:
            ragged += 1
            r = (r + [""] * width)[:width]
        rows.append(OrderedDict(zip(headers, [clean_ws(c) for c in r])))
    if ragged:
        meta["ragged_rows_padded"] = ragged
    meta["rows_in"] = len(rows)
    return headers, rows, meta


def excel_safe(value):
    """Neutralize CSV formula injection without altering the visible text.

    "+" or "-" immediately followed by a digit is a real number (a phone
    number in E.164, a negative amount), not a formula, and is left alone.
    """
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r") and not re.match(r"^[+-]?\d", value):
        return "'" + value
    return value


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out", dest="outfile", required=True)
    ap.add_argument("--strip-the", action="store_true", help='Drop leading "The" from company names')
    ap.add_argument("--strip-tagline", action="store_true", help='Drop "| tagline" tails from company names')
    ap.add_argument("--strip-geo", action="store_true", help="Drop trailing (US)/(EMEA) parentheticals")
    ap.add_argument("--report", default="", help="Write a markdown QA report here")
    args = ap.parse_args()

    headers, rows, meta = read_csv_smart(args.infile)
    cols = detect_columns(headers)
    new_cols = []

    def add_col(name):
        if name not in headers and name not in new_cols:
            new_cols.append(name)
        return name

    has_full = "full_name" in cols
    has_first = "first_name" in cols
    has_last = "last_name" in cols
    if has_full or has_first or has_last:
        add_col("Cleaned Full Name")
        add_col("Cleaned First Name")
        add_col("Cleaned Last Name")
    if "company" in cols:
        add_col("Cleaned Company")
    loc_roles = [r for r in ("city", "state", "country", "location") if r in cols]
    if loc_roles:
        add_col("Cleaned City")
        add_col("Cleaned State")
        add_col("Cleaned State Code")
        add_col("Cleaned Country")
        add_col("Country Code")
    add_col("Normalization Flags")

    flag_counter = Counter()
    changed = Counter()

    for row in rows:
        flags = []

        # ---- names ----
        if has_full or has_first or has_last:
            raw_full = row.get(cols["full_name"], "") if has_full else ""
            raw_first = row.get(cols["first_name"], "") if has_first else ""
            raw_last = row.get(cols["last_name"], "") if has_last else ""

            source = raw_full
            if not source.strip():
                source = " ".join(p for p in (raw_first, raw_last) if p.strip())
            # First-name column that actually holds the whole name.
            elif has_first and not raw_last.strip() and len(raw_first.split()) > 1:
                flags.append("full_name_in_first_name_column")

            if not raw_full.strip() and has_first and not raw_last.strip() \
                    and len(raw_first.split()) > 1:
                flags.append("full_name_in_first_name_column")

            full_clean, nf = clean_person_name(source)
            flags.extend(nf)
            first, last = split_name(full_clean)
            # Trust an explicit, single-token last-name column over the split.
            if raw_last.strip() and full_clean:
                lc, lf = clean_person_name(raw_last)
                if lc and lc.lower() != last.lower() and lc.lower() in full_clean.lower():
                    last = lc
            row["Cleaned Full Name"] = full_clean
            row["Cleaned First Name"] = first
            row["Cleaned Last Name"] = last
            if full_clean and full_clean != clean_ws(source):
                changed["name"] += 1

        # ---- company ----
        if "company" in cols:
            raw_co = row.get(cols["company"], "")
            co, cf = clean_company(raw_co, args.strip_the, args.strip_tagline, args.strip_geo)
            row["Cleaned Company"] = co
            flags.extend(cf)
            if co and co != clean_ws(raw_co):
                changed["company"] += 1

        # ---- location ----
        city = state = country = ""
        if loc_roles:
            if "city" in cols:
                city = row.get(cols["city"], "")
            if "state" in cols:
                state = row.get(cols["state"], "")
            if "country" in cols:
                country = row.get(cols["country"], "")
            # Parse the free-text Location column whenever city/state are still
            # missing, even if Country already came from its own column.
            if "location" in cols and not (city or state):
                pc, ps, pcn, lf = parse_location(row.get(cols["location"], ""), known_country=country)
                city, state = pc, ps
                if not country:
                    country = pcn
                flags.extend(lf)

            cn, iso, cf2 = canon_country(country, in_country_column=True)
            sn, sc, sf = canon_state(state, iso)
            ci, cif = canon_city(city)
            if sc and not iso:
                cn, iso = "United States", "US"
                cf2 = cf2 + ["country_inferred_from_state"]
            row["Cleaned City"] = ci
            row["Cleaned State"] = sn
            row["Cleaned State Code"] = sc
            row["Cleaned Country"] = cn
            row["Country Code"] = iso
            flags.extend(cf2 + sf + cif)

        flags = sorted(set(f for f in flags if f))
        for f in flags:
            flag_counter[f.split(":")[0]] += 1
        row["Normalization Flags"] = " | ".join(flags)

    out_headers = list(headers) + [c for c in new_cols if c not in headers]
    outdir = os.path.dirname(os.path.abspath(args.outfile))
    if outdir and not os.path.isdir(outdir):
        os.makedirs(outdir, exist_ok=True)
    with open(args.outfile, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=out_headers, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: excel_safe(row.get(k, "")) for k in out_headers})

    lines = []
    lines.append("# Normalization report\n")
    lines.append("**Input:** `{}`  ".format(args.infile))
    lines.append("**Output:** `{}`\n".format(args.outfile))
    lines.append("## File\n")
    for k, v in meta.items():
        lines.append("- {}: {}".format(k.replace("_", " "), v))
    lines.append("- rows out: {}".format(len(rows)))
    lines.append("\n## Detected columns\n")
    if cols:
        lines.append("| role | source column |")
        lines.append("| --- | --- |")
        for role, col in cols.items():
            lines.append("| {} | {} |".format(role, col))
    else:
        lines.append("_None detected. Pass explicit column names or rename headers._")
    lines.append("\n## Cells rewritten\n")
    for k, v in sorted(changed.items()):
        lines.append("- {}: {}".format(k, v))
    lines.append("\n## Flags (rows needing review)\n")
    if flag_counter:
        lines.append("| flag | rows |")
        lines.append("| --- | --- |")
        for f, n in flag_counter.most_common():
            lines.append("| {} | {} |".format(f, n))
    else:
        lines.append("_No flags raised._")
    report = "\n".join(lines) + "\n"

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(report)
    sys.stderr.write(report)
    print("Wrote {} rows to {}".format(len(rows), args.outfile))


if __name__ == "__main__":
    main()
