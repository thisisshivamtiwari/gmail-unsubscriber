# Gmail Unsubscriber

Tools for cleaning a Gmail inbox that's drowning in newsletters, promotions and job alerts:

1. **Find** every sender that emails you with an unsubscribe link, grouped by type and volume.
2. **Pick** the ones to drop on a checklist page.
3. **Unsubscribe** automatically where the sender allows it, with a list of the rest to click by hand.
4. **Classify** the whole mailbox into *keep* vs *delete* and bulk-move the junk to Trash.
5. **Block** junk for good with Gmail filters that trash it on arrival, even from senders that ignore unsubscribes.

The Gmail steps run through [Claude](https://claude.com) with the Gmail connector. The Python scripts are plain standard-library tools that work on the JSON those steps produce.

## What's here

| File | What it does |
|---|---|
| `merge_scan.py` | Merges per-date-window sender scans into one `senders.json`, sorted by volume. |
| `categorize.py` | Tags each sender (jobs, money, shopping, travel, learning, newsletters, social, tech, keep) for the picker. |
| `build_picker.py` + `picker_template.html` | Builds the checklist page where you tick senders to drop. |
| `unsubscribe.py` | Unsubscribes from a list of senders. It uses RFC 8058 one-click where offered, otherwise opens the link and submits the confirm form, and reports anything that needs a manual click. |
| `classify.py` | Classifies every sender in a mailbox inventory as keep or delete (rules below). |
| `build_filters.py` | Writes a Gmail filter file that trashes mail from junk senders on arrival. |
| `prompts/` | Instructions for the Claude agents that scan the mailbox, collect unsubscribe links, take inventory and trash junk. |
| `config/*.example.json` | Templates for your personal keep list, hand decisions and marketing-only domains. |

## How classification decides

Kept:
- anything you replied to, starred or labelled
- real people (personal email domains), schools and government
- account and security mail, bank statements and alerts, one-time codes, investment and shareholder notices
- orders, deliveries, bookings and receipts

Deleted:
- newsletters, promotions and marketing
- social notifications and job-alert digests
- anything on your own junk list

When the rules can't decide, the sender is **kept**. Your hand decisions in `config/overrides.json` always win.

## Typical flow

```bash
# 1. Scan: run prompts/scan_senders.md in Claude per date window -> scan/w1.json, w2.json, ...
python3 merge_scan.py scan senders.json
python3 categorize.py senders.json senders_tagged.json
python3 build_picker.py senders_tagged.json picker.html "Jul 31 – Sep 29"

# 2. Unsubscribe: collect links with prompts/collect_unsubscribe_links.md -> targets.json
python3 unsubscribe.py targets.json results.json

# 3. Whole-mailbox cleanup: inventory with prompts/inventory_senders.md -> inv/w_*.json
python3 classify.py inv known_junk.json classified.json
#    then trash the "delete" senders with prompts/trash_junk.md

# 4. Block for good
python3 build_filters.py junk.json keep.json gmail_junk_filters.xml
#    Gmail -> Settings -> See all settings -> Filters and Blocked Addresses -> Import filters
```

## Privacy

Everything these tools produce contains your mailbox data: sender lists, subject lines, and personal unsubscribe links with tokens that let anyone who has them change your subscriptions. `.gitignore` excludes all generated JSON, HTML and XML, and your `config/*.json`. Only the `*.example.json` templates are tracked. Keep it that way.

Deleting moves mail to **Trash**, which Gmail keeps for 30 days, so mistakes can be undone.

## Notes

- The Gmail connector deletes one conversation per call, so a large mailbox is done in batches by many agents working in parallel.
- Unsubscribing only works when the sender honours it. Some take up to 10 days, and some (for example multi-newsletter publishers) need one unsubscribe per list. The filter step covers those.
