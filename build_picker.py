#!/usr/bin/env python3
"""Build picker.html (the "which senders should go?" page) from senders_tagged.json.

The page groups senders by category, shows volume and a "never opened" tag, and lets you tick
the ones to drop. Picks can be copied as a list to paste back to Claude.

Usage: python3 build_picker.py [senders_tagged.json] [picker.html] ["Jul 31 – Sep 29, 2026"]
"""
import json
import os
import sys

src = sys.argv[1] if len(sys.argv) > 1 else "senders_tagged.json"
dst = sys.argv[2] if len(sys.argv) > 2 else "picker.html"
window = sys.argv[3] if len(sys.argv) > 3 else ""

d = json.load(open(src))
slim = {"threads_scanned": d["threads_scanned"], "window": window,
        "senders": [{k: s[k] for k in ("email", "count", "unread", "subject", "cat")} for s in d["senders"]]}
js = json.dumps(slim, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
template = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "picker_template.html")).read()
open(dst, "w").write(template.replace("__DATA__", js))
print(f"{len(slim['senders'])} senders -> {dst}")
