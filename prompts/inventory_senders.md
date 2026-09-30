You are building a read-only inventory of who sends mail to the user's Gmail (<YOUR_EMAIL>), so it can be classified into important vs not. READ-ONLY: do not trash, label, send or modify anything.

Setup: ToolSearch "select:mcp__claude_ai_Gmail__search_threads".

Query: WINDOW  plus the exclusions in <WORK_DIR>/inv/exclude.txt (append its contents after a space; if Gmail rejects the query as too long/invalid, retry with just WINDOW).
Call search_threads(query, pageSize=50, view=THREAD_VIEW_METADATA_ONLY) and follow nextPageToken until none (max 80 pages). Note: another process is trashing junk at the same time, so some threads may vanish between pages; that's fine.

After EVERY page, append the page's threads to a JSONL file OUT_PREFIX_raw.jsonl via Bash (one line per thread: {"id", "senders": [all message senders, lowercased], "labels": [union of labelIds], "date": first message date}). Keep it compact; do this with a small python3 or heredoc so you don't retype data by hand more than once.

When done, run a python3 script that aggregates OUT_PREFIX_raw.jsonl by the thread's FIRST non-user sender (user = <YOUR_EMAIL> / <YOUR_EMAIL_WITHOUT_DOTS>; if all messages are from the user, use "__me__"), and writes OUT_PREFIX.json:
{"window": "...", "threads": N, "senders": [{"email", "count", "replied": <threads where a message is from the user>, "starred": n, "userlabels": n, "cats": {"CATEGORY_PROMOTIONS": n, ...}, "latest": date, "sample_id": thread id}]} sorted by count desc.

Final reply: pages, threads, distinct senders, file path. Short.
