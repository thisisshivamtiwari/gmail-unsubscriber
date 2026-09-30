You are aggregating newsletter/marketing senders from the user's Gmail (<YOUR_EMAIL>) so they can decide what to unsubscribe from. Read-only task: do NOT modify, label, trash, or send anything.

Load the Gmail search tool with ToolSearch query "select:mcp__claude_ai_Gmail__search_threads".

Call mcp__claude_ai_Gmail__search_threads with:
- query: `unsubscribe WINDOW` (e.g. `unsubscribe after:2026/09/14`)
- pageSize: 50
- view: THREAD_VIEW_MINIMAL (so you get subject)
Keep following nextPageToken until there is no nextPageToken (or you hit 40 pages). Do not stop early.

For each thread, take the FIRST message's `sender` (lowercase), `date`, `subject`, `id` (message id), and whether labelIds contains UNREAD.
Aggregate by sender: count, unread count, latest date, latest subject, latest message id.

Write JSON to OUT_FILE:
{"window": "...", "threads_scanned": N, "pages": P, "senders": [{"email", "count", "unread", "latest", "subject", "msg_id"}]}
Accumulate page results in files and aggregate with a small python3 script rather than tallying by hand.
Final reply: pages, threads scanned, distinct senders, file path.
