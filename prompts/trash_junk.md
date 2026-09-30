You are cleaning junk mail out of the user's Gmail (<YOUR_EMAIL>). The user explicitly asked to delete all mail from these marketing senders. You move threads to Trash (recoverable for 30 days). Never permanently delete, never send, never touch anything outside the query.

Setup: ToolSearch "select:mcp__claude_ai_Gmail__search_threads,mcp__claude_ai_Gmail__trash_thread".

Input: GROUP_FILES — JSON files each with {"group", "query", "senders"}. Process them one after another.

For each group, loop:
1. search_threads(query = <group query> + " -is:starred -has:userlabels", pageSize = 50, view = THREAD_VIEW_METADATA_ONLY). If a previous page had nothing to trash, pass its nextPageToken instead of restarting at page 1.
2. For each returned thread, SKIP it (never trash) if ANY message in it has sender <YOUR_EMAIL> or <YOUR_EMAIL_WITHOUT_DOTS> (the user replied), or any labelId is STARRED or starts with "Label_". Remember skipped ids so you don't count them twice.
3. Trash every other thread with trash_thread — issue the calls IN PARALLEL in a single message (all of that page's ids at once). If calls fail with rate-limit/quota errors, retry those ids once in smaller parallel chunks of ~15.
4. Repeat from step 1 (page 1 again, since trashed threads drop out) until the search returns no threads, or only skipped threads and no nextPageToken.

Budget: stop after you have trashed about 300 threads in total in this run (finish the current page first), even if groups remain.

After each group (and when you stop), append one JSON line to LOG_FILE with Bash:
{"group": N, "trashed": X, "skipped": Y, "finished": true|false}
("finished": false if you stopped because of the budget.)

Final reply, short: per group trashed / skipped / finished, and which groups (if any) are unfinished.

Honesty rule: only count a thread as trashed if you actually called trash_thread on it and it returned without error. Never "summarize" remaining work as done. If you're running low on room, stop and report the true count.

Resuming note: earlier runs already trashed part of each group; just run the loop — page 1 of the query shows what's left. Load tools via ToolSearch and call them directly yourself (no sub-agents). The Gmail connector is authenticated. "finished" = the query returned no more threads, not that you hit the budget.
