#!/usr/bin/env python3
"""Build a Gmail filter file that sends mail from junk senders straight to Trash.

Unsubscribing depends on the sender honouring it; a filter doesn't. Import the output in
Gmail: Settings -> See all settings -> Filters and Blocked Addresses -> Import filters.

Blocking rules:
  - A whole domain is blocked only if it's listed in config/marketing_only_domains.json
    (domains that send nothing but newsletters/marketing) and no kept sender uses it.
  - Everything else is blocked by exact address, so e.g. a shop's promo address is filtered
    while its order-confirmation address still reaches you.
  - Addresses on the keep list are never included.
Criteria are split into several filters because Gmail caps each filter at ~1500 characters.

Usage: python3 build_filters.py <junk.json> <keep.json> [gmail_junk_filters.xml]
  junk.json / keep.json: JSON lists of sender addresses.
"""
import json
import os
import re
import sys
from xml.sax.saxutils import quoteattr

junk = set(json.load(open(sys.argv[1])))
keep = set(json.load(open(sys.argv[2])))
out = sys.argv[3] if len(sys.argv) > 3 else "gmail_junk_filters.xml"
here = os.path.dirname(os.path.abspath(__file__))
mo_path = os.path.join(here, "config", "marketing_only_domains.json")
marketing_only = set(json.load(open(mo_path))) if os.path.exists(mo_path) else set()

TWO_PART = re.compile(r"\.(co|com|org|gov|ac|bank|net|edu)\.[a-z]{2}$")


def root(email):
    host = email.split("@")[1]
    parts = host.split(".")
    return ".".join(parts[-3:]) if TWO_PART.search(host) else ".".join(parts[-2:])


junk -= keep
keep_roots = {root(e) for e in keep}
domains, addresses = set(), []
for e in sorted(junk):
    r = root(e)
    if r in marketing_only and r not in keep_roots:
        domains.add(r)
    else:
        addresses.append(e)
terms = sorted(domains) + addresses

chunks, cur = [], []
for t in terms:
    if cur and len(" OR ".join(cur + [t])) > 1400:
        chunks.append(cur)
        cur = []
    cur.append(t)
if cur:
    chunks.append(cur)

entries = "".join(
    "<entry><category term='filter'></category><title>Mail Filter</title><content></content>"
    f"<apps:property name='from' value={quoteattr(' OR '.join(c))}/>"
    "<apps:property name='shouldTrash' value='true'/>"
    "<apps:property name='sizeOperator' value='s_sl'/><apps:property name='sizeUnit' value='s_smb'/></entry>\n"
    for c in chunks)
open(out, "w").write("<?xml version='1.0' encoding='UTF-8'?>\n<feed xmlns='http://www.w3.org/2005/Atom' "
                     "xmlns:apps='http://schemas.google.com/apps/2006'><title>Mail Filters</title>\n" + entries + "</feed>\n")

caught = [k for k in keep if k in addresses or any(k.endswith("@" + d) or k.endswith("." + d) for d in domains)]
print(f"{len(junk)} junk senders -> {len(domains)} domains + {len(addresses)} addresses -> {len(chunks)} filters -> {out}")
if caught:
    sys.exit(f"ERROR: kept senders would be filtered: {caught}")
