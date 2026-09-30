#!/usr/bin/env python3
"""Unsubscribe from mailing lists.

Input: a JSON file with a list of entries. Each entry may carry either
  - a List-Unsubscribe header:  {"email", "list_unsubscribe", "list_unsubscribe_post"}
  - or the unsubscribe link from the email body:  {"email", "url", "kind", "mailto"}

For each sender, in order of preference:
  1. RFC 8058 one-click: POST "List-Unsubscribe=One-Click" to the header's https URL.
  2. Unsubscribe link: GET it. If the page shows a confirm form, submit that form once.
  3. mailto: reported back so an unsubscribe email can be sent from Gmail.
Links that only open a preferences page are reported for a manual click.

Statuses: done (page confirmed it), likely (link opened without error, no
confirmation text found), check (needs a manual click), send-email, failed.

Usage: python3 unsubscribe.py targets.json [results.json]
"""
import html
import html.parser
import http.cookiejar
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
TIMEOUT = 25
SUCCESS = re.compile(
    r"(successfully|you have been|you've been|you are now|you're now|have been)\s+(un-?subscribed|removed|opted out)"
    r"|un-?subscribed\s+successfully|unsubscription (is )?(successful|complete)|you will no longer receive"
    r"|you won't receive|no longer (be )?receiv|removed from (our|the|this|all) (mailing |email )?lists?|opt-?out (was )?successful"
    r"|unsubscribe(d)? (request )?(was |is |has been )?(successful|accepted|confirmed|complete)|request has been (successfully )?(accepted|processed)"
    r"|you('re| are) (now )?unsubscribed|successfully (opted out|removed|unsubscribed)|preferences (have been|were) (updated|saved)"
    r"|sorry to see you go|we('ve| have) removed|you('ve| have) (been )?unsubscribed|will be unsubscribed"
    r"|(we have )?received your request|unsubscribe center thank you",
    re.I,
)
UNSUB_WORD = re.compile(r"unsub|opt.?out|remove me|stop", re.I)


class FormParser(html.parser.HTMLParser):
    """Collect <form>s with their inputs, buttons and visible text."""

    def __init__(self):
        super().__init__()
        self.forms, self.cur, self.in_button = [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.cur = {"action": a.get("action", ""), "method": (a.get("method") or "get").lower(),
                        "fields": [], "text": "", "submits": []}
            self.forms.append(self.cur)
        elif self.cur is not None and tag in ("input", "button", "select", "textarea"):
            typ = (a.get("type") or ("submit" if tag == "button" else "text")).lower()
            name, value = a.get("name"), a.get("value", "")
            if typ in ("submit", "image"):
                self.cur["submits"].append([name, value, value])
                self.cur["text"] += " " + value
                if tag == "button":
                    self.in_button = self.cur["submits"][-1]
            elif typ in ("checkbox", "radio"):
                if "checked" in a and name:
                    self.cur["fields"].append((name, value or "on"))
            elif name:
                self.cur["fields"].append((name, value))

    def handle_endtag(self, tag):
        if tag == "button":
            self.in_button = None
        if tag == "form":
            self.cur = None

    def handle_data(self, data):
        if self.in_button is not None:
            self.in_button[2] += " " + data.strip()
        if self.cur is not None:
            self.cur["text"] += " " + data


def make_opener(verify=True):
    handlers = [urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())]
    if not verify:
        handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    return urllib.request.build_opener(*handlers)


def fetch(opener, url, data=None, content_type=None):
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "text/html,application/xhtml+xml,*/*;q=0.8")
    if content_type:
        req.add_header("Content-Type", content_type)
    with opener.open(req, timeout=TIMEOUT) as resp:
        return resp.status, resp.geturl(), resp.read(300_000).decode("utf-8", "replace")


def visible_text(page):
    page = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))


def try_link(url):
    """GET an unsubscribe link and, if needed, submit its confirm form once."""
    opener = make_opener()
    try:
        code, final, page = fetch(opener, url)
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        opener = make_opener(verify=False)  # sender's cert is misconfigured; link is still theirs
        code, final, page = fetch(opener, url)
    if SUCCESS.search(visible_text(page)):
        return "done", f"HTTP {code}, page confirmed"
    parser = FormParser()
    try:
        parser.feed(page)
    except Exception:
        pass
    forms = [f for f in parser.forms if UNSUB_WORD.search(f["text"] + " " + f["action"])]
    ALL = re.compile(r"(unsubscribe|opt.?out).{0,12}\ball\b|\ball\b.{0,12}(unsubscribe|opt.?out)", re.I)
    forms.sort(key=lambda f: not any(ALL.search(s[2]) for s in f["submits"]))
    if forms:
        f = forms[0]
        fields = list(f["fields"])
        sub = next((s for s in f["submits"] if ALL.search(s[2])), None) \
            or next((s for s in f["submits"] if UNSUB_WORD.search(s[2])), None) \
            or next((s for s in f["submits"] if s[0]), None)
        if sub and sub[0]:
            fields.append((sub[0], sub[1]))
        action = urllib.parse.urljoin(final, f["action"] or final)
        body = urllib.parse.urlencode(fields)
        if f["method"] == "post":
            code2, _, page2 = fetch(opener, action, body.encode(), "application/x-www-form-urlencoded")
        else:
            sep = "&" if "?" in action else "?"
            code2, _, page2 = fetch(opener, action + (sep + body if body else ""))
        if SUCCESS.search(visible_text(page2)):
            return "done", f"confirm form submitted, HTTP {code2}, page confirmed"
        if code2 == 204:
            return "likely", "confirm form accepted (HTTP 204, no page shown)"
        snippet = visible_text(page2).strip()[:160]
        return "check", f"submitted confirm form (HTTP {code2}), page says: {snippet!r}; open to verify: {url}"
    text = visible_text(page).lower()
    if "<script" in page.lower() and len(text) < 400:
        return "check", f"page needs a browser (JavaScript); open: {url}"
    if any(w in text for w in ("sign in", "log in", "login")) and "unsub" not in text:
        return "check", f"page asks you to sign in; open: {url}"
    if any(w in text for w in ("preferences", "confirm", "are you sure", "select")):
        return "check", f"page asks for a choice; open: {url}"
    return "likely", f"HTTP {code}, no confirm step found"


def parse_header(header):
    items = [i.strip() for i in re.findall(r"<([^>]+)>", header or "")]
    return [i for i in items if i.lower().startswith("http")], [i for i in items if i.lower().startswith("mailto:")]


def mailto_detail(link):
    m = urllib.parse.urlparse(link)
    q = urllib.parse.parse_qs(m.query)
    return json.dumps({"to": urllib.parse.unquote(m.path),
                       "subject": q.get("subject", ["unsubscribe"])[0],
                       "body": q.get("body", ["unsubscribe"])[0]})


def unsubscribe(entry):
    r = {"email": entry["email"], "method": None, "status": "failed", "detail": ""}
    header_https, header_mailto = parse_header(entry.get("list_unsubscribe", ""))
    one_click = "one-click" in (entry.get("list_unsubscribe_post") or "").lower()

    if one_click:
        for url in header_https:
            try:
                code, _, _ = fetch(make_opener(), url, b"List-Unsubscribe=One-Click",
                                   "application/x-www-form-urlencoded")
                if 200 <= code < 300:
                    r.update(method="one-click", status="done", detail=f"HTTP {code}")
                    return r
            except Exception as e:
                r["detail"] = f"one-click failed: {type(e).__name__}: {e}"

    url = re.sub(r"\s+", "", entry.get("url") or "")
    if entry.get("kind") == "preferences" and url:
        r.update(method="preferences page", status="check", detail=f"choose 'unsubscribe from all' here: {url}")
        return r
    links = ([url] if url.lower().startswith("http") else []) + header_https
    for link in links:
        try:
            status, detail = try_link(link)
            r.update(method="link", status=status, detail=detail)
            return r
        except urllib.error.HTTPError as e:
            r["detail"] = f"HTTP {e.code} from {urllib.parse.urlparse(link).netloc}; open: {link}"
            r["status"] = "check"
        except Exception as e:
            r["detail"] = f"{type(e).__name__}: {e}; open: {link}"
            r["status"] = "check"

    mailto = entry.get("mailto") or (header_mailto[0] if header_mailto else "")
    if r["status"] != "done" and mailto:
        r.update(method="mailto", status="send-email", detail=mailto_detail(mailto))
    elif not links and not mailto:
        r["detail"] = entry.get("note") or "no unsubscribe link found"
    return r


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    entries = json.load(open(sys.argv[1]))
    out_path = sys.argv[2] if len(sys.argv) > 2 else "results.json"
    results = []
    for e in entries:
        r = unsubscribe(e)
        results.append(r)
        print(f"[{r['status']:>10}] {r['email']:<48} {r['detail'][:100]}", flush=True)
    json.dump(results, open(out_path, "w"), indent=2)
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\nSummary:", counts, "->", out_path)


if __name__ == "__main__":
    main()
