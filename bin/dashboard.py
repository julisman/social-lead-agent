"""Dashboard page for bin/report-server.py — one screen over data/ and reports/.

Read-mostly. The only writes are the dashboard actions, and each goes through
the same door a human at the terminal would use:

  pause / resume       PAUSED in the project root — what guard.sh checks
  park an account      bin/cooldown.sh, so the park is logged like any other
  resolve escalation   flips one Status line in reports/escalations.md

Nothing here writes to data/*.jsonl directly. Those files stay append-only and
owned by the bin/ scripts.
"""
import html
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # python < 3.9
    ZoneInfo = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BIN = os.path.join(ROOT, "bin")
CONFIG = os.path.join(ROOT, "config.json")
PAUSED = os.path.join(ROOT, "PAUSED")
ESCALATIONS = os.path.join(ROOT, "reports", "escalations.md")

PLATFORMS = ("threads", "tiktok", "instagram")
CHART_KINDS = (("public_reply", "Public replies"), ("dm_reply", "DM replies"), ("comment_reply", "Comment replies"))

# Two clicks on the same button must not interleave a read-modify-write.
_write_lock = threading.Lock()


# ------------------------------------------------------------------ loading

def load_config():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def zone(cfg):
    name = cfg.get("timezone") or "UTC"
    if ZoneInfo is None:
        return None, name
    try:
        return ZoneInfo(name), name
    except Exception:
        return ZoneInfo("UTC"), "UTC"


def now_in(cfg):
    tz, _ = zone(cfg)
    return datetime.now(tz) if tz else datetime.now()


def read_jsonl(name):
    path = os.path.join(DATA, name)
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def norm_handle(h):
    # Must match norm_handle in common.sh, or the dedupe lookup misses.
    return (h or "").lstrip("@").lower()


def run_bin(args, timeout=20):
    try:
        p = subprocess.run(
            [os.path.join(BIN, args[0])] + list(args[1:]),
            cwd=ROOT, capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 99, str(e)


def cooldowns():
    out = {}
    d = os.path.join(DATA, "cooldown")
    if not os.path.isdir(d):
        return out
    now = time.time()
    for name in os.listdir(d):
        try:
            with open(os.path.join(d, name), encoding="utf-8") as f:
                lines = f.read().split("\n")
            until = int(lines[0])
        except (OSError, ValueError, IndexError):
            continue
        if until > now:
            out[name] = (until, lines[1] if len(lines) > 1 else "")
    return out


# ------------------------------------------------------------- escalations

STATUS_RE = re.compile(r"^Status:")
OPEN_RE = re.compile(r"^Status:\s*(\*\*)?OPEN\b")


def _sections(lines):
    """(heading, start, end) for every '## ' heading outside a code fence.

    The fence check matters: the file's own format example contains a '## '
    line inside ``` and must never be counted as an escalation.
    """
    heads = []
    fence = False
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if not fence and line.startswith("## "):
            heads.append((line[3:].strip(), i))
    out = []
    for n, (h, start) in enumerate(heads):
        end = heads[n + 1][1] if n + 1 < len(heads) else len(lines)
        out.append((h, start, end))
    return out


def parse_escalations():
    try:
        with open(ESCALATIONS, encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError:
        return []
    items = []
    for heading, start, end in _sections(lines):
        body = lines[start + 1:end]
        status = [l for l in body if STATUS_RE.match(l)]
        last = status[-1] if status else ""
        state = "open" if OPEN_RE.match(last) else ("none" if not last else "closed")
        text = "\n".join(body).strip()
        text = re.sub(r"\n-{3,}\s*$", "", text).strip()
        items.append({"heading": heading, "state": state, "body": text})
    return items


def resolve_escalation(heading, note, stamp):
    note = re.sub(r"\s+", " ", note or "").strip()[:300]
    with _write_lock:
        for _ in range(3):
            try:
                with open(ESCALATIONS, encoding="utf-8") as f:
                    original = f.read()
            except OSError as e:
                return False, "cannot read escalations.md: %s" % e
            lines = original.split("\n")
            match = [s for s in _sections(lines) if s[0] == heading]
            if len(match) != 1:
                return False, "escalation not found (or heading not unique) — nothing changed"
            _, start, end = match[0]

            resolved = "**RESOLVED** %s (dashboard)" % stamp
            status_idx = [i for i in range(start + 1, end) if STATUS_RE.match(lines[i])]
            if status_idx:
                j = status_idx[-1]
                if not OPEN_RE.match(lines[j]):
                    return False, "that escalation is not open — nothing changed"
                # Swap only the OPEN token, so any explanation after it survives.
                lines[j] = re.sub(r"(\*\*)?OPEN(\*\*)?", resolved, lines[j], count=1)
                if note:
                    lines.insert(j + 1, "Resolution: %s" % note)
            else:
                k = end
                while k > start + 1 and lines[k - 1].strip() in ("", "---"):
                    k -= 1
                add = ["", "Status: %s" % resolved] + (["Resolution: %s" % note] if note else [])
                lines[k:k] = add

            # The agent may be appending a new escalation mid-run. Re-read just
            # before replacing; if the file moved under us, start over.
            with open(ESCALATIONS, encoding="utf-8") as f:
                if f.read() != original:
                    continue
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ESCALATIONS), prefix=".esc-")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            os.replace(tmp, ESCALATIONS)
            return True, "Marked resolved: %s" % heading[:80]
        return False, "escalations.md kept changing — try again in a moment"


# ----------------------------------------------------------------- actions

def set_paused(reason, stamp):
    reason = re.sub(r"\s+", " ", reason or "").strip()[:300]
    with _write_lock:
        with open(PAUSED, "w", encoding="utf-8") as f:
            f.write("paused from dashboard %s%s\n" % (stamp, (" — " + reason) if reason else ""))
    return True, "Paused. Every skill will stop at its guard."


def clear_paused():
    with _write_lock:
        if os.path.exists(PAUSED):
            os.remove(PAUSED)
            return True, "Resumed. The next scheduled run will proceed."
    return True, "Was not paused."


def park_account(cfg, brand, platform, hours, reason):
    if brand not in cfg.get("brands", {}) or platform not in cfg["brands"][brand].get("accounts", {}):
        return False, "unknown brand/platform"
    try:
        hours = int(hours)
    except (TypeError, ValueError):
        return False, "hours must be a whole number"
    if not 1 <= hours <= 168:
        return False, "hours must be between 1 and 168"
    reason = re.sub(r"\s+", " ", reason or "").strip()[:200] or "no reason given"
    code, out = run_bin(["cooldown.sh", brand, platform, str(hours), "manual park from dashboard: " + reason])
    return code == 0, out or "cooldown.sh exited %d" % code


def due_preview():
    code, out = run_bin(["due.sh"], timeout=30)
    return out or ("(nothing due)" if code == 0 else "due.sh exited %d" % code)


# ---------------------------------------------------------------- snapshot

def snapshot():
    cfg = load_config()
    now = now_in(cfg)
    today = now.strftime("%Y-%m-%d")
    now_epoch = time.time()

    actions = read_jsonl("actions.jsonl")
    leads = read_jsonl("leads.jsonl")
    seen = read_jsonl("seen.jsonl")
    watch = read_jsonl("watch.jsonl")

    # A lead marked "collected" may already have been answered — engage records
    # that in seen.jsonl, not by rewriting the lead. Waiting = what engage would
    # actually still pick up.
    ttl = int(cfg.get("defaults", {}).get("author_dedupe_days", 30))
    cutoff = now_epoch - ttl * 86400
    seen_posts = {s.get("key") for s in seen if s.get("kind") == "post"}
    seen_authors = {}
    for s in seen:
        if s.get("kind") == "author":
            seen_authors[s.get("key")] = max(seen_authors.get(s.get("key"), 0), s.get("epoch", 0))

    waiting, handled, research, dupes = [], 0, 0, set()
    for l in leads:
        if l.get("status") == "research":
            research += 1
        if l.get("status") != "collected":
            continue
        p = l.get("platform", "")
        pk = "%s:%s" % (p, l.get("post_id") or l.get("post_url"))
        if pk in dupes:
            continue
        dupes.add(pk)
        ak = "%s:%s" % (p, norm_handle(l.get("author")))
        if pk in seen_posts or seen_authors.get(ak, 0) >= cutoff:
            handled += 1
        else:
            waiting.append(l)
    waiting.sort(key=lambda l: l.get("posted_at") or l.get("collected_at") or "", reverse=True)

    cds = cooldowns()
    accounts = []
    for brand, b in sorted(cfg.get("brands", {}).items()):
        for p in PLATFORMS:
            a = b.get("accounts", {}).get(p)
            if a is None:
                continue
            mine = [x for x in actions if x.get("brand") == brand and x.get("platform") == p]
            todays = [x for x in mine if (x.get("ts") or "").startswith(today)]
            runs = [x.get("ts", "") for x in mine if x.get("kind") == "run"]
            enabled = a.get("enabled") is True
            accounts.append({
                "brand": brand, "platform": p, "enabled": enabled,
                "left": run_bin(["budget.sh", brand, p])[1] if enabled else "–",
                "pub": sum(1 for x in todays if x.get("kind") == "public_reply"),
                "dm": sum(1 for x in todays if x.get("kind") == "dm_reply"),
                "com": sum(1 for x in todays if x.get("kind") == "comment_reply"),
                "esc": sum(1 for x in todays if (x.get("kind") or "").endswith("_escalate")),
                "last_run": max(runs) if runs else "",
                "cooldown": cds.get("%s-%s" % (brand, p)),
            })

    # Chart window: from the first logged action, capped at 90 days.
    days = 30
    epochs = [x.get("epoch") for x in actions if isinstance(x.get("epoch"), (int, float))]
    if epochs:
        days = max(14, min(90, int((now_epoch - min(epochs)) // 86400) + 1))
    series = []
    for i in range(days - 1, -1, -1):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        series.append([d] + [0] * len(CHART_KINDS))
    index = {row[0]: row for row in series}
    for x in actions:
        row = index.get((x.get("ts") or "")[:10])
        if row is None:
            continue
        for n, (kind, _) in enumerate(CHART_KINDS):
            if x.get("kind") == kind:
                row[n + 1] += 1

    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    watch_key = lambda w: w.get("recorded_at") or w.get("found_at") or ""
    watch_sorted = sorted(watch, key=watch_key, reverse=True)

    last_ts = max((x.get("ts", "") for x in actions), default="")
    last_epoch = max(epochs) if epochs else None

    paused = None
    if os.path.exists(PAUSED):
        try:
            paused = open(PAUSED, encoding="utf-8").read().strip() or "(no reason given)"
        except OSError:
            paused = "(unreadable)"

    return {
        "cfg": cfg, "now": now, "tzname": zone(cfg)[1], "today": today,
        "paused": paused,
        "accounts": accounts,
        "waiting": waiting, "handled": handled, "research": research,
        "escalations": parse_escalations(),
        "watch": watch_sorted, "watch_week": sum(1 for w in watch if watch_key(w)[:10] >= week_ago),
        "series": series,
        "recent": list(reversed(actions[-25:])),
        "last_ts": last_ts,
        "idle_days": (now_epoch - last_epoch) / 86400 if last_epoch else None,
        "today_total": sum(1 for x in actions if (x.get("ts") or "").startswith(today) and x.get("kind") != "run"),
    }


# ------------------------------------------------------------------ render

def e(s):
    return html.escape("" if s is None else str(s))


def safe_url(u):
    u = u or ""
    return e(u) if re.match(r"^https?://", u) else "#"


def short_ts(ts):
    return (ts or "")[:16].replace("T", " ")


def trunc(s, n):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def form(action, token, inner, cls="inline"):
    return ('<form method="post" action="/action/%s" class="%s">'
            '<input type="hidden" name="token" value="%s">%s</form>' % (action, cls, e(token), inner))


def bar_path(x, y, w, h, r):
    r = min(r, w / 2, h)
    return ("M%.1f,%.1f L%.1f,%.1f Q%.1f,%.1f %.1f,%.1f L%.1f,%.1f Q%.1f,%.1f %.1f,%.1f L%.1f,%.1f Z"
            % (x, y + h, x, y + r, x, y, x + r, y, x + w - r, y, x + w, y, x + w, y + r, x + w, y + h))


def render_chart(series):
    W, H, L, B, T = 760, 220, 34, 26, 10
    plot_w, plot_h = W - L - 8, H - B - T
    totals = [sum(r[1:]) for r in series]
    peak = max(totals + [1])
    step = max(1, -(-peak // 4))
    top = step * 4
    n = len(series)
    slot = plot_w / n
    bw = max(2.0, min(18.0, slot * 0.7))

    parts = []
    for k in range(5):
        v = step * k
        y = T + plot_h - plot_h * v / top
        parts.append('<line class="grid" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>' % (L, W - 8, y, y))
        parts.append('<text class="axis" x="%d" y="%.1f" text-anchor="end">%d</text>' % (L - 6, y + 4, v))

    label_every = max(1, n // 8)
    for i, row in enumerate(series):
        x = L + i * slot + (slot - bw) / 2
        y_base = T + plot_h
        segs = []
        nonzero = [k for k in range(1, len(row)) if row[k]]
        for k in range(1, len(row)):
            v = row[k]
            if not v:
                continue
            h = plot_h * v / top
            y = y_base - h
            gap = 2 if k != nonzero[0] and h > 3 else 0
            hh = h - gap
            if k == nonzero[-1]:
                segs.append('<path class="s%d" d="%s"/>' % (k, bar_path(x, y, bw, hh, 4)))
            else:
                segs.append('<rect class="s%d" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>' % (k, x, y, bw, hh))
            y_base = y
        tip = "%s|%s" % (row[0], "|".join(str(v) for v in row[1:]))
        parts.append('<g class="col" data-tip="%s"><rect class="hit" x="%.1f" y="%d" width="%.1f" height="%d"/>%s</g>'
                     % (e(tip), L + i * slot, T, slot, plot_h, "".join(segs)))
        if i % label_every == 0 or i == n - 1:
            d = datetime.strptime(row[0], "%Y-%m-%d").strftime("%d %b")
            last = i == n - 1  # right-align the final label so it is not clipped
            parts.append('<text class="axis" x="%.1f" y="%d" text-anchor="%s">%s</text>'
                         % (x + (bw if last else bw / 2), H - 8, "end" if last else "middle", d))

    legend = "".join('<span class="key"><i class="sw s%d"></i>%s</span>' % (n + 1, e(lbl))
                     for n, (_, lbl) in enumerate(CHART_KINDS))
    rows = "".join("<tr><td>%s</td>%s<td>%d</td></tr>" % (r[0], "".join("<td>%d</td>" % v for v in r[1:]), sum(r[1:]))
                   for r in reversed(series) if sum(r[1:]))
    head = "".join("<th>%s</th>" % e(lbl) for _, lbl in CHART_KINDS)
    return (
        '<div class="legend">%s</div>'
        '<div class="chart"><svg viewBox="0 0 %d %d" role="img" aria-label="Replies per day by type">%s</svg>'
        '<div class="tip" hidden></div></div>'
        '<details class="tableview"><summary>Show as table</summary><div class="table-wrap"><table>'
        '<thead><tr><th>Day</th>%s<th>Total</th></tr></thead><tbody>%s</tbody></table></div></details>'
    ) % (legend, W, H, "".join(parts), head, rows or '<tr><td colspan="5">No replies in this window.</td></tr>')


def tile(label, value, sub="", tone=""):
    return ('<div class="tile %s"><div class="t-label">%s</div><div class="t-value">%s</div>'
            '<div class="t-sub">%s</div></div>' % (tone, e(label), e(value), sub))


def render(snap, token, msg=None, ok=True, render_markdown=None):
    s = snap
    out = []

    out.append('<header class="dash-head"><div><h1>Social agent</h1>'
               '<div class="meta">%s &middot; %s</div></div><div class="head-actions">%s%s</div></header>' % (
                   e(s["now"].strftime("%a %d %b %Y, %H:%M")), e(s["tzname"]),
                   '<a class="btn ghost" href="/due">What&rsquo;s due now?</a>',
                   form("resume", token, '<button class="btn">Resume</button>') if s["paused"] else
                   form("pause", token, '<input name="reason" placeholder="reason (optional)" maxlength="300">'
                                       '<button class="btn danger">Pause everything</button>')))

    if msg:
        out.append('<div class="flash %s">%s</div>' % ("ok" if ok else "bad", e(msg)))
    if s["paused"]:
        out.append('<div class="banner bad"><strong>PAUSED</strong> — all activity halted. %s</div>' % e(s["paused"]))
    if s["idle_days"] is not None and s["idle_days"] >= 2:
        out.append('<div class="banner warn"><strong>No agent activity for %d days</strong> — last logged action %s. '
                   'Is the loop running?</div>' % (int(s["idle_days"]), e(short_ts(s["last_ts"]))))
    for a in s["accounts"]:
        if a["cooldown"]:
            mins = int((a["cooldown"][0] - time.time()) // 60)
            out.append('<div class="banner warn"><strong>%s / %s parked</strong> — %dh %02dm left — %s</div>'
                       % (e(a["brand"]), e(a["platform"]), mins // 60, mins % 60, e(a["cooldown"][1])))

    open_esc = [x for x in s["escalations"] if x["state"] in ("open", "none")]
    high = sum(1 for l in s["waiting"] if l.get("intent") == "high")
    out.append('<section class="tiles">%s%s%s%s%s</section>' % (
        tile("Open escalations", len(open_esc), "waiting on a human", "alert" if open_esc else ""),
        tile("Leads waiting", len(s["waiting"]), "%d already handled (seen.jsonl)" % s["handled"]),
        tile("High-intent waiting", high, "%d research leads parked" % s["research"]),
        tile("Actions today", s["today_total"], "replies, DMs, escalations"),
        tile("Watch hits, 7 days", s["watch_week"], "%d all time" % len(s["watch"])),
    ))

    out.append('<section class="card"><h2>Replies per day</h2>%s</section>' % render_chart(s["series"]))

    # Accounts
    rows = []
    for a in s["accounts"]:
        if not a["enabled"]:
            state = '<span class="pill">disabled</span>'
        elif a["cooldown"]:
            state = '<span class="pill warn">parked</span>'
        elif s["paused"]:
            state = '<span class="pill bad">paused</span>'
        else:
            state = '<span class="pill ok">active</span>'
        park = ""
        if a["enabled"] and not a["cooldown"]:
            park = form("park", token,
                        '<input type="hidden" name="brand" value="%s"><input type="hidden" name="platform" value="%s">'
                        '<select name="hours"><option>6</option><option selected>24</option><option>48</option></select>'
                        '<input name="reason" placeholder="why" maxlength="200" required>'
                        '<button class="btn small">Park</button>' % (e(a["brand"]), e(a["platform"])))
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class=num>%d</td><td class=num>%s</td>"
                    "<td class=num>%d</td><td class=num>%d</td><td class=num>%d</td><td>%s</td><td>%s</td></tr>" % (
                        e(a["brand"]), e(a["platform"]), state, a["pub"], e(a["left"]), a["dm"], a["com"], a["esc"],
                        e(short_ts(a["last_run"])) or "never", park))
    out.append('<section class="card"><h2>Accounts today</h2><div class="table-wrap"><table>'
               '<thead><tr><th>Brand</th><th>Platform</th><th>State</th><th>Replies</th><th>Left</th><th>DMs</th>'
               '<th>Comments</th><th>Escalated</th><th>Last run</th><th>Park account</th></tr></thead>'
               '<tbody>%s</tbody></table></div>'
               '<p class="hint">Park = <code>bin/cooldown.sh</code>. Use it when you see a platform warning the agent '
               'missed. It cannot be undone here on purpose; delete the file in <code>data/cooldown/</code> to release early.</p>'
               '</section>' % "".join(rows))

    # Escalations
    cards = []
    for x in reversed(open_esc):
        body = render_markdown(x["body"]) if render_markdown else "<pre>%s</pre>" % e(x["body"])
        badge = '<span class="pill">no status line</span>' if x["state"] == "none" else ""
        resolve = form("resolve", token,
                       '<input type="hidden" name="heading" value="%s">'
                       '<input name="note" placeholder="what was done (optional)" maxlength="300">'
                       '<button class="btn small">Mark resolved</button>' % e(x["heading"]))
        cards.append('<details class="esc"><summary><span class="esc-title">%s</span>%s</summary>'
                     '<div class="esc-body">%s</div>%s</details>' % (e(x["heading"].replace("**", "")), badge, body, resolve))
    out.append('<section class="card"><h2>Open escalations <span class="count">%d</span></h2>%s'
               '<p class="hint">Newest first. Resolving rewrites that one <code>Status:</code> line in '
               '<code>reports/escalations.md</code>; <a href="/r/escalations.md">full file</a>.</p></section>'
               % (len(open_esc), "".join(cards) or "<p>Nothing waiting. </p>"))

    # Leads
    brands = sorted({l.get("brand", "") for l in s["waiting"]})
    lrows = []
    for l in s["waiting"]:
        lrows.append(
            '<tr data-brand="%s" data-platform="%s" data-intent="%s" data-text="%s">'
            '<td>%s</td><td>%s</td><td><a href="%s" target="_blank" rel="noopener">@%s</a></td>'
            '<td class="text">%s</td><td><span class="pill %s">%s</span></td><td>%s</td>'
            '<td><a class="btn small ghost" href="%s" target="_blank" rel="noopener">Open post</a></td></tr>' % (
                e(l.get("brand")), e(l.get("platform")), e(l.get("intent")),
                e((l.get("text", "") + " " + l.get("author", "") + " " + l.get("query", "")).lower()),
                e(short_ts(l.get("posted_at") or l.get("collected_at"))), e(l.get("platform")),
                safe_url(l.get("author_url")), e(norm_handle(l.get("author"))),
                e(trunc(l.get("text"), 220)), "ok" if l.get("intent") == "high" else "", e(l.get("intent")),
                e(l.get("query")), safe_url(l.get("post_url"))))
    opt = lambda vals: "".join('<option value="%s">%s</option>' % (e(v), e(v)) for v in vals)
    out.append(
        '<section class="card"><h2>Leads waiting for a reply <span class="count" id="lead-count">%d</span></h2>'
        '<div class="filters"><select id="f-brand"><option value="">all brands</option>%s</select>'
        '<select id="f-platform"><option value="">all platforms</option>%s</select>'
        '<select id="f-intent"><option value="">any intent</option><option>high</option><option>medium</option></select>'
        '<input id="f-q" type="search" placeholder="search text, author, query"></div>'
        '<div class="table-wrap tall"><table id="leads"><thead><tr><th>Posted</th><th>Platform</th><th>Author</th>'
        '<th>What they said</th><th>Intent</th><th>Query</th><th></th></tr></thead><tbody>%s</tbody></table></div>'
        '<p class="hint">Replying stays with <code>social-engage</code>. It runs the budget and dedupe checks this page cannot run. '
        'Leads whose post or author is already in <code>seen.jsonl</code> are hidden.</p></section>'
        % (len(s["waiting"]), opt(brands), opt(PLATFORMS), "".join(lrows)))

    # Watch
    wrows = "".join(
        '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class="text">%s</td>'
        '<td><a class="btn small ghost" href="%s" target="_blank" rel="noopener">Open</a></td></tr>' % (
            e(short_ts(w.get("posted_at") or w.get("found_at"))), e(w.get("watch")), e(w.get("price", "")),
            e(w.get("location", "")), e(trunc(w.get("text"), 180)), safe_url(w.get("post_url")))
        for w in s["watch"][:20])
    out.append('<section class="card"><h2>Latest watch hits</h2><div class="table-wrap"><table><thead><tr>'
               '<th>Posted</th><th>Watch</th><th>Price</th><th>Location</th><th>Post</th><th></th></tr></thead>'
               '<tbody>%s</tbody></table></div></section>' % (wrows or '<tr><td colspan="6">No hits yet.</td></tr>'))

    # Recent actions
    arows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class=\"text\">%s</td></tr>" % (
            e(short_ts(x.get("ts"))), e(x.get("brand")), e(x.get("platform")), e(x.get("kind")),
            e(x.get("author") or x.get("skill") or ""), e(trunc(x.get("text") or x.get("note") or "", 160)))
        for x in s["recent"])
    out.append('<section class="card"><h2>Recent actions</h2><div class="table-wrap"><table><thead><tr>'
               '<th>Time</th><th>Brand</th><th>Platform</th><th>Kind</th><th>Who / skill</th><th>Detail</th></tr></thead>'
               '<tbody>%s</tbody></table></div></section>' % arows)

    out.append(SCRIPT)
    return '<style>%s</style>%s' % (CSS, "".join(out))


def render_due(output):
    return ('<header class="dash-head"><div><h1>What&rsquo;s due now</h1>'
            '<div class="meta">Output of <code>bin/due.sh</code>. It only reads; nothing was started.</div></div></header>'
            '<section class="card"><pre>%s</pre></section><p><a href="/">&larr; dashboard</a></p>'
            '<style>%s</style>' % (e(output), CSS))


CSS = """
.wrap.wide { max-width: 1240px; }
:root { --ok: #1f7a4d; --warn: #9a6400; --bad: #b3261e;
  --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a; }
@media (prefers-color-scheme: dark) {
  :root { --ok: #5cc28d; --warn: #e0a640; --bad: #f08a80;
    --s1: #3987e5; --s2: #d95926; --s3: #199e70; }
}
.dash-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
.dash-head h1 { border: none; margin: 0; padding: 0; }
.dash-head .meta { margin: 0.2rem 0 0; }
.head-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
form.inline { display: flex; gap: 0.4rem; flex-wrap: wrap; align-items: center; margin: 0; }
input, select { font: inherit; font-size: 0.85rem; padding: 0.3rem 0.5rem; border: 1px solid var(--border);
  border-radius: 6px; background: var(--card); color: var(--fg); }
.btn { font: inherit; font-size: 0.85rem; padding: 0.35rem 0.8rem; border-radius: 6px; cursor: pointer;
  border: 1px solid var(--accent); background: var(--accent); color: #fff; text-decoration: none; display: inline-block; white-space: nowrap; }
.btn.ghost { background: transparent; color: var(--accent); }
.btn.danger { background: var(--bad); border-color: var(--bad); }
.btn.small { font-size: 0.78rem; padding: 0.2rem 0.6rem; }
.flash, .banner { padding: 0.6rem 0.9rem; border-radius: 8px; margin: 0.6rem 0; font-size: 0.92rem; border: 1px solid var(--border); background: var(--card); }
.flash.ok { border-color: var(--ok); } .flash.bad, .banner.bad { border-color: var(--bad); }
.banner.warn { border-color: var(--warn); }
.banner.bad strong { color: var(--bad); } .banner.warn strong { color: var(--warn); }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.8rem; margin: 1.2rem 0; }
.tile { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 0.8rem 1rem; }
.tile.alert { border-color: var(--bad); }
.t-label { font-size: 0.8rem; color: var(--muted); }
.t-value { font-size: 2rem; font-weight: 650; line-height: 1.2; font-variant-numeric: tabular-nums; }
.tile.alert .t-value { color: var(--bad); }
.t-sub { font-size: 0.78rem; color: var(--muted); }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 0.4rem 1.1rem 1rem; margin: 1rem 0; }
.card h2 { font-size: 1.1rem; margin: 0.8rem 0 0.6rem; }
.count { font-size: 0.8rem; color: var(--muted); font-weight: 500; margin-left: 0.3rem; }
.hint { color: var(--muted); font-size: 0.8rem; margin: 0.6rem 0 0; }
.pill { display: inline-block; font-size: 0.72rem; padding: 0.1em 0.55em; border-radius: 999px;
  border: 1px solid var(--border); color: var(--muted); white-space: nowrap; }
.pill.ok { color: var(--ok); border-color: var(--ok); } .pill.warn { color: var(--warn); border-color: var(--warn); }
.pill.bad { color: var(--bad); border-color: var(--bad); }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
td.text { min-width: 18rem; }
.card table { font-size: 0.86rem; }
.card td, .card th { vertical-align: top; }
.table-wrap.tall { max-height: 34rem; overflow-y: auto; }
.table-wrap.tall thead th { position: sticky; top: 0; z-index: 1; }
.filters { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.4rem; }
.filters input[type=search] { flex: 1; min-width: 12rem; }
details.esc { border: 1px solid var(--border); border-radius: 8px; margin: 0.5rem 0; padding: 0.5rem 0.8rem; }
details.esc summary { cursor: pointer; display: flex; gap: 0.5rem; align-items: baseline; }
.esc-title { font-weight: 600; font-size: 0.92rem; }
.esc-body { font-size: 0.9rem; border-left: 3px solid var(--border); padding-left: 0.8rem; margin: 0.5rem 0; }
details.esc form { margin-top: 0.4rem; }
details.esc form input[name=note] { flex: 1; min-width: 14rem; }
.legend { display: flex; gap: 1rem; font-size: 0.82rem; color: var(--muted); flex-wrap: wrap; }
.key { display: inline-flex; align-items: center; gap: 0.35rem; }
.sw { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.sw.s1, .s1 { background: var(--s1); fill: var(--s1); }
.sw.s2, .s2 { background: var(--s2); fill: var(--s2); }
.sw.s3, .s3 { background: var(--s3); fill: var(--s3); }
.chart { position: relative; }
.chart svg { width: 100%; height: auto; display: block; }
.chart .grid { stroke: var(--border); stroke-width: 1; }
.chart .axis { fill: var(--muted); font-size: 10px; }
.chart .hit { fill: transparent; }
.chart .col:hover .hit { fill: var(--code-bg); }
.tip { position: absolute; pointer-events: none; background: var(--bg); border: 1px solid var(--border);
  border-radius: 6px; padding: 0.4rem 0.6rem; font-size: 0.8rem; box-shadow: 0 2px 8px rgba(0,0,0,.12); white-space: nowrap; }
.tip b { display: block; margin-bottom: 0.15rem; }
.tip i { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 0.35rem; }
.tableview { font-size: 0.82rem; color: var(--muted); margin-top: 0.4rem; }
.tableview summary { cursor: pointer; }
"""

SCRIPT = """<script>
(function () {
  var names = %s;
  var chart = document.querySelector('.chart'), tip = chart && chart.querySelector('.tip');
  if (chart) {
    chart.addEventListener('mousemove', function (ev) {
      var g = ev.target.closest('.col');
      if (!g) { tip.hidden = true; return; }
      var p = g.getAttribute('data-tip').split('|'), total = 0, rows = '';
      for (var i = 1; i < p.length; i++) {
        total += +p[i];
        rows += '<div><i class="s' + i + '"></i>' + names[i - 1] + ': ' + p[i] + '</div>';
      }
      tip.innerHTML = '<b>' + p[0] + ' &middot; ' + total + '</b>' + rows;
      var r = chart.getBoundingClientRect(), x = ev.clientX - r.left + 12;
      if (x + 180 > r.width) x -= 200;
      tip.style.left = x + 'px'; tip.style.top = (ev.clientY - r.top - 10) + 'px';
      tip.hidden = false;
    });
    chart.addEventListener('mouseleave', function () { tip.hidden = true; });
  }
  var ids = ['f-brand', 'f-platform', 'f-intent', 'f-q'];
  function apply() {
    var b = document.getElementById('f-brand').value, p = document.getElementById('f-platform').value,
        n = document.getElementById('f-intent').value, q = document.getElementById('f-q').value.toLowerCase(), shown = 0;
    document.querySelectorAll('#leads tbody tr').forEach(function (tr) {
      var ok = (!b || tr.dataset.brand === b) && (!p || tr.dataset.platform === p) &&
               (!n || tr.dataset.intent === n) && (!q || tr.dataset.text.indexOf(q) !== -1);
      tr.style.display = ok ? '' : 'none';
      if (ok) shown++;
    });
    document.getElementById('lead-count').textContent = shown;
  }
  ids.forEach(function (id) { var el = document.getElementById(id); if (el) el.addEventListener('input', apply); });
})();
</script>""" % json.dumps([lbl for _, lbl in CHART_KINDS])
