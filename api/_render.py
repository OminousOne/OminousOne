"""
Shared renderer for the live stats endpoints.

Each endpoint fetches fresh data from the GitHub GraphQL API (token in the
GITHUB_TOKEN env var) and renders an SVG card in the same visual system as the
baked assets built by tools/build.py. Cards are cached at the edge for ten
minutes via Cache-Control, so the numbers are near-live without hammering the
API. If GitHub is unreachable the endpoints return a styled fallback card
instead of a broken image.
"""

import datetime
import json
import math
import os
import urllib.request

LOGIN = "OminousOne"

AMBER = "#FFB300"
SLATE = "#6C7986"
SLATE2 = "#46525E"
LINE = "#1E262E"
PANEL = "#0A0D10"
BG = "#0E1116"

MONO = "ui-monospace,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

# languages that are markup, config, or vendored noise rather than "what I write"
LANG_SKIP = {"HTML", "CSS", "SCSS", "Shell", "Dockerfile", "Makefile", "CMake",
             "Nix", "Batchfile", "PowerShell", "MDX", "Go Template", "Smarty"}

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    repositories(first: 50, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        pushedAt
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": f"{LOGIN}-profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    if "errors" in data and not data.get("data"):
        raise RuntimeError(data["errors"][0].get("message", "graphql error"))
    return data["data"]["user"]


# ---------------------------------------------------------------- helpers

def f(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


def shell(w, h, css, body, label):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">
<style><![CDATA[
text{{font-family:{MONO};}}
{chr(10).join(css)}
@media (prefers-reduced-motion:reduce){{*{{animation:none !important;}}}}
]]></style>
<defs>
  <pattern id="scan" width="3" height="3" patternUnits="userSpaceOnUse">
    <rect width="3" height="1" y="2" fill="#000"/>
  </pattern>
</defs>
{body}
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="10" fill="url(#scan)" opacity="0.14"/>
</svg>"""


def frame(w, h, rx=10):
    return f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx}" fill="{BG}" stroke="#262E36" stroke-width="1.5"/>'


def module_box(w, h, title, status):
    return (
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="8" '
        f'fill="{PANEL}" stroke="#262E36" stroke-width="1.5"/>'
        f'<text x="12" y="19" font-size="11" letter-spacing="1.4" fill="{AMBER}">{title}</text>'
        f'<text x="{w - 12}" y="19" font-size="9" letter-spacing="0.8" fill="{SLATE2}" text-anchor="end">{status}</text>'
    )


def odometer(x, y, value, size, dur, prefix, css):
    out, dx = [], 0
    ch_w = size * 0.62
    for ci, ch in enumerate(str(value)):
        d = int(ch)
        p = f"{prefix}{ci}"
        if d > 0:
            css.append(f"@keyframes {p}{{from{{transform:translateY(0)}}to{{transform:translateY({f(-d * size * 1.15)}px)}}}}")
            anim = f"animation:{p} {f(dur)}s steps({d}) both;animation-delay:{f(0.15 * ci + 0.1)}s"
        else:
            anim = ""
        strip = "".join(
            f'<text x="{f(x + dx)}" y="{f(y + k * size * 1.15)}" font-size="{size}" fill="{AMBER}">{k}</text>'
            for k in range(d + 1)
        )
        out.append(
            f'<clipPath id="{p}c"><rect x="{f(x + dx - 1)}" y="{f(y - size + 2)}" width="{f(ch_w + 2)}" height="{f(size + 4)}"/></clipPath>'
            f'<g clip-path="url(#{p}c)"><g style="{anim}">{strip}</g></g>'
        )
        dx += ch_w
    return "".join(out)


# ---------------------------------------------------------------- data shaping

def calendar_days(user):
    """[(date, count)] for every day in the calendar window."""
    days = []
    for w in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in w["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    return days


def streaks(days):
    counts = [c for _, c in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    current = 0
    for c in reversed(counts):
        if c > 0:
            current += 1
        else:
            break
    active = sum(1 for c in counts if c > 0)
    return longest, current, active, len(counts)


def lang_mix(user, months=12):
    cutoff = (datetime.date.today() - datetime.timedelta(days=months * 30)).isoformat()
    totals = {}
    for repo in user["repositories"]["nodes"]:
        if repo["pushedAt"][:10] < cutoff:
            continue
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            if name not in LANG_SKIP:
                totals[name] = totals.get(name, 0) + e["size"]
    total = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda kv: -kv[1])[:4]
    mix = [(name, size / total * 100) for name, size in top]
    other = 100 - sum(p for _, p in mix)
    if other > 0.5:
        mix.append(("other", other))
    return mix


# ---------------------------------------------------------------- cards

def render_stats(user):
    W, H = 830, 172
    css, out = [], [frame(W, H)]
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]
    nz = sorted(c for w in weeks for c in w if c > 0)
    busiest = nz[-1] if nz else 0

    def level(c):
        if c == 0 or not nz:
            return None
        idx = min(3, int(4 * nz.index(c) / len(nz)))
        return (0.25, 0.45, 0.7, 1.0)[idx]

    step, cell = 14.75, 11.5
    gx, gy = 24, 22
    css.append("@keyframes cellin{from{opacity:0}to{opacity:1}}")
    for wi, week in enumerate(weeks):
        col = []
        for di, c in enumerate(week):
            a = level(c)
            if a is None:
                col.append(f'<rect x="{f(gx + wi * step)}" y="{f(gy + di * step)}" width="{cell}" height="{cell}" rx="2" fill="#151B22"/>')
            else:
                col.append(f'<rect x="{f(gx + wi * step)}" y="{f(gy + di * step)}" width="{cell}" height="{cell}" rx="2" fill="{AMBER}" opacity="{f(a)}"/>')
        out.append(f'<g style="animation:cellin .5s both;animation-delay:{f(wi * 0.022)}s">' + "".join(col) + "</g>")

    ty = gy + 7 * step + 26
    total = f"{cal['totalContributions']:,}"
    out.append(f'<text x="24" y="{f(ty)}" font-size="12" fill="{SLATE}"><tspan fill="{AMBER}" font-size="15">{total}</tspan> contributions in the past year</text>')
    out.append(f'<text x="{W - 24}" y="{f(ty)}" font-size="12" fill="{SLATE}" text-anchor="end">busiest day: <tspan fill="{AMBER}" font-size="15">{busiest}</tspan></text>')
    label = f"Live heatmap: {total} contributions in the past year, busiest day {busiest}."
    return shell(W, H, css, "".join(out), label)


def render_streaks(user):
    W, H = 268, 170
    longest, current, active, window = streaks(calendar_days(user))
    total = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    avg = total / active if active else 0
    css, out = [], [module_box(W, H, "STREAKS", "LIVE")]
    out.append(f'<text x="16" y="52" font-size="11" fill="{SLATE}">longest streak</text>')
    out.append(odometer(16, 90, longest, 30, 0.9, "odl_", css))
    out.append(f'<text x="{16 + len(str(longest)) * 19 + 8}" y="90" font-size="11" fill="{SLATE2}">days in a row</text>')
    out.append(f'<text x="16" y="120" font-size="11" fill="{SLATE}">active days <tspan fill="{AMBER}" font-size="14">{active}</tspan> <tspan fill="{SLATE2}">of {window}</tspan></text>')
    out.append(f'<text x="12" y="{H - 12}" font-size="10" fill="{SLATE2}">{f(round(avg, 1))} contributions per active day</text>')
    label = f"Streaks, live: longest {longest} days, {active} active days of {window}, {f(round(avg, 1))} contributions per active day."
    return shell(W, H, css, "".join(out), label)


def render_weekdays(user):
    W, H = 268, 170
    sums = [0] * 7
    for date, c in calendar_days(user):
        sums[datetime.date.fromisoformat(date).weekday()] += c
    total = sum(sums) or 1
    weekend = round((sums[5] + sums[6]) / total * 100)
    vmax = max(sums) or 1
    peak_i = sums.index(max(sums))
    daynames = ["mondays", "tuesdays", "wednesdays", "thursdays", "fridays", "saturdays", "sundays"]
    css, out = [], [module_box(W, H, "WEEKDAYS", "LIVE")]
    css.append("@keyframes wbar{from{transform:scaleY(0)}to{transform:scaleY(1)}}")
    bx, base, bw = 26, 122, 22
    for i, v in enumerate(sums):
        h_ = 8 + 66 * v / vmax
        a = 1.0 if i == peak_i else 0.45 + 0.3 * v / vmax
        out.append(
            f'<rect x="{bx + i * 31}" y="{f(base - h_)}" width="{bw}" height="{f(h_)}" rx="2" fill="{AMBER}" '
            f'opacity="{f(a)}" style="animation:wbar .55s cubic-bezier(.3,.6,.3,1) both;'
            f'animation-delay:{f(0.06 * i)}s;transform-origin:0px {base}px"/>'
        )
        out.append(f'<text x="{bx + i * 31 + bw / 2}" y="136" font-size="8" fill="{SLATE2}" text-anchor="middle">{"mtwtfss"[i]}</text>')
    out.append(f'<text x="12" y="{H - 12}" font-size="10" fill="{SLATE2}">{daynames[peak_i]} lead · weekends get {weekend}%</text>')
    label = f"Contributions by weekday, live: {daynames[peak_i]} lead, weekends get {weekend} percent."
    return shell(W, H, css, "".join(out), label)


def render_langs(user):
    W, H = 268, 170
    mix = lang_mix(user)
    css, out = [], [module_box(W, H, "LANGUAGES", "LAST 12 MONTHS")]
    cx, cy, r = 64, 96, 34
    circ = 2 * math.pi * r
    alphas = [1.0, 0.45, 0.3, 0.2]
    css.append("@keyframes din{from{opacity:0;transform:rotate(-40deg)}to{opacity:1;transform:rotate(0deg)}}")
    segs, acc = [], 0.0
    for i, (name, pct) in enumerate(mix):
        seg = circ * pct / 100
        color = 'stroke="#2A333C"' if name == "other" else f'stroke="{AMBER}" stroke-opacity="{alphas[min(i, 3)]}"'
        segs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" {color} stroke-width="11" '
            f'stroke-dasharray="{f(max(seg - 2, 1))} {f(circ - max(seg - 2, 1))}" '
            f'stroke-dashoffset="{f(-acc)}" transform="rotate(-90 {cx} {cy})"/>'
        )
        acc += seg
    out.append(f'<g style="animation:din .9s cubic-bezier(.3,.6,.3,1) both;transform-origin:{cx}px {cy}px">' + "".join(segs) + "</g>")
    out.append(f'<text x="{cx}" y="{cy + 4}" font-size="12" fill="{AMBER}" text-anchor="middle">{f(round(mix[0][1]))}%</text>')
    ry = 56
    for i, (name, pct) in enumerate(mix):
        if name == "other":
            continue
        out.append(f'<rect x="128" y="{ry - 8}" width="9" height="9" rx="2" fill="{AMBER}" opacity="{alphas[min(i, 3)]}"/>')
        out.append(f'<text x="144" y="{ry}" font-size="10.5" fill="{SLATE}">{name.lower()} <tspan fill="{SLATE2}">{f(round(pct))}%</tspan></text>')
        ry += 24
    out.append(f'<text x="12" y="{H - 12}" font-size="10" fill="{SLATE2}">by size, repos pushed this year</text>')
    lbl = ", ".join(f"{n} {round(p)} percent" for n, p in mix if n != "other")
    return shell(W, H, css, "".join(out), f"Languages in repos pushed in the last 12 months, live: {lbl}.")


def render_footer(user):
    W, H = 900, 44
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]
    busiest = max((c for w in weeks for c in w), default=0)
    total = f"{cal['totalContributions']:,}"
    css, out = [], [frame(W, H)]
    out.append(
        f'<text x="24" y="27" font-size="11.5" fill="{SLATE}">past year on github: '
        f'<tspan fill="{AMBER}">{total}</tspan> contributions · busiest day: <tspan fill="{AMBER}">{busiest}</tspan></text>'
    )
    css.append("@keyframes hpulse{0%,100%{opacity:1}50%{opacity:.25}}")
    out.append(f'<circle cx="745" cy="23" r="3" fill="{AMBER}" style="animation:hpulse 2s ease-in-out infinite"/>')
    out.append(f'<text x="{W - 24}" y="27" font-size="11.5" fill="{SLATE}" text-anchor="end">selected projects</text>')
    return shell(W, H, css, "".join(out), f"Past year on GitHub, live: {total} contributions, busiest day {busiest}.")


def _kv_incr(key):
    """increment a counter in the attached Upstash/Vercel KV store."""
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    req = urllib.request.Request(f"{url}/incr/{key}", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())["result"]


def render_visitors(_user=None):
    W, H = 830, 64
    count = _kv_incr("profile_views")
    css, out = [], [frame(W, H, rx=8)]
    out.append(f'<text x="18" y="39" font-size="14" letter-spacing="2" fill="{AMBER}">VISITORS</text>')
    if count is None:
        out.append(f'<text x="{W / 2}" y="39" font-size="14" fill="{SLATE2}" text-anchor="middle">------</text>')
        out.append(f'<text x="{W - 18}" y="39" font-size="10" fill="{SLATE2}" text-anchor="end">counter warming up</text>')
        return shell(W, H, css, "".join(out), "Visitor counter is warming up.")
    digits = str(count).zfill(6)
    x = (W - len(digits) * 26 * 0.62) / 2
    out.append(f'<rect x="{f(x - 12)}" y="12" width="{f(len(digits) * 26 * 0.62 + 24)}" height="40" rx="4" fill="{PANEL}" stroke="#232B33"/>')
    for ci, ch in enumerate(digits):
        out.append(odometer(x + ci * 26 * 0.62, 44, int(ch), 26, 0.7 + ci * 0.12, f"vc{ci}_", css))
    out.append(f'<text x="{W - 18}" y="39" font-size="10" fill="{SLATE2}" text-anchor="end">you just made this number go up</text>')
    return shell(W, H, css, "".join(out), f"Live visitor counter: you are visitor {count:,}.")


def render_guestbook(_user=None):
    W = 830
    req = urllib.request.Request(
        f"https://raw.githubusercontent.com/{LOGIN}/{LOGIN}/main/data/guestbook.json",
        headers={"User-Agent": f"{LOGIN}-profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        entries = json.loads(resp.read())
    import html as _html
    n_rows = max(len(entries[-8:]), 1)
    H = 58 + n_rows * 22 + 16
    css, out = [], [frame(W, H, rx=8)]
    out.append(f'<text x="18" y="29" font-size="12" letter-spacing="1.6" fill="{AMBER}">GUESTBOOK</text>')
    out.append(f'<text x="{W - 18}" y="29" font-size="10" fill="{SLATE2}" text-anchor="end">signed by visitors, via github issues</text>')
    out.append(f'<line x1="18" y1="40" x2="{W - 18}" y2="40" stroke="{LINE}"/>')
    css.append("@keyframes gbin{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:translateX(0)}}")
    recent = list(reversed(entries[-8:]))
    if not recent:
        out.append(f'<text x="{W / 2}" y="70" font-size="12" fill="{SLATE2}" text-anchor="middle">nobody has signed yet · be the first</text>')
    ry = 64
    for i, e in enumerate(recent):
        user = _html.escape(str(e.get("user", ""))[:30])
        msg = _html.escape(str(e.get("msg", ""))[:60])
        date = _html.escape(str(e.get("date", ""))[:10])
        out.append(
            f'<g style="animation:gbin .4s cubic-bezier(.3,.6,.3,1) both;animation-delay:{f(0.07 * i)}s">'
            f'<text x="18" y="{ry}" font-size="11" fill="{AMBER}">{user}</text>'
            f'<text x="150" y="{ry}" font-size="11" fill="{SLATE}">{msg}</text>'
            f'<text x="{W - 18}" y="{ry}" font-size="10" fill="{SLATE2}" text-anchor="end">{date}</text></g>'
        )
        ry += 22
    label = f"Guestbook with {len(entries)} signatures, showing the most recent."
    return shell(W, H, css, "".join(out), label)


def render_fallback(w, h):
    out = [frame(w, h)]
    out.append(f'<text x="{w / 2}" y="{h / 2 + 4}" font-size="11" fill="{SLATE2}" text-anchor="middle">stats are napping · back in a minute</text>')
    return shell(w, h, [], "".join(out), "Live stats temporarily unavailable.")


# name: (renderer, width, height, needs_github_fetch, cache_seconds)
CARDS = {
    "stats": (render_stats, 830, 172, True, 600),
    "streaks": (render_streaks, 268, 170, True, 600),
    "weekdays": (render_weekdays, 268, 170, True, 600),
    "langs": (render_langs, 268, 170, True, 600),
    "footer": (render_footer, 900, 44, True, 600),
    "visitors": (render_visitors, 830, 64, False, 0),
    "guestbook": (render_guestbook, 830, 236, False, 300),
}


def render_card(name):
    """returns (svg, cache_seconds). Falls back to a styled card on any error."""
    fn, w, h, needs_gh, cache = CARDS[name]
    try:
        return fn(fetch() if needs_gh else None), cache
    except Exception:
        return render_fallback(w, h), 60
