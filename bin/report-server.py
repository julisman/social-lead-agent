#!/usr/bin/env python3
"""Local-only dashboard (/) and viewer for reports/*.md (/reports).

No third-party dependencies (stdlib only). Binds to 127.0.0.1 so the
customer names and phone numbers in reports/ never leave the machine.
Files are re-read and re-rendered on every request, so edits and new
daily reports show up without restarting the server.
"""
import html
import os
import re
import secrets
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, quote, unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dashboard  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(ROOT, "reports")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


# ---------------------------------------------------------------- markdown

def render_inline(text):
    text = html.escape(text, quote=False)
    codes = []

    def stash_code(m):
        codes.append(m.group(1))
        return "\x00CODE%d\x00" % (len(codes) - 1)

    text = re.sub(r"`([^`]+)`", stash_code, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    for i, c in enumerate(codes):
        text = text.replace("\x00CODE%d\x00" % i, "<code>%s</code>" % c)
    return text


def slugify(text):
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s_]+", "-", s)


def align_of(cell):
    left, right = cell.startswith(":"), cell.endswith(":")
    if left and right:
        return "center"
    if right:
        return "right"
    if left:
        return "left"
    return ""


def render_markdown(text, toc=None):
    lines = text.split("\n")
    out = []
    para = []
    i, n = 0, len(lines)

    def flush_para():
        if para:
            out.append("<p>%s</p>" % render_inline(" ".join(para)))
            para.clear()

    while i < n:
        line = lines[i]

        if line.strip().startswith("```"):
            flush_para()
            i += 1
            code = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(code)))
            continue

        if "|" in line and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
            flush_para()
            headers = [c.strip() for c in line.strip().strip("|").split("|")]
            aligns = [align_of(c.strip()) for c in lines[i + 1].strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join(
                '<th style="text-align:%s">%s</th>' % (a or "left", render_inline(h))
                for h, a in zip(headers, aligns + [""] * len(headers))
            )
            trs = []
            for r in rows:
                tds = "".join(
                    '<td style="text-align:%s">%s</td>' % (a or "left", render_inline(c))
                    for c, a in zip(r, aligns + [""] * len(r))
                )
                trs.append("<tr>%s</tr>" % tds)
            out.append(
                '<div class="table-wrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
                % (th, "".join(trs))
            )
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush_para()
            level = len(m.group(1))
            title = m.group(2).strip()
            slug = slugify(title)
            if toc is not None and level in (1, 2, 3):
                toc.append((level, title, slug))
            out.append('<h%d id="%s">%s</h%d>' % (level, slug, render_inline(title), level))
            i += 1
            continue

        if re.match(r"^-{3,}\s*$", line.strip()):
            flush_para()
            out.append("<hr>")
            i += 1
            continue

        if line.strip().startswith(">"):
            flush_para()
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>%s</blockquote>" % render_markdown("\n".join(quote)))
            continue

        if re.match(r"^\s*[-*]\s+", line) and not re.match(r"^[-*]{3,}\s*$", line.strip()):
            flush_para()
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(render_inline(re.sub(r"^\s*[-*]\s+", "", lines[i])))
                i += 1
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % it for it in items))
            continue

        if re.match(r"^\s*\d+\.\s+", line):
            flush_para()
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(render_inline(re.sub(r"^\s*\d+\.\s+", "", lines[i])))
                i += 1
            out.append("<ol>%s</ol>" % "".join("<li>%s</li>" % it for it in items))
            continue

        if not line.strip():
            flush_para()
            i += 1
            continue

        para.append(line.strip())
        i += 1

    flush_para()
    return "\n".join(out)


# -------------------------------------------------------------------- page

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<style>
:root {
  --bg: #faf9f7; --fg: #2b2a28; --muted: #6b6660; --border: #e4e0da;
  --card: #ffffff; --accent: #a8571e; --code-bg: #f1efe9;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #1b1a18; --fg: #e8e4dd; --muted: #9b958c; --border: #37342e;
    --card: #232220; --accent: #e08a4a; --code-bg: #29271f; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.wrap { max-width: 900px; margin: 0 auto; padding: 2rem 1.25rem 5rem; }
a { color: var(--accent); }
header.top { display: flex; align-items: baseline; justify-content: space-between;
  gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
header.top .back { font-size: 0.9rem; color: var(--muted); text-decoration: none; }
h1, h2, h3, h4 { line-height: 1.25; }
h1 { font-size: 1.7rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
h2 { font-size: 1.3rem; margin-top: 2.2rem; }
h3 { font-size: 1.05rem; margin-top: 1.6rem; color: var(--accent); }
p { margin: 0.7rem 0; }
code { background: var(--code-bg); padding: 0.1em 0.35em; border-radius: 4px;
  font-size: 0.88em; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
pre { background: var(--code-bg); padding: 0.8rem 1rem; border-radius: 8px; overflow-x: auto; }
pre code { background: none; padding: 0; }
blockquote { margin: 1rem 0; padding: 0.4rem 1rem; border-left: 3px solid var(--accent);
  color: var(--muted); background: var(--card); border-radius: 0 6px 6px 0; }
hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
ul, ol { padding-left: 1.4rem; }
li { margin: 0.3rem 0; }
strong { color: var(--fg); }
.table-wrap { overflow-x: auto; margin: 1rem 0; }
table { border-collapse: collapse; width: 100%%; font-size: 0.95rem; }
th, td { border: 1px solid var(--border); padding: 0.45rem 0.7rem; }
th { background: var(--card); }
tbody tr:nth-child(odd) { background: color-mix(in srgb, var(--card) 60%%, transparent); }
.meta { color: var(--muted); font-size: 0.85rem; margin-bottom: 1.5rem; }
.toc { background: var(--card); border: 1px solid var(--border); border-radius: 10px;
  padding: 0.9rem 1.2rem; margin-bottom: 2rem; font-size: 0.92rem; }
.toc summary { cursor: pointer; font-weight: 600; color: var(--muted); }
.toc ul { list-style: none; padding-left: 0; margin: 0.6rem 0 0; }
.toc li.lvl2 { margin-left: 0; }
.toc li.lvl3 { margin-left: 1.1rem; font-size: 0.9em; }
.toc a { text-decoration: none; }
.index-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.8rem; }
.index-list a.card { display: block; background: var(--card); border: 1px solid var(--border);
  border-radius: 10px; padding: 1rem 1.25rem; text-decoration: none; color: var(--fg); }
.index-list a.card:hover { border-color: var(--accent); }
.index-list .card-title { font-weight: 600; font-size: 1.05rem; }
.index-list .card-sub { color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem; }
.badge { display: inline-block; font-size: 0.75rem; padding: 0.15em 0.6em; border-radius: 999px;
  background: var(--code-bg); color: var(--muted); margin-left: 0.5rem; }
.badge.open { background: color-mix(in srgb, var(--accent) 20%%, transparent); color: var(--accent); }
nav.nav { display: flex; gap: 1.2rem; font-size: 0.9rem; margin-bottom: 1.2rem; }
nav.nav a { color: var(--muted); text-decoration: none; }
nav.nav a:hover { color: var(--accent); }
footer.note { margin-top: 3rem; color: var(--muted); font-size: 0.8rem; }
</style>
</head>
<body>
<div class="wrap %(wrap)s">
<nav class="nav"><a href="/">Dashboard</a><a href="/reports">Reports</a></nav>
%(body)s
</div>
</body>
</html>
"""


def render_toc(toc):
    if not toc:
        return ""
    items = []
    for level, title, slug in toc:
        if level == 1:
            continue
        cls = "lvl2" if level == 2 else "lvl3"
        items.append('<li class="%s"><a href="#%s">%s</a></li>' % (cls, slug, html.escape(title)))
    if not items:
        return ""
    return '<details class="toc" open><summary>On this page</summary><ul>%s</ul></details>' % "".join(items)


def summarize_report(path, text):
    """Stat table right under the title, rendered as a compact preview line.

    Restricted to the top of the file so a later, unrelated table in a long
    running log (like escalations.md) never gets picked up instead.
    """
    head = "\n".join(text.split("\n")[:15])
    m = re.search(r"\|.*\|\n\|[\s:|-]+\|\n((?:\|.*\|\n?)+)", head)
    if not m:
        return None
    rows = [l for l in m.group(1).strip().split("\n") if l.strip()]
    pairs = []
    for r in rows:
        cells = [c.strip().replace("**", "") for c in r.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0]:
            pairs.append("%s: %s" % tuple(cells))
    return " · ".join(pairs[:4])


def first_paragraph(text):
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("|") or line.startswith("```"):
            continue
        line = re.sub(r"[*`_]", "", line)
        return line[:160] + ("…" if len(line) > 160 else "")
    return None


def index_page():
    if not os.path.isdir(REPORTS_DIR):
        body = "<h1>Reports</h1><p>No <code>reports/</code> directory yet.</p>"
        return PAGE % {"title": "Reports", "body": body, "wrap": ""}

    files = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".md")]
    dated = sorted([f for f in files if DATE_RE.match(f)], reverse=True)
    other = sorted([f for f in files if not DATE_RE.match(f)])

    cards = []
    for f in dated + other:
        full = os.path.join(REPORTS_DIR, f)
        try:
            text = open(full, encoding="utf-8").read()
        except OSError:
            continue
        mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M")
        title_m = re.search(r"^#\s+(.+)$", text, re.M)
        title = title_m.group(1).strip() if title_m else f
        sub = summarize_report(full, text) or first_paragraph(text)
        extra_badge = ""
        if f == "escalations.md" or "escalation" in f.lower():
            total = len(re.findall(r"^## ", text, re.M))
            open_n = len(re.findall(r"Status:\s*\*\*OPEN", text))
            extra_badge = '<span class="badge open">%d open / %d</span>' % (open_n, total)
        sub_html = html.escape(sub) if sub else "updated %s" % mtime
        cards.append(
            '<a class="card" href="/r/%s"><div class="card-title">%s%s</div>'
            '<div class="card-sub">%s &middot; updated %s</div></a>'
            % (f, html.escape(title), extra_badge, sub_html, mtime)
        )

    if not cards:
        cards_html = "<p>No reports found in <code>reports/</code> yet.</p>"
    else:
        cards_html = '<ul class="index-list">%s</ul>' % "".join("<li>%s</li>" % c for c in cards)

    body = (
        "<h1>Reports</h1>"
        '<p class="meta">Served from <code>reports/</code> — local only, never leaves this machine.</p>'
        + cards_html
        + '<footer class="note">Local viewer &middot; auto-refreshes on every request, no restart needed.</footer>'
    )
    return PAGE % {"title": "Reports", "body": body, "wrap": ""}


def report_page(name):
    if not DATE_RE.match(name) and not re.match(r"^[\w.-]+\.md$", name):
        return None
    full = os.path.join(REPORTS_DIR, name)
    full = os.path.abspath(full)
    if not full.startswith(os.path.abspath(REPORTS_DIR) + os.sep) or not os.path.isfile(full):
        return None
    text = open(full, encoding="utf-8").read()
    toc = []
    content = render_markdown(text, toc=toc)
    mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M")
    title_m = re.search(r"^#\s+(.+)$", text, re.M)
    title = title_m.group(1).strip() if title_m else name
    body = (
        '<header class="top"><a class="back" href="/reports">&larr; all reports</a>'
        '<span class="meta">%s &middot; updated %s</span></header>'
        % (html.escape(name), mtime)
    ) + render_toc(toc) + content
    return PAGE % {"title": title, "body": body, "wrap": ""}


# --------------------------------------------------------------- server

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        url = urlparse(self.path)
        path = unquote(url.path)
        if path == "/":
            q = parse_qs(url.query)
            body = dashboard.render(
                dashboard.snapshot(), TOKEN,
                msg=(q.get("msg") or [None])[0], ok=(q.get("ok") or ["1"])[0] == "1",
                render_markdown=render_markdown,
            )
            self._send(PAGE % {"title": "Social agent", "body": body, "wrap": "wide"})
        elif path == "/due":
            self._send(PAGE % {"title": "Due now", "body": dashboard.render_due(dashboard.due_preview()), "wrap": "wide"})
        elif path == "/reports":
            self._send(index_page())
        elif path.startswith("/r/"):
            page = report_page(path[len("/r/"):])
            if page is None:
                self._send("<h1>Not found</h1>", status=404)
            else:
                self._send(page)
        else:
            self._send("<h1>Not found</h1>", status=404)

    def do_POST(self):
        # Any web page you visit can POST to 127.0.0.1. The Host check stops
        # DNS-rebinding, the per-start token stops cross-site form posts.
        if self.headers.get("Host") not in ALLOWED_HOSTS:
            return self._send("<h1>Forbidden</h1>", status=403)
        length = min(int(self.headers.get("Content-Length") or 0), 64 * 1024)
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode("utf-8", "replace")).items()}
        if not secrets.compare_digest(form.get("token", ""), TOKEN):
            return self._send("<h1>Stale page</h1><p>The server restarted. <a href=\"/\">Reload the dashboard</a>.</p>", status=403)

        cfg = dashboard.load_config()
        stamp = dashboard.now_in(cfg).strftime("%Y-%m-%d %H:%M ") + dashboard.zone(cfg)[1]
        action = unquote(urlparse(self.path).path)[len("/action/"):]
        if action == "pause":
            ok, msg = dashboard.set_paused(form.get("reason"), stamp)
        elif action == "resume":
            ok, msg = dashboard.clear_paused()
        elif action == "park":
            ok, msg = dashboard.park_account(cfg, form.get("brand"), form.get("platform"),
                                             form.get("hours"), form.get("reason"))
        elif action == "resolve":
            ok, msg = dashboard.resolve_escalation(form.get("heading", ""), form.get("note"), stamp)
        else:
            return self._send("<h1>Not found</h1>", status=404)

        self.send_response(303)
        self.send_header("Location", "/?ok=%d&msg=%s" % (1 if ok else 0, quote(msg[:300])))
        self.end_headers()

    def _send(self, html_body, status=200):
        data = html_body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


TOKEN = secrets.token_urlsafe(24)
ALLOWED_HOSTS = set()


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("REPORT_SERVER_PORT", "8787"))
    ALLOWED_HOSTS.update({"127.0.0.1:%d" % port, "localhost:%d" % port})
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = "http://127.0.0.1:%d/" % port
    print("Dashboard at %s  (reports at %sreports — local only, Ctrl+C to stop)" % (url, url))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
