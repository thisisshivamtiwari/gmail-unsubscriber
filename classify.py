#!/usr/bin/env python3
"""Classify every sender in a mailbox inventory as keep / delete.

Keep:   anything you replied to, starred or labelled; real people; schools and government;
        security/account mail, banking/tax/investment records, OTPs, orders, bookings, receipts.
Delete: marketing, newsletters, promotions, social notifications, job-alert digests, product news,
        plus every sender listed in the "known junk" file (e.g. the ones you chose to unsubscribe from).
Senders the rules can't place are kept, to be safe.

Optional personal config (not committed — see config/*.example.json):
  config/keep_senders.json  list of addresses to always keep
  config/overrides.json     {"address": "keep" | "delete"} hand decisions; these win over every rule

Inventory format: <inv_dir>/w_*.json, each {"senders": [{"email", "count", "replied", "starred",
"userlabels", "cats": {"CATEGORY_PROMOTIONS": n, ...}, "latest", "sample_id"}]}

Usage: python3 classify.py <inv_dir> <known_junk.json> <out.json>
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict


def load(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


inv_dir, junk_path, out_path = sys.argv[1:4]
here = os.path.dirname(os.path.abspath(__file__))
known_junk = set(load(junk_path, []))
kept_before = set(load(os.path.join(here, "config", "keep_senders.json"), []))
overrides = load(os.path.join(here, "config", "overrides.json"), {})

# Merge the per-window inventories.
agg = defaultdict(lambda: {"count": 0, "replied": 0, "starred": 0, "userlabels": 0, "cats": defaultdict(int), "latest": ""})
for path in glob.glob(os.path.join(inv_dir, "w_*.json")):
    for s in json.load(open(path))["senders"]:
        a = agg[s["email"].lower()]
        for k in ("count", "replied", "starred", "userlabels"):
            a[k] += s.get(k, 0)
        for c, n in (s.get("cats") or {}).items():
            a["cats"][c] += n
        if s.get("latest", "") > a["latest"]:
            a["latest"], a["sample_id"] = s["latest"], s.get("sample_id")

PERSONAL_DOMAINS = re.compile(r"@(gmail|googlemail|yahoo|ymail|outlook|hotmail|live|icloud|me|proton|protonmail|rediffmail|aol)\.")
EDU_GOV = re.compile(r"\.(edu|ac\.[a-z]{2}|edu\.[a-z]{2}|gov|gov\.[a-z]{2}|nic\.in)$")
TRANSACTIONAL = re.compile(
    r"statement|alert|otp|transaction|txn|security|accounts?@|verify|verification|"
    r"receipt|invoice|billing|bill|payment|order|shipment|shipping|delivery|booking|reservation|ticket|"
    r"itinerary|boarding|pnr|refund|mandate|evoting|contract ?note|investor|shareholder|registrar|"
    r"no-?reply@accounts\.google|appleid|id\.apple|password|signin|login|2fa|auth|recruiting@|"
    r"notifications@github|atlassian\.net|calendar-notification", re.I)
JOB_DIGEST = re.compile(r"jobalerts|job-?alerts|jobs@alerts|jobfeed", re.I)
MARKETING = re.compile(
    r"news|newsletter|marketing|offers?|promo|promotions?|deals?|digest|campaign|mailers?|emailers?|engage|"
    r"community|events?|webinar|hello@|hi@|info@|updates?@|team@|welcome@|inspiration|savings|rewards|"
    r"beehiiv|substack|convertkit|kit-mail|mailchimp|sendgrid|hubspot|klaviyo|marketo|braze|moengage|netcore|"
    r"jobs-noreply|careers|recruit|facebookmail|linkedin|quora|pinterest|twitter|instagram|medium\.com|reddit", re.I)

rows = []
for email, a in agg.items():
    if email == "__me__":
        continue
    promo = a["cats"].get("CATEGORY_PROMOTIONS", 0) + a["cats"].get("CATEGORY_SOCIAL", 0)
    share = promo / max(a["count"], 1)
    if email in overrides:
        verdict, why = overrides[email], "reviewed by hand"
    elif a["replied"] or a["starred"] or a["userlabels"]:
        verdict, why = "keep", "you replied, starred or labelled"
    elif email in kept_before:
        verdict, why = "keep", "on your keep list"
    elif email in known_junk:
        verdict, why = "delete", "on your junk list"
    elif PERSONAL_DOMAINS.search(email) or EDU_GOV.search(email.split("@")[-1]):
        verdict, why = "keep", "person, school or government"
    elif JOB_DIGEST.search(email):
        verdict, why = "delete", "job-alert digest"
    elif TRANSACTIONAL.search(email) and share < 0.5:
        verdict, why = "keep", "account, banking or order mail"
    elif MARKETING.search(email) or share >= 0.6:
        verdict, why = "delete", "marketing / newsletter / social"
    else:
        verdict, why = "keep", "unsure, kept to be safe"
    rows.append({"email": email, "count": a["count"], "promo_share": round(share, 2), "verdict": verdict,
                 "why": why, "latest": a["latest"], "sample_id": a.get("sample_id")})

rows.sort(key=lambda r: -r["count"])
json.dump(rows, open(out_path, "w"), indent=1)
tot = defaultdict(lambda: [0, 0])
for r in rows:
    tot[r["verdict"]][0] += 1
    tot[r["verdict"]][1] += r["count"]
for k, (n, c) in tot.items():
    print(f"{k:7} {n:5} senders {c:6} threads")
