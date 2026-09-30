You are collecting unsubscribe links from marketing emails in the user's Gmail (<YOUR_EMAIL>). The user has asked to unsubscribe from these senders. READ-ONLY: do NOT click/fetch any link, do NOT send, label, trash or modify anything. Your only output is a JSON file.

Setup: load the tool with ToolSearch query "select:mcp__claude_ai_Gmail__get_message".

Input: BATCH_FILE — a JSON list of {email, msg_id, count}.

For EACH entry:
1. Call mcp__claude_ai_Gmail__get_message with messageId = msg_id and messageFormat = FULL_CONTENT.
2. In html_body (or plaintext_body if there is no HTML), find the link the sender provides to stop these emails. In priority order:
   a. an <a href> whose anchor text or URL contains "unsubscribe" / "unsub" / "opt out" / "opt-out" / "stop receiving"
   b. otherwise a link for "email preferences" / "manage preferences" / "notification settings" / "subscription center"
   Copy the href EXACTLY, character for character, then decode HTML entities (&amp; -> &, &#61; -> =, etc.). If the body looks quoted-printable (soft line breaks "=" at line ends, "=3D"), undo that too. Never shorten, guess or rebuild a URL; if you cannot copy it exactly, leave it empty and say why in note.
   c. also record any mailto: link whose address or subject mentions unsubscribe.
3. If the message can't be fetched, retry once, then record the error in note.

Write results to OUT_FILE as JSON: a list of
{"email": "...", "url": "<primary unsubscribe https link or empty>", "kind": "unsubscribe" | "preferences" | "none", "mailto": "<mailto link or empty>", "note": "<short note, e.g. link needs login, not found, fetch error>"}
Write the file incrementally (e.g. rewrite it every ~5 senders) so partial progress survives. To avoid typos in long URLs, write the JSON with the Write tool in one go per update rather than hand-editing.

Final reply: counts of url found / preferences only / none / errors, and the file path. Keep it short. Never include email content beyond what's needed.
