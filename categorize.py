#!/usr/bin/env python3
"""Tag each sender in senders.json with a category for the picker page; writes senders_tagged.json.

Categories: keep, jobs, social, money, shop, travel, learn, news, tech (the fallback).
Rules are keyword-based on the sender address; first match wins, so "keep" (account and
security mail) is checked first. Add your own addresses to config/keep_senders.json to
force them into the keep group.

Usage: python3 categorize.py [senders.json] [senders_tagged.json]
"""
import json
import os
import re
import sys
from collections import Counter

src = sys.argv[1] if len(sys.argv) > 1 else "senders.json"
dst = sys.argv[2] if len(sys.argv) > 2 else "senders_tagged.json"
here = os.path.dirname(os.path.abspath(__file__))
keep_path = os.path.join(here, "config", "keep_senders.json")
always_keep = set(json.load(open(keep_path))) if os.path.exists(keep_path) else set()

RULES = [
    ("keep", r"accounts?@|account-security|security@|no-?reply@accounts\.google|statement|alerts?@|otp|transaction|"
             r"payments?-noreply|orders?@|shipment|booking|itinerary|login|signin"),
    ("jobs", r"job|career|hiring|recruit|naukri|indeed|glassdoor|internshala|unstop|foundit|cutshort|flexjobs"),
    ("social", r"linkedin|facebookmail|instagram|twitter|quora|pinterest|reddit|chess\.com|discord"),
    ("money", r"bank|card|loan|credit|invest|mutual|broker|trade|crypto|wallet|insurance|finance|fin\b|pay"),
    ("shop", r"amazon|aliexpress|temu|flipkart|myntra|shop|store|deals|sale|fashion|zomato|swiggy|food"),
    ("travel", r"travel|trip|flight|air|hotel|booking|rail|bus|rent|room|housing|stay|events?|tickets?"),
    ("learn", r"course|learn|academy|edu|school|university|admission|udemy|coursera|upgrad|simplilearn|scaler"),
    ("news", r"news|newsletter|digest|beehiiv|substack|convertkit|editor|weekly|daily"),
]

d = json.load(open(src))
for s in d["senders"]:
    email = s["email"]
    s["cat"] = "keep" if email in always_keep else next((c for c, pat in RULES if re.search(pat, email, re.I)), "tech")
    # Account/security alerts: don't carry subject lines onto the page.
    if s["cat"] == "keep":
        s["subject"] = ""
json.dump(d, open(dst, "w"), indent=1)

count, volume = Counter(), Counter()
for s in d["senders"]:
    count[s["cat"]] += 1
    volume[s["cat"]] += s["count"]
for k in count:
    print(f"{k:8} {count[k]:4} senders {volume[k]:5} emails")
