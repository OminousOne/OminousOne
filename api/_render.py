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

AMBER = "#FFC164"
WHITE = "#F6E9D0"
SLATE = "#C0B7AD"
SLATE2 = "#A79E95"
LINE = "#38313C"
PANEL = "#19161D"
BG = "#211B24"
BARBG = "#372E3A"
MINT = "#9AE6CB"
CORAL = "#FFAD92"
LILAC = "#DABAFB"
BLUE = "#ADD8FF"

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


BOOT_HOLD = 4.8  # match the README boot animation
CARD_GUTTER = 4  # equal visual rails for full-width and packed cards


def shell(w, h, css, body, label, hold=BOOT_HOLD):
    scan = f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="8" fill="url(#scan)" opacity="0.08"/>'
    body += scan
    if hold:
        css = [*css, "@keyframes bootrev{0%{opacity:0}30%{opacity:.8}55%{opacity:.15}100%{opacity:1}}"]
        body = f'<g style="animation:bootrev .5s linear both;animation-delay:{hold}s">{body}</g>'
    width = w + 2 * CARD_GUTTER
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" viewBox="{-CARD_GUTTER} 0 {width} {h}" role="img" aria-label="{label}">
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
</svg>"""


def frame(w, h, rx=10):
    return f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx}" fill="{BG}" stroke="#51444F" stroke-width="1.5"/>'


def module_box(w, h, title, status, accent=AMBER):
    return (
        frame(w, h, rx=8)
        + f'<path d="M12 29h{w - 24}" stroke="{LINE}"/>'
        + f'<path d="M12 29h24" stroke="{accent}" stroke-width="1.5"/>'
        + f'<text x="12" y="21" font-size="13" font-weight="700" fill="{accent}">{title}</text>'
        + f'<text x="{w - 12}" y="20" font-size="10" fill="{SLATE2}" text-anchor="end">{status}</text>'
    )


def odometer(x, y, value, size, dur, prefix, css):
    out, dx = [], 0
    ch_w = size * 0.62
    for ci, ch in enumerate(str(value)):
        d = int(ch)
        p = f"{prefix}{ci}"
        if d > 0:
            css.append(f"@keyframes {p}{{from{{transform:translateY(0)}}to{{transform:translateY({f(-d * size * 1.15)}px)}}}}")
            anim = (f"transform:translateY({f(-d * size * 1.15)}px);"
                    f"animation:{p} {f(dur)}s steps({d}) both;animation-delay:{f(0.15 * ci + 0.1)}s")
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
    W, H = 830, 194
    css, out = [], [module_box(W, H, "Contribution heatmap", "Past 12 months", MINT)]
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]
    nz = sorted(c for w in weeks for c in w if c > 0)
    busiest = nz[-1] if nz else 0

    def level(c):
        if c == 0:
            return BARBG
        idx = min(3, int(4 * nz.index(c) / len(nz)))
        return ("#3E645E", "#538C7C", "#71B9A2", MINT)[idx]

    step, cell = 14.75, 11.5
    gx, gy = 24, 42
    css.append("@keyframes cellin{from{opacity:0}to{opacity:1}}")
    for wi, week in enumerate(weeks):
        col = []
        for di, c in enumerate(week):
            col.append(f'<rect x="{f(gx + wi * step)}" y="{f(gy + di * step)}" width="{cell}" height="{cell}" rx="2" fill="{level(c)}"/>')
        out.append(f'<g style="animation:cellin .5s both;animation-delay:{f(wi * 0.022)}s">' + "".join(col) + "</g>")

    ty = gy + 7 * step + 26
    total = f"{cal['totalContributions']:,}"
    out.append(f'<text x="24" y="{f(ty)}" font-size="13" fill="{SLATE}"><tspan fill="{MINT}" font-size="16">{total}</tspan> contributions in the past year</text>')
    out.append(f'<text x="{W - 24}" y="{f(ty)}" font-size="13" fill="{SLATE}" text-anchor="end">Busiest day <tspan fill="{MINT}" font-size="16">{busiest}</tspan></text>')
    label = f"Live heatmap: {total} contributions in the past year, busiest day {busiest}."
    return shell(W, H, css, "".join(out), label)


def render_streaks(user):
    W, H = 268, 170
    longest, current, active, window = streaks(calendar_days(user))
    total = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    avg = total / active if active else 0
    css, out = [], [module_box(W, H, "Streaks", "Live", AMBER)]
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
    css, out = [], [module_box(W, H, "Weekdays", "Live", BLUE)]
    css.append("@keyframes wbar{from{transform:scaleY(0)}to{transform:scaleY(1)}}")
    bx, base, bw = 26, 122, 22
    for i, v in enumerate(sums):
        h_ = 8 + 66 * v / vmax
        a = 1.0 if i == peak_i else 0.45 + 0.3 * v / vmax
        out.append(
            f'<rect x="{bx + i * 31}" y="{f(base - h_)}" width="{bw}" height="{f(h_)}" rx="2" fill="{BLUE}" '
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
    css, out = [], [module_box(W, H, "Languages", "Past 12 months", LILAC)]
    cx, cy, r = 64, 96, 34
    circ = 2 * math.pi * r
    colors = [LILAC, MINT, CORAL, BLUE]
    css.append("@keyframes din{from{opacity:0;transform:rotate(-40deg)}to{opacity:1;transform:rotate(0deg)}}")
    segs, acc = [], 0.0
    for i, (name, pct) in enumerate(mix):
        seg = circ * pct / 100
        color = BARBG if name == "other" else colors[i % len(colors)]
        segs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="11" '
            f'stroke-dasharray="{f(max(seg - 2, 1))} {f(circ - max(seg - 2, 1))}" '
            f'stroke-dashoffset="{f(-acc)}" transform="rotate(-90 {cx} {cy})"/>'
        )
        acc += seg
    out.append(f'<g style="animation:din .9s cubic-bezier(.3,.6,.3,1) both;transform-origin:{cx}px {cy}px">' + "".join(segs) + "</g>")
    out.append(f'<text x="{cx}" y="{cy + 4}" font-size="12" fill="{WHITE}" text-anchor="middle">{f(round(mix[0][1]))}%</text>')
    ry = 56
    for i, (name, pct) in enumerate(mix):
        if name == "other":
            continue
        out.append(f'<rect x="128" y="{ry - 8}" width="9" height="9" rx="2" fill="{colors[i % len(colors)]}"/>')
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
    out.append(f'<circle cx="20" cy="22" r="3" fill="{MINT}" style="animation:hpulse 2s ease-in-out infinite"/>')
    out.append(f'<text x="31" y="27" font-size="12" fill="{SLATE}">Past year on GitHub</text>')
    out.append(f'<text x="225" y="27" font-size="12" fill="{SLATE}"><tspan fill="{WHITE}" font-weight="700">{total}</tspan> contributions</text>')
    out.append(f'<text x="{W - 18}" y="27" font-size="12" fill="{SLATE}" text-anchor="end">Busiest day <tspan fill="{MINT}">{busiest}</tspan></text>')
    css.append("@keyframes hpulse{0%,100%{opacity:1}50%{opacity:.25}}")
    return shell(W, H, css, "".join(out), f"Past year on GitHub, live: {total} contributions, busiest day {busiest}.",
                 hold=BOOT_HOLD + 0.4)


def _kv_incr(key):
    """increment a counter in the attached Upstash/Vercel KV store."""
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    req = urllib.request.Request(f"{url}/incr/{key}", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())["result"]


def _person(x, y, i, cls="", fill=AMBER, opacity=None):
    """a little pixel person. deterministic variety from the index."""
    r = (i * 2654435761) & 0xFFFF
    h = 4 + (r % 3)                      # body height varies
    op = opacity if opacity is not None else (0.4, 0.55, 0.7)[(r >> 4) % 3]
    g = f'<g{cls} fill="{fill}" opacity="{f(op)}">'
    g += f'<rect x="{f(x + 1.5)}" y="{f(y + 6 - h)}" width="3" height="3"/>'          # head
    g += f'<rect x="{f(x + 1)}" y="{f(y + 9.5 - h)}" width="4" height="{f(h)}"/>'     # body
    g += f'<rect x="{f(x + 1)}" y="{f(y + 9.5)}" width="1.5" height="3"/>'            # legs
    g += f'<rect x="{f(x + 3.5)}" y="{f(y + 9.5)}" width="1.5" height="3"/>'
    return g + "</g>"


def render_visitors(_user=None):
    W = 830
    count = _kv_incr("profile_views")
    if count is None:
        H = 64
        css, out = [], [frame(W, H, rx=8)]
        out.append(f'<text x="18" y="39" font-size="15" font-weight="700" fill="{BLUE}">Visitors</text>')
        out.append(f'<text x="{W / 2}" y="39" font-size="14" fill="{SLATE2}" text-anchor="middle">------</text>')
        out.append(f'<text x="{W - 18}" y="39" font-size="10" fill="{SLATE2}" text-anchor="end">counter warming up</text>')
        return shell(W, H, css, "".join(out), "Visitor counter is warming up.")

    # the crowd: one figure per `unit` visitors, scaled so it always fits
    unit = 1
    for u in (1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 5000):
        if count // u <= 168:
            unit = u
            break
    else:
        unit = 10000
    figures = max(count // unit, 1)
    per_row = 56
    rows = (figures + per_row - 1) // per_row
    crowd_y = 70
    H = crowd_y + rows * 17 + 30

    css, out = [], [frame(W, H, rx=8)]
    out.append(f'<text x="18" y="39" font-size="15" font-weight="700" fill="{BLUE}">Visitors</text>')
    out.append(f'<path d="M18 57h{W - 36}" stroke="{LINE}"/>')
    digits = str(count).zfill(6)
    x = (W - len(digits) * 26 * 0.62) / 2
    out.append(f'<rect x="{f(x - 12)}" y="12" width="{f(len(digits) * 26 * 0.62 + 24)}" height="40" rx="4" fill="{PANEL}" stroke="#232B33"/>')
    for ci, ch in enumerate(digits):
        out.append(odometer(x + ci * 26 * 0.62, 44, int(ch), 26, 0.7 + ci * 0.12, f"vc{ci}_", css))
    out.append(f'<text x="{W - 18}" y="39" font-size="10" fill="{SLATE2}" text-anchor="end">you just made this number go up</text>')

    css.append("@keyframes rowin{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}")
    css.append("@keyframes newest{0%,100%{opacity:1}50%{opacity:.2}}")
    margin = (W - per_row * 14) / 2
    for ri in range(rows):
        row = []
        for ci in range(per_row):
            i = ri * per_row + ci
            if i >= figures:
                break
            if i == figures - 1:
                fx, fy = margin + ci * 14, crowd_y + ri * 17
                row.append(_person(fx, fy, i, cls=' style="animation:newest 1.6s ease-in-out infinite"', opacity=1.0))
                row.append(
                    f'<rect x="{f(fx - 7.5)}" y="{f(fy - 14)}" width="21" height="11" rx="2.5" fill="{PANEL}" fill-opacity=".95" stroke="#2A333C" stroke-width=".6"/>'
                    f'<text x="{f(fx + 3)}" y="{f(fy - 6)}" font-size="8" fill="{AMBER}" text-anchor="middle">you</text>'
                )
            else:
                row.append(_person(margin + ci * 14, crowd_y + ri * 17, i))
        out.append(
            f'<g style="animation:rowin .5s cubic-bezier(.3,.6,.3,1) both;animation-delay:{f(0.1 + ri * 0.08)}s">'
            + "".join(row) + "</g>"
        )

    unit_txt = "each figure is one visitor" if unit == 1 else f"each figure is {unit} visitors"
    out.append(f'<text x="18" y="{H - 12}" font-size="10" fill="{SLATE2}">{unit_txt} · the blinking one is you</text>')
    label = f"Live visitor counter: you are visitor {count:,}, shown as the blinking figure joining a crowd of {figures} pixel people."
    return shell(W, H, css, "".join(out), label)


def render_guestbook(_user=None):
    W = 830
    entries = _gh_json("data/guestbook.json")
    import html as _html
    n_rows = max(len(entries[-8:]), 1)
    H = 58 + n_rows * 22 + 16
    signatures = "1 signature" if len(entries) == 1 else f"{len(entries)} signatures"
    css, out = [], [module_box(W, H, "Guestbook signatures", signatures, LILAC)]
    css.append("@keyframes gbin{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:translateX(0)}}")
    recent = list(reversed(entries[-8:]))
    if not recent:
        out.append(f'<text x="{W / 2}" y="70" font-size="12" fill="{SLATE2}" text-anchor="middle">nobody has signed yet · be the first</text>')
    ry = 64
    for i, e in enumerate(recent):
        name = str(e.get("user", ""))
        user = _html.escape(name if len(name) <= 24 else name[:23] + "…")
        msg = _html.escape(str(e.get("msg", ""))[:60])
        date = _html.escape(str(e.get("date", ""))[:10])
        out.append(
            f'<g style="animation:gbin .4s cubic-bezier(.3,.6,.3,1) both;animation-delay:{f(0.07 * i)}s">'
            f'<path d="M18 {ry + 7}h794" stroke="{LINE}"/>'
            f'<text x="18" y="{ry}" font-size="11" fill="{LILAC}">{user}</text>'
            f'<text x="192" y="{ry}" font-size="11" fill="{WHITE}">{msg}</text>'
            f'<text x="{W - 18}" y="{ry}" font-size="10" fill="{SLATE2}" text-anchor="end">{date}</text></g>'
        )
        ry += 22
    label = f"Guestbook with {len(entries)} signatures, showing the most recent."
    return shell(W, H, css, "".join(out), label)


def _gh_json(path):
    """read a repo file fresh through the contents API (no CDN cache)."""
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        f"https://api.github.com/repos/{LOGIN}/{LOGIN}/contents/{path}?ref=main",
        headers={"Authorization": f"bearer {token}", "Accept": "application/vnd.github.raw+json",
                 "User-Agent": f"{LOGIN}-profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read())


def _boss_sprite(x, y, seed, name="", px=7):
    """procedural symmetric pixel monster, mirrored from a seeded half,
    wearing species accessories keyed off its name."""
    n = name.upper()
    ghostly = any(w in n for w in ("WRAITH", "SPECTER", "LICH", "REVENANT"))
    serpent = any(w in n for w in ("SERPENT", "BASILISK"))
    hulking = any(w in n for w in ("GOLEM", "COLOSSUS", "TITAN", "BEHEMOTH", "OGRE"))
    winged = any(w in n for w in ("DRAGON", "GARGOYLE", "CHIMERA"))
    hydra = "HYDRA" in n
    kraken = "KRAKEN" in n

    if serpent:
        px, rows, half = px * 6 / 7, 5, 9
    else:
        rows, half = 7, 6
    density = 74 if hulking else 62
    base_op = 0.7 if ghostly else 1.0

    out, s = [], seed * 48271 % 2147483647 or 7
    grid = []
    for r in range(rows):
        row = []
        for c in range(half):
            s = (s * 48271) % 2147483647
            hit = (s >> 7) % 100 < (density if 1 <= r <= rows - 2 else 38)
            if ghostly and r == rows - 1 and c % 2 == 0:
                hit = False        # tattered, floating hem
            row.append(hit)
        grid.append(row)
    W2 = 2 * half
    for r in range(rows):
        for c in range(half):
            if grid[r][c]:
                op = (0.55 + 0.4 * (((seed + r * half + c) * 2654435761 >> 8) % 100) / 100) * base_op
                for cx in (c, W2 - 1 - c):
                    out.append(f'<rect x="{f(x + cx * px)}" y="{f(y + r * px)}" width="{px - 1}" height="{px - 1}" fill="{AMBER}" opacity="{f(op)}"/>')

    def cell(cx, cy_, op=0.6):
        out.append(f'<rect x="{f(x + cx * px)}" y="{f(y + cy_ * px)}" width="{px - 1}" height="{px - 1}" fill="{AMBER}" opacity="{f(op)}"/>')

    if winged:
        for side, edge in ((-1, -1), (1, W2)):
            for i in range(3):
                cell(edge + side * i, 2.2 - i * 0.9, op=0.45)
        cell(2, -1, op=0.85)
        cell(W2 - 3, -1, op=0.85)
    if hulking:
        cell(-1, 1.5, op=0.8)
        cell(W2, 1.5, op=0.8)
    if kraken:
        for i, tc in enumerate((0.5, 3, 5.5, 8, 10.5)):
            for d in range(2 + (i + seed) % 3):
                cell(tc, rows + d * 0.9, op=0.4)
    if ghostly:
        ey = y + 2 * px
        out.append(f'<rect x="{f(x + 3 * px)}" y="{f(ey)}" width="{px - 2}" height="{px - 2}" fill="none" stroke="{AMBER}" stroke-width="1.4"/>')
        out.append(f'<rect x="{f(x + 8 * px)}" y="{f(ey)}" width="{px - 2}" height="{px - 2}" fill="none" stroke="{AMBER}" stroke-width="1.4"/>')
    elif hydra:
        for hc in (1, 5, 9):
            cell(hc, -1.6, op=0.9)
            cell(hc, -0.8, op=0.9)
            out.append(f'<rect x="{f(x + hc * px + 1.5)}" y="{f(y - 1.3 * px)}" width="3" height="3" fill="#EDE6D6"/>')
    else:
        ey = y + (1 if serpent else 2) * px
        e1, e2 = (3, half + 1) if serpent else (3, 8)
        out.append(f'<rect x="{f(x + e1 * px)}" y="{f(ey)}" width="{px - 2}" height="{px - 2}" fill="#EDE6D6"/>')
        out.append(f'<rect x="{f(x + e2 * px)}" y="{f(ey)}" width="{px - 2}" height="{px - 2}" fill="#EDE6D6"/>')
    return "".join(out)


def render_boss(_user=None):
    W, H = 404, 190
    st = _gh_json("data/games/boss.json")
    hp, mx = st["hp"], st["max_hp"]
    frac = max(hp, 0) / mx
    enraged = frac < 0.2
    css, out = [], [module_box(W, H, "Raid boss", f"Boss #{st['boss_num']}" + (" · enraged" if enraged else ""), CORAL)]
    css.append("@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}")
    out.append(f'<rect x="13" y="39" width="92" height="113" rx="5" fill="{PANEL}" stroke="{LINE}"/>')
    out.append(f'<g style="animation:bob {"1.1" if enraged else "2.6"}s ease-in-out infinite">{_boss_sprite(31, 74, st["boss_num"], st["name"], px=4.5)}</g>')
    out.append(f'<text x="120" y="48" font-size="13" font-weight="700" fill="{WHITE}">{st["name"]}</text>')
    out.append(f'<rect x="120" y="60" width="266" height="11" rx="2" fill="{BARBG}"/>')
    css.append("@keyframes hpin{from{transform:scaleX(0)}to{transform:scaleX(1)}}")
    hp_fill = "#FF796E" if enraged else CORAL
    css.append("@keyframes rage{0%,100%{opacity:1}50%{opacity:.55}}")
    rage = "animation:hpin .8s cubic-bezier(.3,.6,.3,1) both, rage 1s ease-in-out infinite;" if enraged else "animation:hpin .8s cubic-bezier(.3,.6,.3,1) both;"
    out.append(f'<rect x="120" y="60" width="{f(266 * frac)}" height="11" rx="2" fill="{hp_fill}" style="{rage}transform-origin:120px 0"/>')
    out.append(f'<text x="120" y="88" font-size="11" fill="{SLATE}"><tspan fill="{AMBER}">{max(hp,0):,}</tspan> / {mx:,} hp</text>')
    top = sorted(st["damage"].items(), key=lambda kv: -kv[1])[:3]
    ry = 112
    for name, dmg in top:
        out.append(f'<text x="120" y="{ry}" font-size="10" fill="{SLATE}">{name[:20]} <tspan fill="{AMBER}">{dmg:,}</tspan></text>')
        ry += 16
    if not top:
        out.append(f'<text x="120" y="112" font-size="10" fill="{SLATE2}">nobody has struck it yet</text>')
    out.append(f'<text x="14" y="{H - 12}" font-size="10" fill="{SLATE2}">attack once per hour · {len(st["slain"])} slain before it</text>')
    label = f"Raid boss #{st['boss_num']}, {st['name']}: {max(hp,0):,} of {mx:,} hp. Attack it by opening the pre-filled issue."
    return shell(W, H, css, "".join(out), label)


PET_SPRITES = {
    "egg":      ["..xxxx..", ".xxxxxx.", "xxxOxxxx", "xxxxxxxx", ".xxxxxx.", "..xxxx.."],
    "blobling": ["..xxxx..", ".xxxxxx.", ".xExxEx.", "xxxxxxxx", "xxxxxxxx", ".xxxxxx."],
    "blob":     ["..xxxx..", ".xxxxxx.", "xxExxExx", "xxxxxxxx", "xxxxxxxx", ".xxxxxx.", "d.d..d.d"],
}


def render_pet(_user=None):
    W, H = 404, 190
    st = _gh_json("data/games/pet.json")
    total = st["total_care"]
    stage = "egg" if total < 10 else ("blobling" if total < 50 else "blob")
    hungry, sad = st["hunger"] > 75, st["mood"] < 30
    css, out = [], [module_box(W, H, f"{st['name']} the README pet", stage, AMBER)]
    out.append(f'<rect x="13" y="39" width="100" height="113" rx="5" fill="{PANEL}" stroke="{LINE}"/>')
    css.append("@keyframes squish{0%,100%{transform:scale(1,1)}50%{transform:scale(1.07,.9)}}")
    css.append("@keyframes blink{0%,92%,100%{opacity:1}95%{opacity:0}}")
    px = 9
    sprite = []
    for r, row in enumerate(PET_SPRITES[stage]):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            x0, y0 = 24 + c * px, 58 + r * px
            if ch == "x":
                sprite.append(f'<rect x="{x0}" y="{y0}" width="{px - 1}" height="{px - 1}" fill="{AMBER}" opacity="{f(0.85 if (r + c) % 2 else 0.7)}"/>')
            elif ch == "O":
                sprite.append(f'<rect x="{x0}" y="{y0}" width="{px - 1}" height="{px - 1}" fill="#EDE6D6" opacity=".8"/>')
            elif ch == "E":
                sprite.append(f'<g style="animation:blink 4s linear infinite"><rect x="{x0}" y="{y0 + (2 if sad else 0)}" width="{px - 1}" height="{px - 1}" fill="#EDE6D6"/></g>')
            elif ch == "d":
                sprite.append(f'<rect x="{x0 + 2}" y="{y0 - 2}" width="{px - 5}" height="{px - 3}" fill="{AMBER}" opacity=".4"/>')
    if hungry and stage != "egg":
        sprite.append(f'<rect x="{24 + 3 * px}" y="{58 + 4 * px - 3}" width="{2 * px - 1}" height="3" fill="#05070A"/>')
    speed = "3.4" if sad or hungry else "1.8"
    base_h = len(PET_SPRITES[stage]) * px + 58
    out.append(f'<g style="animation:squish {speed}s ease-in-out infinite;transform-origin:{24 + 4 * px}px {base_h}px">{"".join(sprite)}</g>')

    def bar(y, lbl, val, color):
        return (
            f'<text x="130" y="{y + 9}" font-size="11" fill="{SLATE}">{lbl}</text>'
            f'<rect x="180" y="{y}" width="162" height="9" rx="2" fill="{BARBG}"/>'
            f'<rect x="180" y="{y}" width="{f(162 * val / 100)}" height="9" rx="2" fill="{color}"/>'
            f'<text x="383" y="{y + 9}" text-anchor="end" font-size="11" fill="{color}">{val}%</text>'
        )
    out.append(bar(52, "Food", 100 - st["hunger"], AMBER))
    out.append(bar(76, "Mood", st["mood"], MINT))
    times = "time" if total == 1 else "times"
    people = "person" if len(st["care"]) == 1 else "people"
    out.append(f'<text x="130" y="112" font-size="10" fill="{SLATE2}">cared for {total} {times} by {len(st["care"])} {people}</text>')
    if st.get("last_care_by"):
        out.append(f'<text x="130" y="128" font-size="10" fill="{SLATE2}">last looked after by {st["last_care_by"][:24]}</text>')
    status_txt = "starving, feed it!" if hungry else ("sulking, pet it" if sad else "doing okay")
    out.append(f'<text x="14" y="{H - 12}" font-size="10" fill="{SLATE2}">{status_txt} · everyone shares one pet</text>')
    label = f"{st['name']} the readme pet, a communal {stage}: food {100 - st['hunger']} percent, mood {st['mood']} percent, {status_txt}."
    return shell(W, H, css, "".join(out), label)


CANVAS_COLORS = {"a": AMBER, "w": WHITE, "s": "#788897"}


def _grid_labels(gx, gy, cols, rows_, cell):
    """coordinate labels every 4th column and row, for aiming plays.
    Player-facing coordinates are 1-based; state stays 0-based."""
    out = []
    for c in range(0, cols, 4):
        out.append(f'<text x="{gx + c * cell + cell / 2 - 1}" y="{gy - 4}" font-size="7" fill="{SLATE2}" text-anchor="middle">{c + 1}</text>')
    for r in range(0, rows_, 4):
        out.append(f'<text x="{gx - 6}" y="{gy + r * cell + cell / 2 + 2}" font-size="7" fill="{SLATE2}" text-anchor="end">{r + 1}</text>')
    return "".join(out)


def render_canvas(_user=None):
    W = 830
    st = _gh_json("data/games/canvas.json")
    cols, rows_, cell = 64, 16, 12
    gx, gy = (W - cols * cell) // 2 + 4, 50
    H = gy + rows_ * cell + 34
    css, out = [], [module_box(W, H, "Pixel canvas", "64 × 16", BLUE)]
    out.append(_grid_labels(gx, gy, cols, rows_, cell))
    for r in range(rows_):
        for c in range(cols):
            color = st["cells"].get(f"{c},{r}")
            fill = CANVAS_COLORS.get(color, "#272936" if (c + r) % 2 else "#2B2E3B")
            out.append(f'<rect x="{gx + c * cell}" y="{gy + r * cell}" width="{cell - 1}" height="{cell - 1}" rx="1" fill="{fill}"/>')
    px_word = "pixel" if st["count"] == 1 else "pixels"
    out.append(f'<text x="18" y="{H - 12}" font-size="10" fill="{SLATE2}">{st["count"]} {px_word} placed · grid is 64 x 16 · one pixel per 15 minutes</text>')
    label = f"Communal pixel canvas, 64 by 16, {st['count']} pixels placed so far."
    return shell(W, H, css, "".join(out), label)


def render_life(_user=None):
    W = 830
    st = _gh_json("data/games/life.json")
    cols, rows_, cell = 64, 16, 12
    gx, gy = (W - cols * cell) // 2 + 4, 50
    H = gy + rows_ * cell + 34
    css, out = [], [module_box(W, H, "Life garden", "One generation per hour", MINT)]
    out.append(_grid_labels(gx, gy, cols, rows_, cell))
    live = {(c, r) for c, r in st["cells"]}
    css.append("@keyframes lifein{from{opacity:0}to{opacity:1}}")
    for r in range(rows_):
        for c in range(cols):
            if (c, r) in live:
                d = f"animation:lifein .5s both;animation-delay:{f(((c * 7 + r * 13) % 20) * 0.03)}s"
                out.append(f'<rect x="{gx + c * cell}" y="{gy + r * cell}" width="{cell - 1}" height="{cell - 1}" rx="1" fill="{MINT}" style="{d}"/>')
            else:
                out.append(f'<rect x="{gx + c * cell}" y="{gy + r * cell}" width="{cell - 1}" height="{cell - 1}" rx="1" fill="#252933"/>')
    alive = len(st["cells"])
    quiet = " · the garden is quiet, plant something" if alive < 6 else ""
    cells_word = "cell" if alive == 1 else "cells"
    out.append(f'<text x="18" y="{H - 12}" font-size="10" fill="{SLATE2}">generation {st["generation"]} · {alive} {cells_word} alive · {st["planted"]} planted by visitors{quiet}</text>')
    label = f"Communal Conway's Game of Life garden: generation {st['generation']}, {alive} cells alive."
    return shell(W, H, css, "".join(out), label)


def render_fallback(w, h):
    out = [frame(w, h)]
    out.append(f'<text x="{w / 2}" y="{h / 2 + 4}" font-size="11" fill="{SLATE2}" text-anchor="middle">stats are napping · back in a minute</text>')
    return shell(w, h, [], "".join(out), "Live stats temporarily unavailable.")


# name: (renderer, width, height, needs_github_fetch, cache_seconds)
CARDS = {
    "stats": (render_stats, 830, 194, True, 600),
    "streaks": (render_streaks, 268, 170, True, 600),
    "weekdays": (render_weekdays, 268, 170, True, 600),
    "langs": (render_langs, 268, 170, True, 600),
    "footer": (render_footer, 900, 44, True, 600),
    "visitors": (render_visitors, 830, 64, False, 0),
    "guestbook": (render_guestbook, 830, 236, False, 30),
    "boss": (render_boss, 404, 190, False, 15),
    "pet": (render_pet, 404, 190, False, 15),
    "canvas": (render_canvas, 830, 268, False, 15),
    "life": (render_life, 830, 268, False, 15),
}


def render_card(name):
    """returns (svg, cache_seconds). Falls back to a styled card on any error."""
    fn, w, h, needs_gh, cache = CARDS[name]
    try:
        return fn(fetch() if needs_gh else None), cache
    except Exception:
        return render_fallback(w, h), 60
