#!/usr/bin/env python3
"""Merge per-window sender scans (w*.json) into one senders.json, sorted by volume.

Usage: python3 merge_scan.py <scan_dir> <out.json>
"""
import glob
import json
import os
import sys

scan_dir, out_path = sys.argv[1], sys.argv[2]
merged, scanned = {}, 0
for path in sorted(glob.glob(os.path.join(scan_dir, "w[0-9].json"))):
    data = json.load(open(path))
    scanned += data.get("threads_scanned", 0)
    for s in data["senders"]:
        email = s["email"].strip().lower()
        m = merged.setdefault(email, {"email": email, "count": 0, "unread": 0,
                                      "latest": "", "subject": "", "msg_id": ""})
        m["count"] += s.get("count", 0)
        m["unread"] += s.get("unread", 0)
        if s.get("latest", "") > m["latest"]:
            m.update(latest=s["latest"], subject=s.get("subject", ""), msg_id=s.get("msg_id", ""))

senders = sorted(merged.values(), key=lambda s: (-s["count"], s["email"]))
json.dump({"threads_scanned": scanned, "senders": senders}, open(out_path, "w"), indent=1)
print(f"{scanned} threads, {len(senders)} senders -> {out_path}")
