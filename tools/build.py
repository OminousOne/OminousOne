#!/usr/bin/env python3
"""
build.py generates every SVG asset for the profile README.

No JavaScript, no GIFs: each graphic is a single SVG whose animation is baked
into CSS keyframes, which GitHub preserves inside <img>-embedded SVGs.

Outputs:
  assets/hero-header.svg   pixel wordmark strip
  assets/header-*.svg      animated tiles for the six featured projects
  assets/launch-*.svg      project cards for the grid in the Projects section
  assets/story.svg         the timeline above the story section

The stat cards are NOT built here: they are rendered live from the GitHub API
by the Vercel functions in api/ (see api/_render.py).

Usage:  python3 tools/build.py [--shift SECONDS]
        --shift is a dev flag: it fast-forwards every animation so a headless
        browser screenshot can capture any moment of a loop.
"""

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AMBER = "#FFC164"
WHITE = "#F6E9D0"
SLATE = "#C0B7AD"
SLATE2 = "#A79E95"
LINE = "#38313C"
PANEL = "#19161D"
SCREEN = "#111017"
BG = "#211B24"
BARBG = "#372E3A"

MONO = "ui-monospace,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

# the page cold-boots: the header plays a terminal initialization sequence
# and every other graphic stays dark until this moment, then flickers alive
BOOT = 4.8


def f(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


# ------------------------------------------------------------- pixel font

FONT = {
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    " ": ["00000"] * 7,
}


def pixel_text(text, x, y, u, fill, cls_prefix=None):
    out = []
    for ci, ch in enumerate(text):
        glyph = FONT[ch]
        cls = f' class="{cls_prefix}{ci}"' if cls_prefix else ""
        rects = []
        for r, row in enumerate(glyph):
            for c, bit in enumerate(row):
                if bit == "1":
                    rects.append(
                        f'<rect x="{f(x + ci * 6 * u + c * u)}" y="{f(y + r * u)}" '
                        f'width="{f(u * 0.86)}" height="{f(u * 0.86)}"/>'
                    )
        if rects:
            out.append(f'<g fill="{fill}"{cls}>' + "".join(rects) + "</g>")
    return "".join(out)


def pixel_width(text, u):
    return len(text) * 6 * u - u


# ------------------------------------------------------------- svg shell

def shell(w, h, css, body, label, shift=None, hold=BOOT, overlay=True, gutter=4, view_box=True):
    dev = f"<style>*{{animation-delay:-{f(shift)}s !important}}</style>" if shift else ""
    scan = f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="8" fill="url(#scan)" opacity="0.10"/>' if overlay else ""
    if hold:
        css = list(css)
        css.append("@keyframes bootrev{0%{opacity:0}30%{opacity:.8}55%{opacity:.15}100%{opacity:1}}")
        # the scanline overlay hides with the body, or it ghosts during boot
        body = f'<g style="animation:bootrev .5s linear both;animation-delay:{f(hold)}s">{body}{scan}</g>'
        scan = ""
    width = w + 2 * gutter
    dimensions = f'width="{width}" height="{h}" viewBox="{-gutter} 0 {width} {h}"' if view_box else f'height="{h}"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" {dimensions} role="img" aria-label="{label}">
<style><![CDATA[
text{{font-family:{MONO};}}
{chr(10).join(css)}
@media (prefers-reduced-motion:reduce){{*{{animation:none !important;}}}}
]]></style>
{dev}
<defs>
  <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
    <feGaussianBlur stdDeviation="1.8" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="scan" width="3" height="3" patternUnits="userSpaceOnUse">
    <rect width="3" height="1" y="2" fill="#000"/>
  </pattern>
</defs>
{body}
{scan}
</svg>"""


def frame(w, h, rx=10):
    return f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx}" fill="{BG}" stroke="#51444F" stroke-width="1.5"/>'


def module_box(x, y, w, h, title, status, accent=AMBER):
    return (
        f'<rect x="{x + 0.75}" y="{y + 0.75}" width="{w - 1.5}" height="{h - 1.5}" rx="8" '
        f'fill="{PANEL}" stroke="#51444F" stroke-width="1.5"/>'
        f'<path d="M{x + 12} {y + 28}h{w - 24}" stroke="{LINE}"/>'
        f'<path d="M{x + 12} {y + 28}h26" stroke="{accent}" stroke-width="1.5"/>'
        f'<text x="{x + 12}" y="{y + 20}" font-size="12" font-weight="700" letter-spacing=".8" fill="{accent}">{title}</text>'
        f'<text x="{x + w - 12}" y="{y + 20}" font-size="9" fill="{SLATE2}" text-anchor="end">{status}</text>'
    )


# ------------------------------------------------------------- hero modules
# each returns (body, css). coordinates are absolute; p = unique class prefix.

def mod_reciped(x, y, w, h):
    accent = "#FFAD92"
    css, out = [], [module_box(x, y, w, h, "RECIPED", "FLAGSHIP", accent)]
    bars = [("import", 0.86, 0.0), ("parse", 0.76, 0.9), ("cook", 0.44, 1.8)]
    bw = w - 96
    for i, (label, fill_to, delay) in enumerate(bars):
        by = y + 44 + i * 30
        p = f"rcp{i}"
        out.append(f'<text x="{x + 12}" y="{by + 8}" font-size="10.5" fill="{SLATE}">{label}</text>')
        out.append(f'<rect x="{x + 62}" y="{by}" width="{bw}" height="8" rx="2" fill="{BARBG}"/>')
        out.append(
            f'<rect x="{x + 62}" y="{by}" width="{bw}" height="8" rx="2" fill="{accent}" opacity="0.9" '
            f'class="{p}" style="transform:scaleX({f(fill_to)});transform-origin:{x + 62}px 0"/>'
        )
        css.append(
            f"@keyframes {p}{{0%{{transform:scaleX(0)}}"
            f"{f(8 + delay * 6)}%{{transform:scaleX(0)}}"
            f"{f(34 + delay * 6)}%{{transform:scaleX({f(fill_to)})}}"
            f"88%{{transform:scaleX({f(fill_to)})}}96%,100%{{transform:scaleX(0)}}}}"
        )
        css.append(f".{p}{{animation:{p} 10s cubic-bezier(.3,.6,.3,1) infinite;}}")
    css.append("@keyframes rcpcur{0%,49%{opacity:1}50%,100%{opacity:0}}")
    out.append(
        f'<rect x="{x + 62}" y="{y + 134}" width="6" height="11" fill="{accent}" '
        f'style="animation:rcpcur 1.1s steps(1) infinite"/>'
    )
    out.append(f'<text x="{x + 12}" y="{y + 144}" font-size="10" fill="{SLATE2}">next up</text>')
    return "".join(out), css


def mod_uschedule(x, y, w, h):
    accent = "#9AE6CB"
    css, out = [], [module_box(x, y, w, h, "USCHEDULE.CA", "LIVE ↗", accent)]
    css.append("@keyframes uspulse{0%,100%{opacity:1}50%{opacity:.2}}")
    out.append(f'<circle cx="{x + w - 60}" cy="{y + 15.5}" r="3" fill="{accent}" style="animation:uspulse 2s ease-in-out infinite"/>')
    gx, gy, cw, ch, gap = x + 12, y + 34, 45, 20, 3
    for c in range(5):
        out.append(f'<rect x="{f(gx + c * (cw + gap))}" y="{gy}" width="{cw}" height="{5 * (ch + gap) - gap}" fill="{SCREEN}" stroke="{LINE}"/>')
    blocks = [(0, 1, 2), (2, 0, 1), (1, 3, 2), (3, 1, 2), (4, 3, 1), (2, 2, 2), (0, 4, 1), (4, 0, 2)]
    for i, (c, r, span) in enumerate(blocks):
        p = f"usb{i}"
        t_on = 6 + i * 7
        css.append(
            f"@keyframes {p}{{0%,{t_on}%{{opacity:0}}{t_on + 4}%,86%{{opacity:1}}92%,100%{{opacity:0}}}}"
        )
        css.append(f".{p}{{animation:{p} 11s linear infinite;}}")
        out.append(
            f'<rect x="{f(gx + c * (cw + gap) + 3)}" y="{f(gy + r * (ch + gap) + 2)}" width="{cw - 6}" '
            f'height="{f(span * (ch + gap) - gap - 4)}" rx="2" fill="{accent}" fill-opacity="0.28" '
            f'stroke="{accent}" stroke-opacity="0.85" class="{p}" opacity="1"/>'
        )
    out.append(f'<text x="{x + 12}" y="{y + h - 12}" font-size="10" fill="{SLATE2}">a timetable assembling itself</text>')
    return "".join(out), css


def spark_path(seed, width, amp=6.0, step=8):
    vals, s = [], seed
    n = width // step
    for _ in range(n):
        s = (s * 1103515245 + 12345) % (2 ** 31)
        vals.append(((s >> 16) % 1000) / 1000.0 * amp * 2 - amp)
    pts = []
    for copy in range(2):
        for i, v in enumerate(vals):
            pts.append(f"{f(copy * width + i * step)},{f(v)}")
    pts.append(f"{f(2 * width)},{f(vals[0])}")
    return "M" + " L".join(pts)


def mod_polybot(x, y, w, h):
    accent = "#A7E393"
    css, out = [], [module_box(x, y, w, h, "POLYBOT", "PAPER ONLY", accent)]
    names = ["market-maker", "basket-arb", "btc-5m"]
    for i, name in enumerate(names):
        ry = y + 52 + i * 32
        p = f"pb{i}"
        css.append(f"@keyframes {p}led{{0%,100%{{opacity:1}}50%{{opacity:.15}}}}")
        out.append(f'<circle cx="{x + 18}" cy="{ry}" r="2.6" fill="{accent}" style="animation:{p}led {f(1.3 + i * 0.5)}s ease-in-out infinite"/>')
        out.append(f'<text x="{x + 28}" y="{ry + 3.5}" font-size="9" fill="{SLATE}">{name}</text>')
        sw = w - 122
        sx = x + 106
        css.append(f"@keyframes {p}s{{from{{transform:translateX(0)}}to{{transform:translateX(-{sw}px)}}}}")
        out.append(
            f'<clipPath id="{p}c"><rect x="{sx}" y="{ry - 12}" width="{sw}" height="24"/></clipPath>'
            f'<g clip-path="url(#{p}c)"><g transform="translate({sx},{ry})">'
            f'<path d="{spark_path(seed=11 + i * 7, width=sw)}" fill="none" stroke="{accent}" '
            f'stroke-width="1.1" opacity="0.7" style="animation:{p}s {f(14 + i * 4)}s linear infinite"/></g></g>'
        )
    out.append(f'<text x="{x + 12}" y="{y + h - 12}" font-size="10" fill="{SLATE2}">6 strategies, no real money</text>')
    return "".join(out), css


def mod_netcode(x, y, w, h):
    css, out = [], [module_box(x, y, w, h, "NETCODE", "60 TICK/S")]
    cx, cy, cw, ch = x + 12, y + 32, w - 24, h - 62
    out.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" fill="{SCREEN}" stroke="{LINE}"/>')
    out.append(f'<line x1="{f(cx + cw / 2)}" y1="{cy + 4}" x2="{f(cx + cw / 2)}" y2="{cy + ch - 4}" stroke="{LINE}" stroke-dasharray="3 5"/>')
    lx, rx_ = cx + 8, cx + cw - 12
    top, bot, mid = cy + 8, cy + ch - 8, cy + ch / 2
    css.append(
        f"@keyframes ncball{{0%{{transform:translate({f(lx + 6)}px,{f(mid + 18)}px)}}"
        f"25%{{transform:translate({f(cx + cw * 0.5)}px,{f(top)}px)}}"
        f"50%{{transform:translate({f(rx_ - 4)}px,{f(mid - 6)}px)}}"
        f"75%{{transform:translate({f(cx + cw * 0.42)}px,{f(bot)}px)}}"
        f"100%{{transform:translate({f(lx + 6)}px,{f(mid + 18)}px)}}}}"
    )
    css.append(".ncball{animation:ncball 5.2s linear infinite;}")
    out.append(f'<rect x="-2.5" y="-2.5" width="5" height="5" fill="{AMBER}" filter="url(#glow)" class="ncball" style="transform:translate({f(lx + 6)}px,{f(mid + 18)}px)"/>')
    css.append(
        f"@keyframes ncpl{{0%{{transform:translateY({f(mid + 18)}px)}}40%{{transform:translateY({f(mid - 10)}px)}}"
        f"100%{{transform:translateY({f(mid + 18)}px)}}}}"
    )
    css.append(
        f"@keyframes ncpr{{0%{{transform:translateY({f(mid + 14)}px)}}50%{{transform:translateY({f(mid - 6)}px)}}"
        f"100%{{transform:translateY({f(mid + 14)}px)}}}}"
    )
    css.append(".ncpl{animation:ncpl 5.2s ease-in-out infinite;}")
    css.append(".ncpr{animation:ncpr 5.2s ease-in-out infinite;}")
    css.append(".nclag{animation-delay:-4.9s;}")
    out.append(f'<rect x="{lx}" y="-10" width="4" height="20" rx="1" fill="{AMBER}" class="ncpl" style="transform:translateY({f(mid)}px)"/>')
    out.append(f'<rect x="{rx_}" y="-10" width="4" height="20" rx="1" fill="#FFAD92" class="ncpr" style="transform:translateY({f(mid)}px)"/>')
    out.append(
        f'<rect x="{rx_}" y="-10" width="4" height="20" rx="1" fill="none" stroke="{AMBER}" '
        f'stroke-dasharray="3 2" opacity="0.5" class="ncpr nclag" style="transform:translateY({f(mid)}px)"/>'
    )
    out.append(f'<text x="{x + 12}" y="{y + h - 12}" font-size="10" fill="{SLATE2}">prediction and reconciliation</text>')
    return "".join(out), css


def mod_factory(x, y, w, h):
    accent = "#DABAFB"
    css, out = [], [module_box(x, y, w, h, "SOFTWARE FACTORY", "AGENTS", accent)]
    my = y + 92
    mgr = (x + 20, my - 12, 46, 24)
    workers = [(x + 106, my - 52 + i * 40 - 9, 40, 18) for i in range(3)]
    rev = (x + 180, my - 12, 46, 24)

    def node(nx, ny, nw, nh, label, fs=9):
        return (
            f'<rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" rx="3" fill="{SCREEN}" stroke="#2A333C"/>'
            f'<text x="{f(nx + nw / 2)}" y="{f(ny + nh / 2 + 3)}" font-size="{fs}" fill="{SLATE}" text-anchor="middle">{label}</text>'
        )

    out.append(node(*mgr, "plan"))
    for i, wk in enumerate(workers):
        out.append(node(*wk, f"code {i + 1}"))
    out.append(node(*rev, "review"))
    out.append(f'<text x="{x + w - 16}" y="{f(my + 4)}" font-size="10" fill="{accent}" text-anchor="end" opacity="0.9">PR</text>')
    for i, wk in enumerate(workers):
        wy = wk[1] + 9
        out.append(f'<line x1="{mgr[0] + mgr[2]}" y1="{my}" x2="{wk[0]}" y2="{wy}" stroke="#232B33"/>')
        out.append(f'<line x1="{wk[0] + wk[2]}" y1="{wy}" x2="{rev[0]}" y2="{my}" stroke="#232B33"/>')
        p = f"sfp{i}"
        css.append(
            f"@keyframes {p}{{0%{{transform:translate({mgr[0] + mgr[2]}px,{my}px);opacity:0}}"
            f"4%{{opacity:1}}22%{{transform:translate({wk[0]}px,{wy}px)}}"
            f"46%{{transform:translate({wk[0] + wk[2]}px,{wy}px);opacity:1}}"
            f"64%{{transform:translate({rev[0]}px,{my}px);opacity:1}}68%{{opacity:0}}100%{{opacity:0}}}}"
        )
        css.append(f".{p}{{animation:{p} 5.4s linear infinite;animation-delay:{f(i * 1.1)}s;}}")
        out.append(f'<circle r="2.4" fill="{accent}" class="{p}" opacity="0"/>')
    css.append(
        f"@keyframes sfpr{{0%,66%{{opacity:0;transform:translate({rev[0] + rev[2]}px,{my}px)}}"
        f"72%{{opacity:1}}84%{{transform:translate({x + w - 26}px,{my}px);opacity:1}}88%,100%{{opacity:0}}}}"
    )
    css.append(".sfpr{animation:sfpr 5.4s linear infinite;}")
    out.append(f'<circle r="2.4" fill="{accent}" class="sfpr" opacity="0"/>')
    out.append(f'<text x="{x + 12}" y="{y + h - 12}" font-size="10" fill="{SLATE2}">agents that ship pull requests</text>')
    return "".join(out), css


# ------------------------------------------------------------- 3d globe
# real 3D, baked: rotate the sphere in Python, orthographically project each
# frame, clip the back hemisphere, and flash the frames with opacity keyframes.

TILT = math.radians(16)

CITIES = {
    "YOW": (45.3, -75.7), "YVR": (49.2, -123.2), "YYZ": (43.7, -79.6),
    "YUL": (45.5, -73.6), "YYC": (51.1, -114.0), "YHZ": (44.9, -63.5),
    "YFB": (63.8, -68.6),
}
ROUTES = [("YOW", "YVR"), ("YYZ", "YHZ"), ("YUL", "YFB"), ("YVR", "YYC")]


def _coast():
    return json.load(open(os.path.join(ROOT, "tools", "coastlines.json")))


def _proj(lat, lon, phi, r):
    """rotate by phi about the poles, tilt toward the viewer, project.
    returns (px, py, visible) with px/py relative to the globe centre."""
    la, lo = math.radians(lat), math.radians(lon) + phi
    x = math.cos(la) * math.sin(lo)
    y = math.sin(la)
    z = math.cos(la) * math.cos(lo)
    y2 = y * math.cos(TILT) - z * math.sin(TILT)
    z2 = y * math.sin(TILT) + z * math.cos(TILT)
    return x * r, -y2 * r, z2 > 0.02


def _chain(pts):
    """pts: [(px,py,vis)] -> compact path drawing only visible runs."""
    d, run = [], False
    for px, py, vis in pts:
        if vis:
            d.append(f"{'L' if run else 'M'}{round(px)},{round(py)}")
            run = True
        else:
            run = False
    path = "".join(d)
    return path if "L" in path else ""


def _gc_points(a, b, n, bulge=0.0):
    """great-circle samples between two (lat,lon) cities, optional altitude."""
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    v1 = (math.cos(la1) * math.cos(lo1), math.cos(la1) * math.sin(lo1), math.sin(la1))
    v2 = (math.cos(la2) * math.cos(lo2), math.cos(la2) * math.sin(lo2), math.sin(la2))
    dot = max(-1, min(1, sum(p * q for p, q in zip(v1, v2))))
    om = math.acos(dot)
    pts = []
    for i in range(n + 1):
        t = i / n
        s1 = math.sin((1 - t) * om) / math.sin(om)
        s2 = math.sin(t * om) / math.sin(om)
        v = [s1 * p + s2 * q for p, q in zip(v1, v2)]
        alt = 1 + bulge * math.sin(math.pi * t)
        lat = math.degrees(math.asin(max(-1, min(1, v[2] / math.hypot(*v)))))
        lon = math.degrees(math.atan2(v[1], v[0]))
        pts.append((lat, lon, alt))
    return pts


def globe(cx, cy, r, n_frames, dur, prefix, coast, meridian_step=45,
          coast_width=0.8, routes=ROUTES, dots=True):
    """returns (body, css) for a rotating baked-3D globe centred at cx,cy."""
    css, out = [], []
    out.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{r}" fill="{SCREEN}" stroke="#2A333C"/>')

    # parallels are invariant under spin: draw once
    static = []
    for lat in (-60, -30, 0, 30, 60):
        pts = [_proj(lat, lon, 0, r) for lon in range(0, 366, 6)]
        p = _chain(pts)
        if p:
            static.append(f'<path d="{p}" fill="none" stroke="{LINE}" stroke-width="0.7"/>')
    out.append(f'<g transform="translate({f(cx)},{f(cy)})">{"".join(static)}</g>')

    route_pts = [_gc_points(CITIES[a], CITIES[b], 18, bulge=0.07) for a, b in routes]

    frames = []
    for fi in range(n_frames):
        phi = 2 * math.pi * fi / n_frames
        el = []
        # meridians spin with the sphere
        mer = []
        for lon in range(0, 360, meridian_step):
            pts = [_proj(lat, lon, phi, r) for lat in range(-90, 92, 10)]
            p = _chain(pts)
            if p:
                mer.append(p)
        el.append(f'<path d="{"".join(mer)}" fill="none" stroke="{LINE}" stroke-width="0.7"/>')
        # coastlines
        coast_d = []
        for ring in coast:
            p = _chain([_proj(la, lo, phi, r) for lo, la in ring])
            if p:
                coast_d.append(p)
        el.append(f'<path d="{"".join(coast_d)}" fill="none" stroke="{AMBER}" stroke-opacity="0.55" stroke-width="{coast_width}" stroke-linejoin="round"/>')
        # flight arcs + planes
        arc_d, plane_d = [], []
        for ri, pts in enumerate(route_pts):
            proj = [_proj(la, lo, phi, r * alt) for la, lo, alt in pts]
            p = _chain(proj)
            if p:
                arc_d.append(p)
            if dots:
                pos = (fi / n_frames * 2 + ri * 0.25) % 1.0
                la, lo, alt = pts[round(pos * (len(pts) - 1))]
                px, py, vis = _proj(la, lo, phi, r * alt)
                if vis:
                    plane_d.append(f'<rect x="{round(px) - 1.5}" y="{round(py) - 1.5}" width="3" height="3" fill="{AMBER}"/>')
        if arc_d:
            el.append(f'<path d="{"".join(arc_d)}" fill="none" stroke="{AMBER}" stroke-opacity="0.8" stroke-width="0.9"/>')
        el += plane_d
        if dots:
            city_d = []
            for la, lo in CITIES.values():
                px, py, vis = _proj(la, lo, phi, r)
                if vis:
                    city_d.append(f'<circle cx="{round(px)}" cy="{round(py)}" r="1.3" fill="{WHITE}"/>')
            el.append(f'<g opacity="0.8">{"".join(city_d)}</g>')
        frames.append("".join(el))

    for fi, content in enumerate(frames):
        p = f"{prefix}f{fi}"
        t0, t1 = fi / n_frames * 100, (fi + 1) / n_frames * 100
        if fi == 0:
            css.append(f"@keyframes {p}{{0%{{opacity:1}}{f(t1 - 0.004)}%{{opacity:1}}{f(t1)}%{{opacity:0}}100%{{opacity:0}}}}")
            base = 1
        else:
            css.append(
                f"@keyframes {p}{{0%,{f(t0 - 0.004)}%{{opacity:0}}{f(t0)}%{{opacity:1}}"
                f"{f(t1 - 0.004)}%{{opacity:1}}{f(t1)}%{{opacity:0}}100%{{opacity:0}}}}"
            )
            base = 0
        css.append(f".{p}{{animation:{p} {f(dur)}s linear infinite;}}")
        out.append(f'<g transform="translate({f(cx)},{f(cy)})" class="{p}" opacity="{base}">{content}</g>')

    out.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{r}" fill="none" stroke="{AMBER}" stroke-opacity="0.25"/>')
    return "".join(out), css


def mod_atc(x, y, w, h):
    css, out = [], [module_box(x, y, w, h, "ATC SIMULATOR", "CYOW ↗", "#ADD8FF")]
    body, gcss = globe(x + w / 2, y + 92, 52, 210, 14, "atc", _coast())
    out.append(body)
    css += gcss
    out.append(f'<text x="{x + 12}" y="{y + h - 12}" font-size="10" fill="{SLATE2}">1,000 real flights on a globe</text>')
    return "".join(out), css


def mod_from_scene(x, y, w, h, title, status, caption, render):
    scene, css, accent, backdrop = render()
    body = f"""
{module_box(x, y, w, h, title, status, accent)}
<rect x="{x + 10}" y="{y + 36}" width="{w - 20}" height="{h - 64}" rx="4" fill="{backdrop}" stroke="{LINE}"/>
<g transform="translate({x} {y + 40}) scale({f(w / 438)})">{scene}</g>
<text x="{x + 12}" y="{y + h - 12}" font-size="10" fill="{SLATE2}">{caption}</text>
"""
    return body, css


def mod_oberon(x, y, w, h):
    return mod_from_scene(x, y, w, h, "OBERON", "MACOS", "one Git worktree per chat", oberon_scene)


def mod_worldmesh(x, y, w, h):
    return mod_from_scene(x, y, w, h, "WORLDMESH", "RUST", "one world across servers", worldmesh_scene)


def build_hero_header(shift=None):
    """Power on, check the project modules, and roll the unlock into the wordmark."""
    w, h = 900, 250
    confirm_delay = .15
    unlock_at, release_at = 3.14, 3.72
    css = [
        '@media (prefers-reduced-motion:reduce){.boot-only{display:none}}',
        '@keyframes pop{from{opacity:0}to{opacity:1}}',
        '@keyframes powerline{0%{opacity:.8;transform:scaleX(.03)}36%{opacity:1;transform:scaleX(1)}'
        '100%{opacity:0;transform:scaleX(1)}}',
        '@keyframes bootlog{0%{opacity:0;transform:translateX(-5px)}'
        '50%{opacity:.74;transform:translateX(1px)}100%{opacity:1;transform:translateX(0)}}',
        '@keyframes prompt{0%,100%{opacity:0}1%{opacity:1}77%{opacity:.45}}',
        '@keyframes check{0%,24%{opacity:1}49%{opacity:.64}100%{opacity:1}}',
        '@keyframes lamp-hit{0%{fill-opacity:.34}100%{fill-opacity:.12}}',
        '@keyframes scan-boot{0%{opacity:0;transform:translateY(0)}'
        '14%,74%{opacity:.075}100%{opacity:0;transform:translateY(140px)}}',
        '@keyframes raster-off{0%{opacity:1;transform:scaleY(1)}'
        '69%{opacity:.65;transform:scaleY(.11)}100%{opacity:0;transform:scaleY(.03)}}',
        '@keyframes approve{0%{opacity:0;transform:scale(.78)}'
        '31%{opacity:1;transform:scale(1.06)}67%{opacity:1;transform:scale(.99)}'
        '100%{opacity:1;transform:scale(1)}}',
        '@keyframes unlock-dim{0%,100%{opacity:0}14%,77%{opacity:.38}}',
        '@keyframes recoil{0%{transform:translate(0,0)}18%{transform:translate(-3px,2px)}'
        '41%{transform:translate(2px,-1px)}64%{transform:translate(-1px,0)}100%{transform:translate(0,0)}}',
        '@keyframes stamp-ring{0%{opacity:0;transform:scale(.94)}23%{opacity:.44}'
        '100%{opacity:0;transform:scale(1.09,1.35)}}',
        '@keyframes stamp-release{0%{opacity:1;transform:scaleY(1)}'
        '72%{opacity:1;transform:scaleY(.08)}100%{opacity:0;transform:scaleY(.02)}}',
        '@keyframes beam{0%{opacity:0;transform:translateY(0) scaleX(.52)}'
        '20%{opacity:.94;transform:translateY(-4px) scaleX(.94)}'
        '68%{opacity:.58;transform:translateY(-32px) scaleX(1)}'
        '100%{opacity:0;transform:translateY(-53px) scaleX(.95)}}',
        '@keyframes namein{0%{opacity:0;transform:translateY(3px);fill:#FFE7BB}'
        '18%{opacity:1;transform:translateY(-1px);fill:#FFE7BB}'
        f'36%{{opacity:.56;transform:translateY(0);fill:{AMBER}}}'
        f'65%,100%{{opacity:1;transform:translateY(0);fill:{AMBER}}}}}',
    ]
    copper, mint = "#F3A87F", "#9AE6CB"
    checks = [
        (0.17, "Phosphor array", "READY", AMBER, "M-18 2h8l5-10 8 16 6-10h9"),
        (0.56, "Reciped import pipeline", "ONLINE", copper, "M-10-12h15l5 5v19h-20zM-5-4h5m-5 5h10m-10 5h10"),
        (1.04, "Worldmesh entity groups", "LINKED", mint, "M-16 0 0-9l16 9L0 9zM-16 0h32M0-9V9"),
        (1.32, "Software Factory workers", "SPAWNED", "#D5ACF2", "M-16 0h7m5 0h7m5 0h7m-4-4 4 4-4 4M-9-5h5v10h-5zm12 0h5v10H3z"),
        (1.60, "Oberon worktree isolation", "READY", "#9BBCFF", "M-17 1h6l4-7 5 12 5-7h13M-17-10h34v20h-34z"),
        (2.14, "Arcade BLOB sensor", "SQUISH", AMBER, "M-12 7V-1h4v-5h4v-3h8v3h4v5h4v8zM-4 0v3m8-3v3"),
    ]
    logs, lamps = [], []
    progress_duration = unlock_at - .12
    progress = ['0%{transform:scaleX(0)}']
    for i, (at, name, status, accent, icon) in enumerate(checks):
        confirmed = at + confirm_delay
        next_at = checks[i + 1][0] if i + 1 < len(checks) else 2.77
        y = 67 + i * 24
        logs.append(f'<rect x="28" y="{y - 10}" width="6" height="11" rx="1" fill="{accent}" '
                    f'style="animation:prompt {f(next_at - at)}s step-end {f(at)}s both"/>')
        logs.append(f'<g style="animation:bootlog .08s steps(2) {f(at)}s both">'
                    f'<text x="43" y="{y}" font-size="14" fill="{WHITE}">&gt; {name}</text>'
                    f'<path d="M375 {y - 4}h68" stroke="{LINE}" stroke-dasharray="2 4"/>'
                    f'<text x="531" y="{y}" text-anchor="end" font-size="12" fill="{accent}" '
                    f'style="animation:pop .04s step-end {f(confirmed - .04)}s both">{status}</text></g>')
        x, lamp_y = 583 + (i % 3) * 86, 57 + (i // 3) * 60
        lamps.append(f'<rect x="{x}" y="{lamp_y}" width="76" height="49" rx="4" fill="{PANEL}" stroke="{LINE}"/>')
        lamps.append(f'<g opacity="0" style="animation:check .16s linear {f(confirmed)}s forwards">'
                     f'<rect x="{x}" y="{lamp_y}" width="76" height="49" rx="4" fill="{accent}" stroke="{accent}" '
                     f'stroke-opacity=".7" style="animation:lamp-hit .16s ease-out {f(confirmed)}s both"/>'
                     f'<path d="{icon}" transform="translate({x + 38} {lamp_y + 25})" fill="none" stroke="{accent}" stroke-width="1.5"/>'
                     f'<circle cx="{x + 64}" cy="{lamp_y + 11}" r="2" fill="{accent}"/></g>')
        progress.append(f'{f(100 * confirmed / progress_duration)}%{{transform:scaleX({f((i + 1) * .143)})}}')
    progress.append('90%{transform:scaleX(.858);animation-timing-function:cubic-bezier(.2,.8,.3,1)}')
    progress.append('100%{transform:scaleX(1)}')
    css.append('@keyframes loadboot{' + ''.join(progress) + '}')
    body = f"""
{frame(w, h)}
<rect x="9" y="9" width="882" height="232" rx="6" fill="{SCREEN}" stroke="{LINE}"/>
<path d="M27 33H873M27 209H873" stroke="{LINE}"/>
<text x="29" y="25" fill="{SLATE}" font-size="10" letter-spacing="1.5">OMINOUSONE.SYS</text>
<text x="871" y="25" text-anchor="end" fill="{SLATE2}" font-size="10" letter-spacing="1">PHOSPHOR TERMINAL</text>
<g class="boot-only">
  <g class="diagnostics" style="animation:pop .13s steps(2) .12s both,raster-off .19s ease-in 3.57s forwards;transform-origin:450px 124px">
    <rect x="27" y="44" width="846" height="12" fill="{AMBER}" opacity="0"
          style="animation:scan-boot 1.15s linear .31s 2 both"/>
    <path d="M551 44v151" stroke="{LINE}"/>
    {''.join(logs)}{''.join(lamps)}
    <text x="583" y="192" fill="{SLATE}" font-size="11">Checking project modules</text>
    <rect x="30" y="221" width="840" height="4" rx="2" fill="{BARBG}"/>
    <rect x="30" y="221" width="840" height="4" rx="2" fill="{AMBER}"
          style="animation:loadboot {f(progress_duration)}s step-end both;transform-origin:30px 223px"/>
  </g>
  <rect x="27" y="123" width="846" height="2.5" fill="{WHITE}" filter="url(#glow)" opacity="0"
        style="animation:powerline .34s cubic-bezier(.18,.76,.26,1) both;transform-origin:450px 124px"/>
  <rect x="21" y="37" width="858" height="198" rx="4" fill="{SCREEN}" opacity="0"
        style="animation:unlock-dim .64s ease-out {f(unlock_at)}s both"/>
  <rect x="226" y="88" width="448" height="72" rx="5" fill="none" stroke="{AMBER}" opacity="0"
        style="animation:stamp-ring .28s ease-out {f(unlock_at + .04)}s both;transform-origin:450px 124px"/>
  <g style="animation:stamp-release .17s cubic-bezier(.7,.05,.9,.35) {f(release_at)}s both;transform-origin:450px 124px">
    <g style="animation:recoil .16s linear {f(unlock_at + .04)}s both">
      <g opacity="0" style="animation:approve .16s ease-out {f(unlock_at)}s both;transform-origin:450px 124px">
        <rect x="226" y="88" width="448" height="72" rx="5" fill="{SCREEN}" stroke="{AMBER}" stroke-width="1.7"/>
        <path d="M240 112v-10h16m388 0h16v10m0 24v10h-16m-388 0h-16v-10" fill="none" stroke="{AMBER}"/>
        <text x="450" y="133" text-anchor="middle" fill="{AMBER}" font-size="23" font-weight="700"
              letter-spacing="4" filter="url(#glow)">ACCESS GRANTED</text>
      </g>
    </g>
  </g>
  <rect x="27" y="123" width="846" height="2" rx="1" fill="{AMBER}" opacity="0" filter="url(#glow)"
        style="animation:beam .34s ease-out {f(release_at + .14)}s both;transform-origin:450px 124px"/>
</g>
"""
    name = "JULIEN DEWOLFE"
    unit = 5.7
    x = (w - pixel_width(name, unit)) / 2
    # The sweep ignites the lettering from the center toward the edges.
    center = (len(name) - 1) / 2
    for i in range(len(name)):
        delay = release_at + .2 + .03 * abs(i - center)
        css.append(f'.wm{i}{{animation:namein .32s linear {f(delay)}s both}}')
    body += f"""
<g filter="url(#glow)">{pixel_text(name, x, 79, unit, AMBER, cls_prefix="wm")}</g>
<g style="animation:pop .1s ease-out 4.48s both">
  <text x="450" y="153" text-anchor="middle" fill="{WHITE}" font-size="15">swe intern @ gadget.dev · software engineering @ uOttawa</text>
  <path d="M413 176h74" stroke="{AMBER}" stroke-opacity=".5"/>
</g>
<g style="animation:pop .01s linear {f(BOOT)}s both">
  <circle cx="33" cy="225" r="3.5" fill="{mint}"/>
  <text x="45" y="229" font-size="12" fill="{SLATE}">boot complete in {BOOT:.1f}s</text>
  <text x="871" y="229" text-anchor="end" font-size="11" fill="{SLATE2}">refresh to reboot</text>
</g>
"""
    return shell(w, h, css, body, "Boot terminal. Project checks come online, access is granted, "
                 "then the terminal reveals Julien DeWolfe, software engineering intern at Gadget and student at uOttawa.", shift, hold=0)

HERO_MODULES = [
    ("mod-reciped", mod_reciped, "Reciped: animated recipe import, parse, and cook steps. Links to the Reciped section below."),
    ("mod-oberon", mod_oberon, "Oberon: animated Pit Wall with agent activity and pull requests. Links to the Oberon project."),
    ("mod-worldmesh", mod_worldmesh, "Worldmesh: an entity moves through a world simulated across servers. Links to the docs."),
    ("mod-uschedule", mod_uschedule, "uschedule.ca: a timetable assembling itself. Links to uschedule.ca."),
    ("mod-atc", mod_atc, "ATC simulator: a rotating 3D globe with Canadian flight routes. Links to the live simulator."),
    ("mod-factory", mod_factory, "Software Factory: work flowing from plan through code to review and a PR. Links to the Software Factory section below."),
    # Keep generating the images used by older versions of the README.
    ("mod-polybot", mod_polybot, "Polybot: three trading strategy sparklines. Links to the Polybot section below."),
    ("mod-netcode", mod_netcode, "Netcode: a miniature multiplayer Pong court. Links to the netcode section below."),
]


def build_hero_modules(shift=None):
    pieces = {}
    for i, (name, fn, label) in enumerate(HERO_MODULES):
        body, css = fn(0, 0, 268, 170)
        # power-on: after the boot terminal finishes, the board boots left to
        # right, each module flickering alive like a CRT warming up
        delay = BOOT + 0.1 + i * 0.16
        css = list(css)
        css.append(
            "@keyframes pwr{0%{opacity:0}18%{opacity:.85}38%{opacity:.15}"
            "62%{opacity:1}100%{opacity:1}}"
        )
        body = (
            f'<g style="animation:pwr .55s linear both;animation-delay:{f(delay)}s">{body}</g>'
        )
        pieces[name] = shell(268, 170, css, body, label, shift, hold=0)
    return pieces


# ------------------------------------------------------------- header tiles

def header_tile(title, action, accent, backdrop, art, css, label, index, shift, linked=True):
    width, height = 268, 170
    delay = BOOT + 0.1 + index * 0.08
    link_mark = f'<path d="M241 154h13m-5-4 5 4-5 4" fill="none" stroke="{accent}" stroke-width="1.2"/>'
    body = f"""
{frame(width, height, rx=8)}
<rect x="9" y="34" width="250" height="107" rx="4" fill="{backdrop}" stroke="{accent}" stroke-opacity=".38"/>
<path d="M10 40v-5h22m204 105h22v-5" fill="none" stroke="{accent}" stroke-opacity=".68"/>
<text x="13" y="23" font-size="15" font-weight="700" fill="{WHITE}">{title}</text>
<g style="--art-start:{f(delay)}s">{art}</g>
<text x="13" y="158" font-size="10.5" fill="{accent}">{action}</text>
{link_mark if linked else ''}
"""
    return shell(width, height, css, body, label, shift, hold=delay)


def header_reciped():
    coral, cream = "#FFA98F", "#F6E4CD"
    css = [
        '@keyframes receipt{0%,16%,100%{transform:translateY(-5px);opacity:.72}'
        '42%,87%{transform:translateY(0);opacity:1}}',
        '@keyframes recipe-link{0%,12%{transform:translateX(0);opacity:0}'
        '20%{opacity:1}54%,100%{transform:translateX(46px);opacity:0}}',
    ]
    art = f"""
<rect x="25" y="59" width="67" height="49" rx="5" fill="#542832" stroke="#95594F"/>
<path d="M25 68h67" stroke="#8C554D"/>
<path d="M52 78l14 7-14 7z" fill="{coral}"/>
<path d="M97 85h43" stroke="{coral}" stroke-dasharray="2 4" opacity=".55"/>
<circle cx="97" cy="85" r="3" fill="{coral}" opacity="0" style="animation:recipe-link 5.5s linear var(--art-start) infinite"/>
<g style="animation:receipt 5.5s ease-out var(--art-start) infinite">
  <path d="M145 46h64l14 14v68l-5-3-5 3-5-3-5 3-5-3-5 3-5-3-5 3-5-3-5 3-5-3-5 3-5-3-5 3-5-3z" fill="{cream}"/>
  <path d="M209 46v14h14" fill="none" stroke="#AA7864"/>
  <text x="154" y="70" font-size="10" font-weight="700" fill="#713841">RECIPE</text>
  <path d="M154 76h57m-48 9h45m-45 8h33m-42 9h57m-57 8h46" stroke="#B28776"/>
  <path d="M154 85h4m-4 8h4" stroke="#9D4F53" stroke-width="1.6"/>
</g>
"""
    return "Reciped", "Explore the recipe app", coral, "#34202A", art, css, "Reciped. A cooking video is imported and turned into a recipe."


def header_oberon():
    gold, lilac = "#F6C881", "#D2AFF6"
    css = ['@keyframes worktree-pulse{0%,100%{transform:translate(0,0);opacity:0}'
           '14%{opacity:1}46%{transform:translate(45px,0)}'
           '73%{transform:translate(89px,-28px);opacity:1}85%{opacity:0}}']
    art = f"""
<path d="M32 87h79c18 0 20-28 47-28h21M111 87c18 0 20 29 47 29h21" fill="none" stroke="#958097" stroke-width="2"/>
<path d="M32 87h79" stroke="{gold}" stroke-width="2"/>
<circle cx="48" cy="87" r="4" fill="{gold}"/><circle cx="84" cy="87" r="3" fill="{gold}"/>
<circle cx="89" cy="87" r="3.2" fill="{gold}" opacity="0" style="animation:worktree-pulse 5s ease var(--art-start) infinite"/>
<circle cx="149" cy="60" r="3.3" fill="{lilac}"/><circle cx="149" cy="115" r="3.3" fill="{lilac}"/>
<text x="31" y="108" font-size="10" fill="{gold}">main</text>
<rect x="177" y="46" width="66" height="25" rx="4" fill="#392B48" stroke="#755B90"/>
<rect x="177" y="103" width="66" height="25" rx="4" fill="#392B48" stroke="#755B90"/>
<g font-size="10" fill="{lilac}"><text x="187" y="62">Codex</text><text x="187" y="119">Claude</text></g>
<path d="M102 103v11" stroke="#8B738E" stroke-dasharray="2 3"/>
<text x="101" y="128" text-anchor="middle" font-size="9" fill="#C2AFC9">Git worktrees</text>
"""
    return "Oberon", "Native macOS agent workspace", gold, "#251F2E", art, css, "Oberon. Codex and Claude chats run in separate Git worktrees."


def header_worldmesh():
    mint, gold = "#8CE7D0", "#F2C887"
    css = [
        '@keyframes mesh-send{0%,13%{transform:translate(0,0)}40%{transform:translate(63px,0)}'
        '69%{transform:translate(122px,0)}85%,100%{transform:translate(0,0)}}',
        f'@keyframes mesh-owner{{0%,40%,90%,100%{{fill:{mint}}}45%,85%{{fill:{gold}}}}}',
    ]
    art = f"""
<circle cx="134" cy="88" r="42" fill="#173436" stroke="#4D8B83"/>
<ellipse cx="134" cy="88" rx="19" ry="42" fill="none" stroke="#416D68"/>
<path d="M93 88h82m-74-21q33 22 66 0m-66 42q33-22 66 0" fill="none" stroke="#416D68"/>
<path d="M55 88h158" stroke="{mint}" stroke-opacity=".62" stroke-dasharray="3 4"/>
<g fill="#234744" stroke="#72A49D">
  <rect x="23" y="67" width="29" height="35" rx="3"/><rect x="216" y="67" width="29" height="35" rx="3"/>
</g>
<path d="M28 76h19m-19 8h19m-19 8h19m174-16h19m-19 8h19m-19 8h19" stroke="#9ACFC4"/>
<g font-size="9.5" text-anchor="middle">
  <text x="38" y="120" fill="{mint}">Group A</text><text x="230" y="120" fill="{gold}">Group B</text>
</g>
<circle cx="73" cy="88" r="4" fill="{mint}" stroke="#E7F6E9" stroke-width="1"
  style="animation:mesh-send 5s ease-in-out var(--art-start) infinite, mesh-owner 5s steps(1) var(--art-start) infinite"/>
"""
    return "Worldmesh", "Read the networking docs", mint, "#142D2E", art, css, "Worldmesh. An entity is handed between server groups in a shared multiplayer world."


def header_uschedule():
    green, sky, lilac = "#A4D894", "#A3C9EE", "#D6B9EF"
    css = ['@keyframes match-slot{0%,12%,100%{opacity:.67;transform:translateY(-4px)}36%,88%{opacity:1;transform:translateY(0)}}']
    weekdays = "".join(
        f'<text x="{47 + i * 34}" y="58">{day}</text><path d="M{30 + i * 34} 64v62" stroke="#375345"/>'
        for i, day in enumerate("MTWTF")
    )
    slots = "".join(
        f'<rect x="{x}" y="{y}" width="25" height="{height}" rx="2" fill="{color}" fill-opacity=".25" stroke="{color}"/>'
        for x, y, height, color in ((34, 70, 22, green), (68, 98, 22, sky), (102, 70, 22, green), (170, 95, 25, lilac))
    )
    art = f"""
<rect x="29" y="64" width="171" height="62" rx="2" fill="#172B23" stroke="#436859"/>
<g font-size="10" text-anchor="middle" fill="#ADCAAD">{weekdays}</g>
<path d="M30 94h169" stroke="#375345"/>
{slots}
<rect x="136" y="81" width="25" height="27" rx="2" fill="{sky}" fill-opacity=".22" stroke="{sky}"
      style="animation:match-slot 5s ease-out var(--art-start) infinite"/>
<circle cx="228" cy="90" r="13" fill="#2B4432" stroke="{green}"/>
<path d="M222 90l4 4 8-9" fill="none" stroke="{green}" stroke-width="2"/>
"""
    return "uschedule.ca", "Build a timetable", green, "#1D3028", art, css, "uschedule.ca. A conflict-free timetable takes shape across five weekdays."


def header_nav():
    sky, gold = "#9ABEF9", "#FFCA86"
    css = ['@keyframes radar-turn{to{transform:rotate(360deg)}}']
    art = f"""
<g transform="translate(146 88)">
  <circle r="46" fill="#18263A" stroke="#587395"/>
  <circle r="32" fill="none" stroke="#3B5373"/><circle r="17" fill="none" stroke="#3B5373"/>
  <path d="M-46 0h92m-46-46v92" stroke="#3B5373"/>
  <g style="animation:radar-turn 6.4s linear var(--art-start) infinite">
    <path d="M0 0V-45a45 45 0 0 1 23 6z" fill="{sky}" opacity=".17"/>
    <path d="M0 0l23-39" stroke="{sky}" stroke-opacity=".63"/>
  </g>
  <path d="M-23 15Q-9-18 21-16m-17 38Q11 10 31 4" fill="none" stroke="{gold}" stroke-opacity=".58" stroke-dasharray="2 3"/>
  <circle cx="-23" cy="15" r="2.6" fill="{gold}"/><circle cx="21" cy="-16" r="2.6" fill="{gold}"/>
  <circle cx="31" cy="4" r="2" fill="{gold}"/>
</g>
<g font-size="10" fill="{sky}"><text x="26" y="72">YOW</text><text x="26" y="105">YUL</text></g>
<path d="M56 68h19m-19 33h21m123-31h29m-29 34h26" stroke="#55779E" stroke-dasharray="2 3"/>
<text x="222" y="90" font-size="9" fill="{sky}">ATC</text>
"""
    return "NAV Canada Simulator", "Open the simulator", sky, "#1B2A40", art, css, "NAV Canada Simulator. A radar sweeps over illustrated Canadian flight paths."


def header_factory():
    lilac, mint = "#D9B7F6", "#A7E3C1"
    css = ['@keyframes ticket-relay{0%,8%{transform:translateX(0);opacity:0}'
           '17%{opacity:1}33%{transform:translateX(55px)}62%{transform:translateX(110px)}'
           '85%{transform:translateX(165px);opacity:1}96%,100%{transform:translateX(165px);opacity:0}}']
    steps = "".join(
        f'<rect x="{x}" y="56" width="42" height="43" rx="4" fill="#34263F" stroke="#7B6191"/>'
        f'<path d="{icon}" transform="translate({x + 21} 76)" fill="none" stroke="{color}" stroke-width="1.3"/>'
        f'<text x="{x + 21}" y="124" text-anchor="middle" font-size="9" fill="{color}">{name}</text>'
        for x, name, icon, color in (
            (30, "Plan", "M-7-10h11l4 4v17H-7zM-3-3h6m-6 5h6", lilac),
            (85, "Build", "M-5-6l-6 6 6 6m10-12 6 6-6 6m-3-16-4 20", lilac),
            (140, "Review", "M-9 0l6 6 12-13", lilac),
            (195, "PR", "M-6-8v16m12-14v8q0 5-7 5h-5M-8-9h4v4h-4zm12 0h4v4h-4z", mint),
        )
    )
    art = f"""
{steps}
<path d="M51 109h165" stroke="#896BA2" stroke-dasharray="2 4"/>
<circle cx="51" cy="109" r="3.5" fill="{mint}" opacity="0" style="animation:ticket-relay 5s linear var(--art-start) infinite"/>
"""
    return "Software Factory", "See the agent pipeline", lilac, "#292138", art, css, "Software Factory. A task moves through planning, coding, and review before opening a pull request."


def build_header_tiles(shift=None):
    tiles = {
        "header-reciped": header_reciped,
        "header-oberon": header_oberon,
        "header-worldmesh": header_worldmesh,
        "header-uschedule": header_uschedule,
        "header-nav": header_nav,
        "header-factory": header_factory,
    }
    return {name: header_tile(*draw(), index, shift, linked=name != "header-oberon")
            for index, (name, draw) in enumerate(tiles.items())}


# ------------------------------------------------------------- text panels
# the page's prose lives in SVGs too, so the boot blackout owns everything

def _text_panel(name, lines, label, h=None, shift=None, pad_y=34, line_h=19):
    W = 830
    H = h or (pad_y + len(lines) * line_h + 16)
    out = [frame(W, H, rx=8)]
    y = pad_y
    for ln, size, fill in lines:
        out.append(f'<text x="22" y="{y}" font-size="{size}" fill="{fill}">{ln}</text>')
        y += line_h
    return name, shell(W, H, [], "".join(out), label, shift, hold=BOOT + 0.4)


def build_text_panels(shift=None):
    panels = []
    bio = [
        ("I made my first games in Blender at nine.", 20, WHITE),
        ("Then came Unity, C#, game jams, Minecraft plugins, and multiplayer networking.", 15, SLATE),
        ("I study software engineering at uOttawa and work on developer tools at Gadget.", 15, SLATE),
    ]
    panels.append(_text_panel("text-intro", bio,
                              "Julien DeWolfe started making games in Blender at nine, followed by Unity, C#, "
                              "game jams, Minecraft plugins, and multiplayer networking. He studies software "
                              "engineering at uOttawa and works on developer tools at Gadget.", shift=shift, line_h=24))

    def section(name, title, sub, label, accent):
        W, H = 830, 56
        out = [
            f'<path d="M2 29v-14h6v14z" fill="{accent}"/>',
            f'<text x="20" y="30" font-size="24" font-weight="700" fill="{WHITE}">{title}</text>',
            f'<text x="{W - 2}" y="27" font-size="12" fill="{SLATE2}" text-anchor="end">{sub}</text>',
            f'<path d="M2 43h826" stroke="{LINE}"/>',
            f'<path d="M2 43h133l9-5h22" fill="none" stroke="{accent}" stroke-opacity=".8" stroke-width="1.4"/>',
        ]
        return name, shell(W, H, [], "".join(out), label, shift, overlay=False)

    panels.append(section("sect-projects", "Some of my projects", "games, apps, and experiments",
                          "Some of my projects. Games, apps, and experiments.", AMBER))
    panels.append(section("sect-gadget", "Gadget experience", "software engineering intern",
                          "Gadget experience. Software engineering intern. Selected work across integrations, support, job queues, and data export.", "#ADD8FF"))
    panels.append(section("sect-stats", "A year on GitHub", "activity and languages",
                          "A year on GitHub. Activity and languages.", "#9AE6CB"))
    panels.append(section("sect-guestbook", "Guestbook", "leave a GitHub issue to sign",
                          "Guestbook, signed by visitors through GitHub issues.", "#DABAFB"))
    panels.append(section("sect-games", "Fun and games", "shared boards powered by GitHub issues",
                          "Everyone plays the same boards through GitHub issues.", "#FFAD92"))

    return dict(panels)


# ------------------------------------------------------------- buttons
# every link button, regenerated with the boot hold baked in

BUTTONS = {
    "btn-sign": ("Sign the guestbook", "#DABAFB"),
    "btn-attack": ("Attack the boss", "#FFAD92"),
    "btn-feed": ("Feed BLOB", AMBER),
    "btn-pet": ("Pet BLOB", AMBER),
    "btn-pixel": ("Place a pixel", "#ADD8FF"),
    "btn-cell": ("Plant a cell", "#9AE6CB"),
    "btn-hatch": ("Open the service hatch", "#FFC164"),
    "btn-pong": ("Play the Pong latency demo", "#FFC164"),
}


SOCIALS = [
    # (name, icon, full label, compact label)
    ("chip-linkedin", "in", "julien-dewolfe", "LinkedIn"),
    ("chip-email", "mail", "JulienDeWolfe@protonmail.com", "Email"),
    ("chip-uschedule", "cal", "uschedule.ca", "uSchedule"),
    ("chip-x", "x", "DewolfeJulien", "X"),
    ("chip-itch", "pad", "itch.io", "itch.io"),
    ("chip-reciped", "fork", "reciped.app", "Reciped"),
]


def _icon(kind, x, y):
    """small amber line icons, 18x18 box at x,y."""
    if kind == "in":
        return (
            f'<rect x="{x}" y="{y}" width="18" height="18" rx="3.5" fill="none" stroke="{AMBER}" stroke-width="1.6"/>'
            f'<text x="{x + 9}" y="{y + 13.5}" font-size="11" font-weight="bold" fill="{AMBER}" text-anchor="middle">in</text>'
        )
    if kind == "mail":
        return (
            f'<rect x="{x}" y="{y + 2}" width="18" height="14" rx="2.5" fill="none" stroke="{AMBER}" stroke-width="1.6"/>'
            f'<path d="M{x + 1.5} {y + 4.5} L{x + 9} {y + 10} L{x + 16.5} {y + 4.5}" fill="none" stroke="{AMBER}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    if kind == "x":
        return (
            f'<rect x="{x}" y="{y}" width="18" height="18" rx="3.5" fill="none" stroke="{AMBER}" stroke-width="1.6"/>'
            f'<path d="M{x + 4.5} {y + 4.5} L{x + 13.5} {y + 13.5} M{x + 13.5} {y + 4.5} L{x + 4.5} {y + 13.5}" '
            f'fill="none" stroke="{AMBER}" stroke-width="1.8" stroke-linecap="round"/>'
        )
    if kind == "cal":
        return (
            f'<rect x="{x}" y="{y + 2}" width="18" height="15" rx="2.5" fill="none" stroke="{AMBER}" stroke-width="1.6"/>'
            f'<line x1="{x + 4.5}" y1="{y}" x2="{x + 4.5}" y2="{y + 4}" stroke="{AMBER}" stroke-width="1.6"/>'
            f'<line x1="{x + 13.5}" y1="{y}" x2="{x + 13.5}" y2="{y + 4}" stroke="{AMBER}" stroke-width="1.6"/>'
            f'<rect x="{x + 4}" y="{y + 8}" width="3" height="3" fill="{AMBER}"/>'
            f'<rect x="{x + 10}" y="{y + 8}" width="3" height="3" fill="{AMBER}"/>'
            f'<rect x="{x + 4}" y="{y + 12.2}" width="3" height="2.5" fill="{AMBER}"/>'
        )
    if kind == "pad":
        return (
            f'<g transform="translate({x} {y})" fill="none" stroke="#DABAFB" stroke-width="1.4" stroke-linecap="round">'
            '<path d="M5 4h8c1.8 0 3.2 1.3 3.5 3l1 4.4c.5 2-1.7 3.3-3.1 1.8L12 11H6l-2.4 2.2C2.2 14.7 0 13.4.5 11.4L1.5 7C1.8 5.3 3.2 4 5 4z"/>'
            '<path d="M5.3 6.5v3.7m-1.8-1.8h3.6m5.1-.8h.2m2 1.8h.2"/></g>'
        )
    if kind == "fork":
        return (
            f'<g transform="translate({x} {y})" fill="none" stroke="#FFAD92" stroke-width="1.5" stroke-linecap="round">'
            '<path d="M4 2v5m3-5v5m3-5v5m-6 0c0 1.5 1 2.5 3 2.5S10 8.5 10 7m-3 2.5V16m8-14c-1.5 2-2 4-2 7h2m0-7v14"/></g>'
        )
    return ""


def build_socials(shift=None):
    pieces = {}
    for name, icon, text, compact in SOCIALS:
        width, height = 270, 44
        compact_below = 49 + len(text) * 7.5
        css = [
            '.compact{display:none}',
            f'@media (max-width:{f(compact_below)}px){{.full{{display:none}}.compact{{display:inline}}}}',
        ]
        body = (
            f'<rect x="2.25" y=".75" width="100%" height="42.5" rx="6" fill="{BG}" stroke="#51444F" '
            'stroke-width="1.5" style="width:calc(100% - 4.5px)"/>'
            '<rect x="2.25" y="1.5" width="100%" height="41" rx="5" fill="url(#scan)" opacity=".1" '
            'style="width:calc(100% - 4.5px)"/>'
            f'<path d="M33 9v26" stroke="{LINE}"/>'
            + _icon(icon, 12, 13)
            + f'<text class="full" x="40" y="26.5" font-size="12.5" fill="{WHITE}">{text}</text>'
            + f'<text class="compact" x="37" y="26" font-size="10.5" fill="{WHITE}">{compact}</text>'
        )
        # Resolve the SVG viewport from the displayed width so the artwork doesn't stretch.
        pieces[name] = shell(width, height, css, body, text, shift, hold=BOOT + 0.3,
                             overlay=False, gutter=0, view_box=False)
    return pieces


def build_buttons(shift=None):
    pieces = {}
    for name, (text, accent) in BUTTONS.items():
        w = len(text) * 8 + 40
        body = (
            f'<rect x="0.75" y="0.75" width="{f(w - 1.5)}" height="34.5" rx="5" fill="{BG}" stroke="{accent}" stroke-opacity=".55"/>'
            f'<path d="M11 13l5 5-5 5" fill="none" stroke="{accent}" stroke-width="1.8"/>'
            f'<text x="27" y="23" font-size="13" font-weight="700" fill="{accent}">{text}</text>'
        )
        pieces[name] = shell(w, 36, [], body, text, shift, gutter=0)
    return pieces


# ------------------------------------------------------------- project cards
# the projects section: one featured card plus six half-width cards in a grid.
# descriptions are baked into the SVGs; the README wraps site cards in links.

def project_card(name, w, h, title, status, desc, motif, motif_css, caption, label, shift=None):
    css = list(motif_css)
    out = [module_box(0, 0, w, h, title, status)]
    y = 48
    for ln in desc:
        out.append(f'<text x="16" y="{y}" font-size="10.5" fill="{SLATE}">{ln}</text>')
        y += 18
    out.append(motif)
    out.append(f'<text x="16" y="{h - 12}" font-size="10" fill="{SLATE2}">{caption}</text>')
    return name, shell(w, h, css, "".join(out), label, shift, hold=BOOT + 0.3)


def card_reciped(shift=None):
    css, out = [], []
    labels = ("api", "web", "mobile")
    for i, to in enumerate((0.86, 0.76, 0.44)):
        by = 56 + i * 16
        p = f"crc{i}"
        out.append(f'<text x="656" y="{by + 6}" font-size="9.5" fill="{SLATE2}" text-anchor="end">{labels[i]}</text>')
        out.append(f'<rect x="666" y="{by}" width="124" height="5" rx="2" fill="{BARBG}"/>')
        out.append(f'<rect x="666" y="{by}" width="124" height="5" rx="2" fill="{AMBER}" opacity="0.9" class="{p}" style="transform:scaleX({f(to)});transform-origin:666px 0"/>')
        css.append(f"@keyframes {p}{{0%,{6 + i * 5}%{{transform:scaleX(0)}}{30 + i * 5}%,88%{{transform:scaleX({f(to)})}}96%,100%{{transform:scaleX(0)}}}}")
        css.append(f".{p}{{animation:{p} 9s cubic-bezier(.3,.6,.3,1) infinite;}}")
    desc = [
        "My current focus: a social recipe app. Import a recipe from any website,",
        "keep your collection in one place, and share what you cook. One GraphQL API",
        "serves the Next.js web app and the Flutter app, with a local LLM parsing recipes.",
    ]
    return project_card("card-reciped", 830, 150, "RECIPED", "IN DEVELOPMENT", desc,
                        "".join(out), css, "the repo stays private until launch",
                        "Reciped, in development: a social recipe app with recipe import, one GraphQL API, "
                        "a Next.js web app, a Flutter mobile app, and local language model parsing.", shift)


def card_uschedule(shift=None):
    css, out = [], []
    for i in range(8):
        p = f"cus{i}"
        bx = 230 + (i % 4) * 40
        by = 106 + (i // 4) * 18
        css.append(f"@keyframes {p}{{0%,{5 + i * 6}%{{opacity:0}}{9 + i * 6}%,86%{{opacity:1}}93%,100%{{opacity:0}}}}")
        css.append(f".{p}{{animation:{p} 10s linear infinite;}}")
        out.append(f'<rect x="{bx}" y="{by}" width="34" height="14" rx="2" fill="{AMBER}" fill-opacity="0.28" stroke="{AMBER}" stroke-opacity="0.8" class="{p}"/>')
    desc = [
        "A timetable builder for uOttawa students. Set your",
        "preferences, get every conflict-free schedule, ranked.",
        "Professor ratings and calendar export are built in.",
    ]
    return project_card("card-uschedule", 404, 170, "USCHEDULE.CA", "LIVE", desc,
                        "".join(out), css, "open uschedule.ca ↗",
                        "uschedule.ca, live: a timetable builder for uOttawa students with preference-based "
                        "conflict-free schedule generation, professor ratings, and calendar export.", shift)


def card_factory(shift=None):
    css, out = [], []
    xs = [154, 218, 282, 346]
    labels = ["plan", "code", "review", "PR"]
    for nx, lb in zip(xs, labels):
        out.append(f'<rect x="{nx}" y="114" width="44" height="20" rx="3" fill="{SCREEN}" stroke="#2A333C"/>')
        out.append(f'<text x="{nx + 22}" y="127" font-size="9" fill="{SLATE}" text-anchor="middle">{lb}</text>')
    for i in range(3):
        out.append(f'<line x1="{xs[i] + 44}" y1="124" x2="{xs[i + 1]}" y2="124" stroke="#232B33"/>')
    css.append(
        "@keyframes csf{0%{transform:translateX(198px);opacity:0}6%{opacity:1}"
        "30%{transform:translateX(218px)}45%{transform:translateX(262px)}"
        "66%{transform:translateX(282px)}80%{transform:translateX(326px)}"
        "92%{transform:translateX(346px);opacity:1}100%{opacity:0}}"
    )
    css.append(".csf{animation:csf 4.5s linear infinite;}")
    out.append(f'<circle cy="124" r="2.4" fill="{AMBER}" class="csf" opacity="0"/>')
    desc = [
        "AI agents working as a small dev team. A manager plans",
        "the work, workers write the code, a reviewer checks it,",
        "and the results come back to me as pull requests.",
    ]
    return project_card("card-factory", 404, 170, "SOFTWARE FACTORY", "AI DEV PIPELINE", desc,
                        "".join(out), css, "personal tool · private repo",
                        "Software Factory: AI agents working as a dev team, with a manager, workers, and a "
                        "reviewer, delivering results as pull requests.", shift)


def card_polybot(shift=None):
    css, out = [], []
    css.append("@keyframes cpb{from{transform:translateX(0)}to{transform:translateX(-230px)}}")
    out.append(
        '<clipPath id="cpbc"><rect x="160" y="106" width="230" height="36"/></clipPath>'
        f'<g clip-path="url(#cpbc)"><g transform="translate(160,124)">'
        f'<path d="{spark_path(seed=23, width=230, amp=9)}" fill="none" stroke="{AMBER}" stroke-width="1.2" opacity="0.75" style="animation:cpb 16s linear infinite"/></g></g>'
    )
    desc = [
        "A lab for testing prediction market strategies on",
        "Polymarket. Six strategies, each in its own Docker",
        "container, reporting to one live dashboard.",
    ]
    return project_card("card-polybot", 404, 170, "POLYBOT", "PAPER TRADING", desc,
                        "".join(out), css, "no wallet keys · no real money",
                        "Polybot: a lab for testing prediction market trading strategies on Polymarket, six "
                        "strategies in Docker containers with one dashboard, paper trading only.", shift)


def card_navsim(shift=None):
    coast = [ring[::2] for ring in _coast() if len(ring) >= 12]
    body, css = globe(330, 118, 25, 144, 12, "cng", coast, meridian_step=60,
                      coast_width=0.7, routes=ROUTES[:2], dots=False)
    desc = [
        "Air traffic control on a 3D globe: 1,000 real Canadian",
        "flights, weather overlays, and conflict scenarios to",
        "resolve before they become close calls.",
    ]
    return project_card("card-navsim", 404, 170, "NAV CANADA SIMULATOR", "SIMULATION", desc,
                        body, css, "try it live ↗",
                        "NAV Canada simulator: air traffic control on a rotating 3D globe with 1,000 real "
                        "Canadian flights, weather, and conflict resolution. Click to open the live simulator.", shift)


def card_netcode(shift=None):
    css, out = [], []
    out.append(f'<rect x="160" y="102" width="230" height="42" fill="{SCREEN}" stroke="{LINE}"/>')
    out.append(f'<line x1="275" y1="106" x2="275" y2="140" stroke="{LINE}" stroke-dasharray="2 4"/>')
    css.append(
        "@keyframes cnc{0%{transform:translate(172px,132px)}25%{transform:translate(240px,108px)}"
        "50%{transform:translate(378px,126px)}75%{transform:translate(290px,140px)}100%{transform:translate(172px,132px)}}"
    )
    css.append(".cnc{animation:cnc 4.6s linear infinite;}")
    out.append(f'<rect x="-2" y="-2" width="4" height="4" fill="{AMBER}" class="cnc" style="transform:translate(172px,132px)"/>')
    css.append("@keyframes cncl{0%,100%{transform:translateY(128px)}40%{transform:translateY(112px)}}")
    css.append("@keyframes cncr{0%,100%{transform:translateY(120px)}50%{transform:translateY(128px)}}")
    out.append(f'<rect x="166" y="-7" width="3" height="14" fill="{AMBER}" style="animation:cncl 4.6s ease-in-out infinite;transform:translateY(128px)"/>')
    out.append(f'<rect x="383" y="-7" width="3" height="14" fill="{AMBER}" style="animation:cncr 4.6s ease-in-out infinite;transform:translateY(120px)"/>')
    desc = [
        "Multiplayer networking from scratch in C#: prediction,",
        "reconciliation, and interpolation, so games feel instant",
        "while the server stays in charge of the truth.",
    ]
    return project_card("card-netcode", 404, 170, "MULTIPLAYER NETCODE", "C# · KUBERNETES", desc,
                        "".join(out), css, "insert coin: play pong with real lag ↗",
                        "Multiplayer netcode: client prediction, server reconciliation, and interpolation in "
                        "C#, plus Kubernetes game servers. Click to play pong with simulated lag and "
                        "toggleable client prediction.", shift)


def card_earlier(shift=None):
    css, out = [], []
    cells = [(0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (1, 1), (2, 1), (4, 1), (2, 0)]
    for i, (c, r) in enumerate(cells):
        p = f"cev{i}"
        css.append(f"@keyframes {p}{{0%,{4 + i * 5}%{{opacity:0}}{8 + i * 5}%,88%{{opacity:1}}94%,100%{{opacity:0}}}}")
        css.append(f".{p}{{animation:{p} 12s linear infinite;}}")
        op = 0.9 if r == 2 else 0.65 if r == 1 else 0.45
        out.append(f'<rect x="{250 + c * 15}" y="{104 + (2 - r) * 11}" width="13" height="9" fill="{AMBER}" opacity="{op}" class="{p}"/>')
    desc = [
        "Years of Minecraft server plugins in Java and Kotlin,",
        "including Conway's Game of Life running inside the",
        "game itself, and Tailor, a tool for flashing OSes.",
    ]
    return project_card("card-earlier", 404, 170, "EARLIER WORK", "2018 TO 2024", desc,
                        "".join(out), css, "where I learned to program · repos ↗",
                        "Earlier work, 2018 to 2024: Minecraft server plugins in Java and Kotlin including "
                        "Conway's Game of Life inside Minecraft, and Tailor, an OS flashing tool. Click for my repos.", shift)


# ------------------------------------------------------------- launch bay

def featured_reciped(shift=None):
    cream, coral = "#F7E7D1", "#FFAD92"
    css = [
        '@keyframes importProgress{0%,12%{transform:scaleX(.12)}'
        '57%,92%{transform:scaleX(1)}100%{transform:scaleX(.12)}}',
        '@keyframes recipePaper{0%,22%{transform:translateY(-5px);opacity:.72}'
        '61%,100%{transform:translateY(0);opacity:1}}',
        '.import-progress{animation:importProgress 5s ease-in-out infinite;transform-origin:481px 106px}',
        '.recipe-paper{animation:recipePaper 5s ease-out infinite}',
    ]
    body = f"""
{frame(830, 260, rx=10)}
<rect x="12" y="12" width="806" height="236" rx="6" fill="#35191D" stroke="#805047"/>
<path d="M426 24v212" stroke="#64413E" stroke-dasharray="2 5"/>
<text x="35" y="94" fill="{cream}" font-size="59" font-weight="700">Reciped</text>
<g fill="{cream}" font-size="21">
  <text x="38" y="137">Turn cooking videos and links</text>
  <text x="38" y="165">into recipes you can cook.</text>
</g>
<path d="M38 199h32" stroke="{coral}" stroke-width="2"/>
<text x="38" y="224" fill="{coral}" font-size="19">Explore Reciped</text>
<path d="M229 217h22m-7-7 7 7-7 7" fill="none" stroke="{coral}" stroke-width="1.6"/>
<rect x="464" y="39" width="314" height="73" rx="5" fill="#21171B" stroke="#8A5249"/>
<text x="481" y="60" fill="{coral}" font-size="12">Recipe import</text>
<rect x="481" y="68" width="280" height="21" rx="3" fill="#3A2629"/>
<path d="M490 75h9l4 4-4 4h-9m9-4h10" fill="none" stroke="{coral}"/>
<text x="517" y="83" fill="{cream}" font-size="12">Cooking video or link</text>
<rect x="481" y="100" width="280" height="4" rx="2" fill="#503539"/>
<rect x="481" y="100" width="280" height="4" rx="2" fill="{coral}" class="import-progress"/>
<path d="M621 113v16m-4-4 4 4 4-4" fill="none" stroke="{coral}"/>
<g class="recipe-paper">
  <rect x="481" y="138" width="280" height="86" rx="4" fill="{cream}"/>
  <text x="495" y="162" fill="#66282E" font-size="17" font-weight="700">Recipe draft</text>
  <path d="M495 171h251m-128 7v35" stroke="#AA7871" stroke-opacity=".65"/>
  <g font-size="11" fill="#66282E">
    <text x="495" y="190">Ingredients</text><text x="630" y="190">Steps</text>
  </g>
  <path d="M495 201h93m-93 8h64m71-8h108m-108 8h72" stroke="#A46760" stroke-opacity=".65" stroke-width="2"/>
</g>
"""
    return shell(830, 260, css, body, "Reciped. Turn cooking videos and links into recipes you can cook.", shift)


def launch_card(title, action, accent, backdrop, scene, css, label, shift, linked=True):
    width, height = 438, 218
    link_mark = f'<path d="M402 198h18m-6-6 6 6-6 6" fill="none" stroke="{accent}" stroke-width="1.5"/>'
    body = f"""
{frame(width, height, rx=9)}
<rect x="12" y="12" width="414" height="128" rx="5" fill="{backdrop}" stroke="{accent}" stroke-opacity=".36"/>
{scene}
<path d="M13 148h412" stroke="{LINE}"/>
<path d="M13 148h36" stroke="{accent}" stroke-width="2"/>
<text x="16" y="179" fill="{WHITE}" font-size="26" font-weight="700">{title}</text>
<text x="17" y="203" fill="{accent}" font-size="16">{action}</text>
{link_mark if linked else ''}
"""
    return shell(width, height, css, body, label, shift)


def oberon_scene():
    gold, purple = "#F6C77F", "#C3B0FD"
    css = [
        '@keyframes activity{from{transform:translateX(-6px);opacity:.4}'
        'to{transform:translateX(126px);opacity:1}}',
        '.activity{animation:activity 3.1s linear infinite}',
    ]
    scene = f"""
<rect x="40" y="27" width="358" height="97" rx="4" fill="#141319" stroke="#534B58"/>
<path d="M41 48h356M100 48v76M100 75h297M100 99h297" stroke="#403846"/>
<path d="M52 37h12m5 0h4m5 0h4" stroke="{gold}" stroke-width="2"/>
<text x="114" y="41" font-size="11" fill="{gold}">Pit Wall</text>
<path d="M52 60h29m-29 13h19m-19 13h25m-25 13h15" stroke="#746779" stroke-width="2"/>
<g font-size="10" fill="#D3C5D5">
  <text x="115" y="65">Codex</text><text x="115" y="91">Claude</text><text x="115" y="114">Pull requests</text>
  <text x="328" y="65" fill="{gold}">working</text><text x="328" y="91" fill="{purple}">review</text>
</g>
<path d="M183 61h29l7-7 5 12 10-9 8 4h65M183 87h124M206 110h101" fill="none" stroke="#6D5F71"/>
<circle class="activity" cx="184" cy="61" r="2.5" fill="{gold}"/>
<path d="M183 87h76m-53 23h46" stroke="{purple}" stroke-opacity=".7" stroke-width="2"/>
"""
    return scene, css, gold, "#26202C"


def launch_oberon(shift=None):
    scene, css, accent, backdrop = oberon_scene()
    return launch_card("Oberon", "Native macOS workspace for AI agents", accent, backdrop, scene, css,
                       "Oberon, a native macOS workspace for AI coding with isolated Git worktrees and pull request review.",
                       shift, linked=False)


def worldmesh_scene():
    mint, gold = "#88E5C9", "#FDC471"
    grid = "".join(
        f'<path d="M{110 + i * 22} {f(78 - i * 6.6)}l110 33M{110 + i * 22} {f(78 + i * 6.6)}l110 -33"/>'
        for i in range(1, 5)
    )
    css = [
        '@keyframes handoff{0%,100%{transform:translate(146px,77px)}'
        '28%{transform:translate(222px,60px)}52%{transform:translate(292px,76px)}'
        '76%{transform:translate(220px,94px)}}',
        f'@keyframes owner{{0%,38%,84%,100%{{fill:{mint}}}39%,83%{{fill:{gold}}}}}',
        '.entity{animation:handoff 6s linear infinite;transform:translate(222px,60px)}',
        '.entity circle{animation:owner 6s steps(1) infinite}',
    ]
    scene = f"""
<path d="M110 78l110-33 110 33-110 33z" fill="#1A3535" stroke="#426662"/>
<g fill="none" stroke="#345855">{grid}</g>
<path d="M146 77 222 60 292 76 220 94z" fill="none" stroke="#72918B" stroke-dasharray="3 4"/>
<path d="M88 75h38m198 0h27" stroke="#72918B" stroke-dasharray="3 4"/>
<g font-size="10" text-anchor="middle">
  <rect x="26" y="49" width="62" height="46" rx="4" fill="#112328" stroke="{mint}" stroke-opacity=".5"/>
  <text x="57" y="69" fill="{mint}">group A</text><path d="M42 81h30" stroke="{mint}" stroke-dasharray="3 3"/>
  <rect x="351" y="49" width="61" height="46" rx="4" fill="#26241D" stroke="{gold}" stroke-opacity=".5"/>
  <text x="381" y="69" fill="{gold}">group B</text><path d="M367 81h29" stroke="{gold}" stroke-dasharray="3 3"/>
</g>
<path d="M175 68h5m-2.5-2.5v5m21 16h5m-2.5-2.5v5" stroke="{mint}" stroke-width="2"/>
<path d="M265 69h5m-2.5-2.5v5m-17 13h5m-2.5-2.5v5" stroke="{gold}" stroke-width="2"/>
<g class="entity"><circle r="5" fill="{mint}" stroke="#E8FFF9" stroke-width="1.5"/></g>
<text x="219" y="128" text-anchor="middle" font-size="10" fill="#A4BDB8">one world / entity groups A and B</text>
"""
    return scene, css, mint, "#0D2024"


def launch_worldmesh(shift=None):
    scene, css, accent, backdrop = worldmesh_scene()
    return launch_card("Worldmesh", "Read the docs", accent, backdrop, scene, css,
                       "Worldmesh, an open-source Rust library for multiplayer worlds across servers.", shift)


def launch_uschedule(shift=None):
    mint, blue, lilac = "#89E6B4", "#83C6FF", "#C2AFF6"
    days = ("MON", "TUE", "WED", "THU", "FRI")
    grid = "".join(
        f'<text x="{113 + i * 54}" y="36">{day}</text><path d="M{86 + i * 54} 44v78" stroke="#2A443C"/>'
        for i, day in enumerate(days)
    )
    css = ['@keyframes slot{from{opacity:0;transform:translateY(-5px)}to{opacity:1;transform:translateY(0)}}']
    blocks = []
    for i, (day, y, height, color, course) in enumerate((
        (0, 49, 24, mint, "SEG"), (1, 77, 39, blue, "CSI"),
        (2, 49, 24, mint, "SEG"), (3, 77, 39, blue, "CSI"),
        (0, 93, 23, lilac, "MAT"), (2, 93, 23, lilac, "MAT"),
    )):
        x = 91 + 54 * day
        blocks.append(f'<g style="animation:slot .25s ease-out {f(.2 + i * .11)}s both">'
                      f'<rect x="{x}" y="{y}" width="44" height="{height}" rx="2" fill="{color}" fill-opacity=".18" stroke="{color}" stroke-opacity=".75"/>'
                      f'<text x="{x + 22}" y="{y + 15}" fill="{color}">{course}</text></g>')
    scene = f"""
<path d="M86 43h270v79H86zm0 26h270m-270 26h270" fill="none" stroke="#2A443C"/>
<g text-anchor="middle" font-size="10" fill="#A7C5B7">{grid}{''.join(blocks)}</g>
<path d="M370 82l8 8 15-16" fill="none" stroke="{mint}" stroke-width="2"/>
"""
    return launch_card("uschedule.ca", "Build a timetable", mint, "#10231C", scene, css,
                       "uschedule.ca, a conflict-free timetable builder for University of Ottawa students.", shift)


def launch_navsim(shift=None):
    sky = "#9DBBFF"
    coast = [ring[::2] for ring in _coast() if len(ring) >= 12]
    sphere, css = globe(289, 76, 53, 90, 14, "launchatc", coast, meridian_step=60, coast_width=1)
    scene = f"""
<g stroke="{sky}" stroke-opacity=".22" fill="none">
  <circle cx="289" cy="76" r="60"/><path d="M197 76h184m-92-63v126" stroke-dasharray="3 4"/>
  <path d="M44 39h8m-8 0v8m125 59h-8m8 0v-8"/>
  <path d="M371 31h26v19h-26v36h26v33h-26"/>
</g>
<g font-size="13" fill="{sky}">
  <text x="57" y="61">YOW / YVR</text><text x="57" y="85">YYZ / YHZ</text>
</g>
<path d="M56 97h85" stroke="{sky}" stroke-opacity=".55" stroke-dasharray="2 4"/>
{sphere}
"""
    return launch_card("NAV Canada Simulator", "Open the radar", sky, "#111C33", scene, css,
                       "NAV Canada Simulator, an air traffic control simulator with Canadian flights on a 3D globe.", shift)


def launch_game_networking(shift=None):
    sky, mint = "#ADD8FF", "#ADF0CF"
    css = ['@keyframes snapshot{0%,12%{transform:translateX(0);opacity:0}20%{opacity:1}'
           '72%{transform:translateX(-73px);opacity:1}88%,100%{transform:translateX(-73px);opacity:0}}']
    cube = '<path d="M0-20l19 10v19L0 20-19 9v-19zM-19-10 0 0l19-10M0 0v20" fill="none" stroke="currentColor" stroke-width="1.4"/>'
    scene = f"""
<path d="M40 84l70-46 83 43-69 29zM57 74l82 30M74 62l80 35m-64-45 80 37M60 91l71-42m-52 49 71-39m-52 46 71-37"
      fill="none" stroke="#45677A"/>
<g color="#6596A7" opacity=".5" transform="translate(87 68)">{cube}</g>
<g color="{sky}" transform="translate(119 59)">{cube}</g>
<g color="{mint}" transform="translate(146 71)">{cube}</g>
<path d="M182 61h75m-71-4-4 4 4 4" stroke="#749EA9" stroke-dasharray="3 3" fill="none"/>
<circle cx="256" cy="61" r="3.2" fill="{mint}" opacity="0" style="animation:snapshot 4.2s linear infinite"/>
<rect x="260" y="36" width="142" height="54" rx="4" fill="#1D3542" stroke="#547589"/>
<text x="331" y="56" text-anchor="middle" font-size="10" fill="{mint}">AUTHORITATIVE SERVER</text>
<path d="M274 65h113" stroke="#516F80"/>
<text x="331" y="80" text-anchor="middle" font-size="10" fill="{sky}">State snapshots</text>
<path d="M25 114h388" stroke="#45677A"/>
<g font-size="10" text-anchor="middle" fill="{sky}">
  <text x="83" y="129">Client prediction</text><text x="219" y="129">Server reconciliation</text><text x="355" y="129">Entity interpolation</text>
</g>
"""
    return launch_card("Realtime Game Networking", "Server-authoritative 3D rollback", sky, "#192B38", scene, css,
                       "Realtime Game Networking. Server-authoritative rollback architecture for a 3D game, with client prediction, server reconciliation, and entity interpolation.",
                       shift, linked=False)


def launch_lightbound(shift=None):
    lavender, gold = "#C9B7FF", "#FFD486"
    css = ['@keyframes lightbound-ring{from{r:15px;opacity:.8}to{r:43px;opacity:0}}']
    souls = "".join(
        f'<g transform="translate({x} {y})"><path d="M-6 7v-7a6 6 0 0 1 12 0v7l-3-3-3 3-3-3z" '
        f'fill="#67558F" stroke="#8E76C7"/><circle cx="-2" cy="-1" r="1" fill="{lavender}"/>'
        f'<circle cx="2" cy="-1" r="1" fill="{lavender}"/></g>'
        for x, y in ((62, 57), (177, 49), (226, 82), (88, 111), (186, 115))
    )
    scene = f"""
<ellipse cx="143" cy="80" rx="111" ry="43" fill="#2B2145" stroke="#594783"/>
<ellipse cx="143" cy="80" rx="79" ry="30" fill="none" stroke="#594783" stroke-dasharray="3 4"/>
<path d="M33 80h220m-110-40v81" stroke="#6B568E" stroke-opacity=".65"/>
{souls}
<circle cx="143" cy="80" r="15" fill="none" stroke="{gold}" stroke-opacity=".7"
        style="animation:lightbound-ring 3.4s ease-out infinite"/>
<path d="M143 72l8 8-8 8-8-8z" fill="{gold}" filter="url(#glow)"/>
<rect x="267" y="53" width="125" height="57" rx="4" fill="#332A4A" stroke="#715D98"/>
<text x="329" y="71" font-size="10" text-anchor="middle" fill="{lavender}">STAT SWAP</text>
<text x="329" y="94" font-size="15" text-anchor="middle" fill="{gold}">HP ⇄ DMG</text>
"""
    return launch_card("Lightbound", "2023 game jam · Survive stat swaps", lavender, "#231B37", scene, css,
                       "Lightbound. Fight waves of lost souls while two stats swap every minute. Made for the 2023 GMTK Game Jam.", shift)


def launch_dice_knight(shift=None):
    jade, gold = "#B1E6BE", "#FFD385"
    css = ['@keyframes dice-rock{0%,100%{transform:rotate(-12deg)}50%{transform:rotate(11deg)}}']
    floor = "".join(
        f'<rect x="{40 + 16 * col}" y="{29 + 16 * row}" width="14" height="14" rx="1" '
        f'fill="{"#517266" if tile == "." else "#32483F"}"/>'
        for row, pattern in enumerate(("####..######", "#......#####", "#.###...####", "#...###....#", "###.....#..#", "#####..#####"))
        for col, tile in enumerate(pattern)
    )
    pip_dots = "".join(f'<circle cx="{x}" cy="{y}" r="2.8" fill="#49403F"/>'
                       for x, y in ((-9, -9), (9, -9), (0, 0), (-9, 9), (9, 9)))
    scene = f"""
{floor}
<path d="M112 53v17h47v16h49" fill="none" stroke="{jade}" stroke-width="1.5" stroke-dasharray="3 3" opacity=".7"/>
<path d="M109 50h6v6h-6z" fill="{jade}"/>
<circle cx="208" cy="86" r="4" fill="{gold}"/>
<path d="M238 83h27m-5-5 5 5-5 5" fill="none" stroke="{jade}" stroke-width="1.5"/>
<g transform="translate(330 72)">
  <g style="animation:dice-rock 4s ease-in-out infinite">
    <rect x="-23" y="-20" width="46" height="46" rx="6" fill="#77694B"/>
    <rect x="-24" y="-24" width="46" height="46" rx="6" fill="#E9DCC0" stroke="{gold}"/>
    {pip_dots}
  </g>
</g>
<circle cx="368" cy="111" r="5" fill="none" stroke="{gold}"/>
<circle cx="381" cy="108" r="4" fill="none" stroke="{gold}"/>
"""
    return launch_card("Dice Knight", "2022 game jam · Fight with dice", jade, "#21322A", scene, css,
                       "Dice Knight. Fight with dice, collect gold, and explore randomly generated dungeons. Made for the 2022 GMTK Game Jam.", shift)


def launch_factory(shift=None):
    lilac = "#DABAFB"
    boxes = "".join(
        f'<rect x="{x}" y="63" width="76" height="33" rx="4" fill="#241C30" stroke="{lilac}" stroke-opacity=".45"/>'
        f'<text x="{x + 38}" y="83" text-anchor="middle" fill="{lilac}" font-size="11">{name}</text>'
        for x, name in ((37, "Plan"), (133, "Build"), (229, "Review"), (325, "Open PR"))
    )
    css = [
        '@keyframes factorypulse{0%{transform:translateX(0);opacity:0}8%{opacity:1}'
        '90%{opacity:1}100%{transform:translateX(288px);opacity:0}}',
        '.factory-pulse{animation:factorypulse 4.6s linear infinite}',
    ]
    scene = f"""
<path d="M75 53h288M113 79h20m76 0h20m76 0h20" stroke="#78668A" stroke-dasharray="2 3"/>
{boxes}
<circle cx="75" cy="53" r="3.2" fill="{lilac}" class="factory-pulse"/>
<path d="M171 99v12h96V99" fill="none" stroke="#78668A" stroke-dasharray="2 3"/>
"""
    return launch_card("Software Factory", "Plan, build, review, open a PR", lilac, "#20182B", scene, css,
                       "Software Factory, a coding tool that assigns planning, implementation, and review to AI agents and opens a pull request.",
                       shift, linked=False)


def launch_polybot(shift=None):
    green, rose = "#A7E393", "#EE9EA6"
    css = ['@keyframes chartscan{0%,12%{transform:translateX(0);opacity:0}'
           '20%,84%{opacity:.8}95%,100%{transform:translateX(262px);opacity:0}}']
    chart = "".join(
        f'<path d="{spark_path(seed, width=264, amp=11, step=8)}" fill="none" stroke="{color}" stroke-width="1.6"/>'
        for seed, color in ((7, green), (23, rose))
    )
    scene = f"""
<rect x="43" y="34" width="352" height="85" rx="4" fill="#15201A" stroke="#49604B"/>
<path d="M57 54h300m-300 22h300m-300 22h300" stroke="#36513D" stroke-dasharray="3 4"/>
<clipPath id="polybot-chart"><rect x="57" y="43" width="300" height="65"/></clipPath>
<g clip-path="url(#polybot-chart)"><g transform="translate(59 76)">{chart}</g></g>
<path d="M59 44v64" stroke="{green}" stroke-opacity=".6" style="animation:chartscan 5s linear infinite"/>
<circle cx="371" cy="57" r="3" fill="{green}"/><circle cx="371" cy="78" r="3" fill="{rose}"/>
"""
    return launch_card("Polybot", "Prediction-market paper trading", green, "#162219", scene, css,
                       "Polybot, a paper-trading lab that runs Polymarket strategies in separate containers and shows their results on one dashboard.",
                       shift, linked=False)


def launch_crossword(shift=None):
    lilac = "#D9BEFF"
    css = [
        '@keyframes crossword-letter{0%,8%{opacity:0}16%,83%{opacity:1}95%,100%{opacity:0}}',
    ]
    board = []
    for row, pattern in enumerate(("#....", ".....", ".....", ".....", "....#")):
        for col, cell in enumerate(pattern):
            x, y = 225 + col * 20, 26 + row * 20
            fill = "#877499" if row == 2 else "#493D57"
            if cell == "#":
                fill = "#1F1929"
            board.append(f'<rect x="{x}" y="{y}" width="18" height="18" rx="1" fill="{fill}" stroke="#A78CB3" stroke-opacity=".42"/>')
    for col, letter in enumerate("SOLVE"):
        board.append(f'<text x="{234 + col * 20}" y="79" text-anchor="middle" fill="#FFF5FF" font-size="12" '
                     f'style="animation:crossword-letter 5.5s linear {f(col * .17)}s infinite">{letter}</text>')
    scene = f"""
<text x="51" y="66" font-size="28" fill="{lilac}">5 × 5</text>
<text x="51" y="87" font-size="12" fill="#BBAECD">A new puzzle daily</text>
<path d="M52 99h122" stroke="#8A709E" stroke-dasharray="2 4"/>
{''.join(board)}
<rect x="305" y="66" width="18" height="18" rx="1" fill="none" stroke="#FFF5FF" stroke-width="1.5"/>
"""
    return launch_card("Totally Not the Mini", "Play today’s crossword", lilac, "#281E32", scene, css,
                       "Totally Not the Mini, a daily crossword with original clues, saved progress, and shareable scores.", shift)


def launch_addons(shift=None):
    gold = "#ECCC8D"
    css = ['@keyframes addon-status{0%,100%{opacity:1}50%{opacity:.45}}']
    scene = f"""
<rect x="53" y="27" width="332" height="98" rx="4" fill="#211C1D" stroke="#765E47"/>
<path d="M54 49h330m-224 0v76" stroke="#624C3F"/>
<text x="65" y="42" fill="{gold}" font-size="11">Installations</text>
<text x="174" y="42" fill="{gold}" font-size="11">Addon library</text>
<rect x="62" y="57" width="89" height="20" rx="3" fill="#594735"/>
<text x="71" y="71" fill="{gold}" font-size="10">Retail</text>
<text x="71" y="93" fill="#C2AB93" font-size="10">Classic</text>
<g fill="#D8C3AB" font-size="10">
  <text x="196" y="67">Action bars</text><text x="196" y="88">Raid tools</text><text x="196" y="109">Quest tracker</text>
</g>
<path d="M171 73h203m-203 22h203" stroke="#4D3D37"/>
<path d="M178 59h10v9h-10zM178 81h10v9h-10zM178 102h10v9h-10z" fill="none" stroke="{gold}"/>
<path d="M361 61l3 3 5-5m-8 24 3 3 5-5m-8 23 3 3 5-5" fill="none" stroke="#B8CDA0" stroke-width="1.5"
      style="animation:addon-status 3.5s ease-in-out infinite"/>
"""
    return launch_card("AddOn Ledger", "See the WoW addon manager", gold, "#332722", scene, css,
                       "AddOn Ledger, a work-in-progress desktop app that keeps the addon libraries of separate World of Warcraft installations organized.", shift)


def launch_construction_map(shift=None):
    orange, blue = "#FFB677", "#90CCE8"
    points = ((89, 61), (176, 86), (247, 61), (319, 100), (348, 75))
    markers = "".join(
        f'<circle cx="{x}" cy="{y}" r="6" fill="#513827" stroke="{orange}" stroke-width="1.5"/>'
        f'<circle cx="{x}" cy="{y}" r="2" fill="{orange}"/>'
        for x, y in points
    )
    css = ['@keyframes project-ring{0%{r:7px;opacity:.85}70%,100%{r:18px;opacity:0}}']
    scene = f"""
<path d="M29 75c35 2 53-40 91-39s64 26 94 22 74-33 111-25 48 38 82 26" fill="none" stroke="#235169" stroke-width="19"/>
<g fill="none" stroke="#506258" stroke-width="1.2">
  <path d="M28 101l87-15 52-26 46 7 64 33 128 15m-373 12 101-6 67-19 46-41 67-6 95 23"/>
  <path d="M47 43l20 39 8 46m43-79 24 28 12 51m29-84-7 42 14 42m50-80 25 34-4 47m36-83 22 54 20 27m29-76-20 26 22 53"/>
  <path d="M33 55h38m64 45 16 15m155-28 40 14m-132 21 49-7"/>
</g>
<path d="M62 109c46-6 72-26 114-23l71-25 72 39 29-25" fill="none" stroke="{orange}" stroke-dasharray="3 4" stroke-opacity=".55"/>
<text x="135" y="39" font-size="10" fill="{blue}">Ottawa River</text>
{markers}
<circle cx="247" cy="61" r="7" fill="none" stroke="{orange}" opacity="0" style="animation:project-ring 2.9s ease-out infinite"/>
"""
    return launch_card("Ottawa Construction Map", "Explore projects on the map", orange, "#182827", scene, css,
                       "Ottawa Construction Map. Explore City of Ottawa construction and development applications on a live map.", shift)


def launch_earlier(shift=None):
    aqua = "#91DCD8"
    cells = {(2, 0), (3, 1), (1, 2), (2, 2), (3, 2)}
    blocks = "".join(
        f'<rect x="{49 + col * 19}" y="{35 + row * 19}" width="16" height="16" rx="1" '
        f'fill="{aqua if (col, row) in cells else LINE}"/>'
        for row in range(5) for col in range(7)
    )
    body = f"""
{frame(830, 116, rx=9)}
<rect x="13" y="13" width="400" height="90" rx="5" fill="#18272A" stroke="{aqua}" stroke-opacity=".36"/>
<g transform="translate(28 -3) scale(.83)">
  {blocks}
  <path d="M203 31v92" stroke="{LINE}"/>
  <rect x="226" y="40" width="165" height="75" rx="4" fill="{SCREEN}" stroke="#46656A"/>
  <text x="240" y="65" font-size="13" fill="{aqua}">&gt; flash OS image</text>
  <path d="M241 85h132" stroke="{LINE}" stroke-width="6"/>
  <path d="M241 85h102" stroke="{aqua}" stroke-width="6"/>
</g>
<text x="440" y="53" font-size="26" font-weight="700" fill="{WHITE}">Earlier work</text>
<text x="441" y="78" font-size="16" fill="{aqua}">Minecraft plugins and OS tools</text>
<path d="M782 72h24m-7-7 7 7-7 7" fill="none" stroke="{aqua}" stroke-width="1.5"/>
"""
    return shell(830, 116, [], body,
                 "Earlier work, including Conway's Game of Life inside Minecraft and Tailor, an OS flashing tool.", shift)


# ------------------------------------------------------------- Gadget work

def gadget_api_upgrades(shift=None):
    blue, lilac = "#ADD8FF", "#DBBBF1"
    scene = f"""
<rect x="31" y="36" width="178" height="83" rx="4" fill="#192A36" stroke="#506F85"/>
<rect x="229" y="36" width="178" height="83" rx="4" fill="#2C2436" stroke="#735B85"/>
<text x="44" y="61" font-size="18" font-weight="700" fill="{blue}">2026-07</text>
<text x="242" y="61" font-size="18" font-weight="700" fill="{lilac}">2026-10</text>
<path d="M44 70h152m46 0h152" stroke="#536073"/>
<g font-size="11">
  <text x="44" y="89" fill="{blue}">Flexible collections</text>
  <text x="44" y="106" fill="#ACC2CE">Model updates</text>
  <text x="242" y="89" fill="{lilac}">Requested order edits</text>
  <text x="242" y="106" fill="#C8B3D4">Webhook updates</text>
</g>
<path d="M212 77h14m-4-4 4 4-4 4" fill="none" stroke="{WHITE}"/>
"""
    return launch_card("Shopify API upgrades", "2026-07 and 2026-10 connector releases", blue, "#1D2835", scene, [],
                       "Shopify API upgrades. Worked on Gadget’s managed connector releases for 2026-07 and 2026-10, including flexible collections and requested order edits.",
                       shift, linked=False)


def gadget_support_bot(shift=None):
    mint = "#A4E8B8"
    css = ['@keyframes draft-message{0%,15%{opacity:.6;transform:translateY(3px)}35%,100%{opacity:1;transform:translateY(0)}}']
    scene = f"""
<rect x="57" y="29" width="324" height="96" rx="4" fill="#192B25" stroke="#527360"/>
<path d="M58 49h322" stroke="#395748"/>
<text x="69" y="43" font-size="10" fill="{mint}">SUPPORT INBOX</text>
<rect x="70" y="58" width="166" height="22" rx="4" fill="#30463D"/>
<text x="80" y="72" font-size="10" fill="#CBDED0">Incoming support ticket</text>
<g style="animation:draft-message 5s ease-out infinite">
  <rect x="189" y="88" width="179" height="23" rx="4" fill="#294936" stroke="#638D70"/>
  <text x="199" y="103" font-size="10" fill="{mint}">Draft ready for review</text>
</g>
"""
    return launch_card("Automatic Support Bot", "Draft replies for staff review", mint, "#1B2923", scene, css,
                       "Automatic Support Bot. Helps draft responses to incoming support tickets for staff to review.",
                       shift, linked=False)


def gadget_job_cancellation(shift=None):
    coral, amber = "#FFAD92", "#F4CE88"
    scene = f"""
<rect x="47" y="28" width="344" height="97" rx="4" fill="#34242A" stroke="#7D535B"/>
<text x="61" y="48" font-size="10" fill="{coral}">FILTER BY</text>
<g font-size="10" text-anchor="middle" fill="{coral}">
  <rect x="128" y="35" width="53" height="18" rx="3" fill="#4C333B"/><text x="154" y="48">Queue</text>
  <rect x="188" y="35" width="62" height="18" rx="3" fill="#4C333B"/><text x="219" y="48">Action</text>
  <rect x="257" y="35" width="52" height="18" rx="3" fill="#4C333B"/><text x="283" y="48">Shop</text>
</g>
<path d="M60 61h318m-318 28h318" stroke="#60434A"/>
<g font-size="11" fill="#E5C9C5">
  <text x="64" y="78">Matching queued jobs</text><text x="64" y="107">Running jobs</text>
</g>
<g font-size="10" text-anchor="end">
  <text x="372" y="78" fill="{coral}">Cancel pending</text><text x="372" y="107" fill="{amber}">Keep running</text>
</g>
"""
    return launch_card("Cancel background jobs", "Clear queues or cancel matching jobs", coral, "#33232B", scene, [],
                       "Background job cancellation. Lets users cancel queued jobs by queue, action, or Shopify shop while running jobs finish.",
                       shift, linked=False)


def gadget_data_exporter(shift=None):
    amber = "#F4CE88"
    css = ['@keyframes export-signal{0%,10%{transform:translateX(0);opacity:0}20%{opacity:1}'
           '77%{transform:translateX(82px);opacity:1}90%,100%{transform:translateX(82px);opacity:0}}']
    scene = f"""
<rect x="47" y="36" width="132" height="83" rx="4" fill="#332A23" stroke="#786243"/>
<text x="59" y="54" font-size="10" font-weight="700" fill="{amber}">APP CONTENTS</text>
<g font-size="10" fill="#DCCAB0">
  <text x="59" y="73">Model records</text><text x="59" y="90">Uploaded files</text><text x="59" y="107">App source</text>
</g>
<path d="M180 77h79m0-26v52m0-52h11m-11 26h11m-11 26h11" fill="none" stroke="#8D774F" stroke-dasharray="3 3"/>
<circle cx="181" cy="77" r="3" fill="{amber}" opacity="0" style="animation:export-signal 4.3s linear infinite"/>
<g font-size="11" fill="{amber}">
  <rect x="272" y="41" width="119" height="20" rx="3" fill="#4B3C2D"/><text x="286" y="55">ZIP</text>
  <rect x="272" y="67" width="119" height="20" rx="3" fill="#4B3C2D"/><text x="286" y="81">S3</text>
  <rect x="272" y="93" width="119" height="20" rx="3" fill="#4B3C2D"/><text x="286" y="107">PostgreSQL</text>
</g>
"""
    return launch_card("Data Exporter", "Export to ZIP, S3, or PostgreSQL", amber, "#2E251F", scene, css,
                       "Data Exporter. Exports app data to a ZIP download, S3-compatible storage, or PostgreSQL.",
                       shift, linked=False)


def service_radio(shift=None):
    # Morse timing: one unit per dot, three per dash or letter gap.
    code = ("-...", ".-..", "---", "-...")
    pulses = []
    unit = 0
    for letter in code:
        for mark in letter:
            length = 1 if mark == "." else 3
            pulses.append((unit, length))
            unit += length + 1
        unit += 2
    duration = (unit + 4) * .16
    css = ['@keyframes tune{to{transform:translateX(647px)}}',
           f'.tuner{{animation:tune {f(duration)}s linear infinite}}']
    marks = "".join(
        f'<rect x="{f(90 + start * 647 / (unit + 4))}" y="55" '
        f'width="{f(length * 647 / (unit + 4))}" height="19" rx="2" fill="{AMBER}"/>'
        for start, length in pulses
    )
    body = f"""
{frame(830, 108, rx=8)}
<text x="24" y="30" font-size="15" fill="{WHITE}">Maintenance radio</text>
<text x="806" y="30" font-size="12" fill="#AAB6C1" text-anchor="end">Morse signal / repeat</text>
<rect x="72" y="46" width="686" height="37" rx="3" fill="{SCREEN}" stroke="{LINE}"/>
<path d="M89 64h654" stroke="#625241"/>
{marks}
<path d="M90 48v32" class="tuner" stroke="#FFF0D3" stroke-opacity=".8"/>
"""
    return shell(830, 108, css, body, "Maintenance radio. Morse code: dash dot dot dot, "
                 "dot dash dot dot, dash dash dash, dash dot dot dot.", shift, hold=0)


def build_story(shift=None):
    W, H = 830, 100
    x0, x1 = 24, 806
    span = x1 - x0
    # (label, start, end, lane) as fractions of the whole stretch; overlapping
    # spans share the page the way they shared the years
    eras = [
        ("blender games", 0.00, 0.17, 0),
        ("unity + c#", 0.13, 0.44, 1),
        ("minecraft plugins", 0.28, 0.68, 0),
        ("uottawa", 0.62, 1.00, 1),
        ("gadget", 0.78, 1.00, 0),
    ]
    css, out = [], [frame(W, H, rx=8)]
    css.append("@keyframes erabar{from{transform:scaleX(0)}to{transform:scaleX(1)}}")
    css.append("@keyframes eralbl{from{opacity:0}to{opacity:1}}")
    css.append("@keyframes nowpulse{0%,100%{opacity:1}50%{opacity:.25}}")

    out.append(f'<line x1="{x0}" y1="74" x2="{x1}" y2="74" stroke="{LINE}"/>')
    out.append(f'<line x1="{x1}" y1="10" x2="{x1}" y2="74" stroke="#2A333C" stroke-dasharray="2 4"/>')

    for label, s, e, lane in eras:
        bx, bw = x0 + s * span, (e - s) * span
        by = 12 + lane * 28
        delay = 0.15 + s * 1.1
        out.append(
            f'<rect x="{f(bx)}" y="{by}" width="{f(bw)}" height="20" rx="4" fill="{AMBER}" fill-opacity="0.14" '
            f'stroke="{AMBER}" stroke-opacity="0.55" '
            f'style="animation:erabar .7s cubic-bezier(.3,.6,.3,1) both;animation-delay:{f(delay)}s;'
            f'transform-origin:{f(bx)}px 0"/>'
        )
        out.append(
            f'<text x="{f(bx + 9)}" y="{by + 14}" font-size="10.5" fill="{AMBER}" '
            f'style="animation:eralbl .4s both;animation-delay:{f(delay + 0.35)}s">{label}</text>'
        )

    out.append(f'<text x="{x0}" y="92" font-size="10" fill="{SLATE2}">the beginning</text>')
    out.append(f'<circle cx="{x1 - 34}" cy="88.5" r="3" fill="{AMBER}" style="animation:nowpulse 2s ease-in-out infinite"/>')
    out.append(f'<text x="{x1}" y="92" font-size="10" fill="{SLATE}" text-anchor="end">now</text>')
    label = ("Timeline from the beginning to now: blender games, then unity and c sharp, minecraft plugins "
             "overlapping them, then uOttawa with gadget running alongside it into the present.")
    return shell(W, H, css, "".join(out), label, shift)


# ------------------------------------------------------------- 3d skyline

def build_skyline(shift=None, camera="flyover", fly_phi=20, fly_tilt=28):
    with open(os.path.join(ROOT, "tools", "skyline-data.json")) as snapshot:
        data = json.load(snapshot)
    weeks = data["weeks"]
    peak = max((count for week in weeks for count in week), default=0)

    W, H = 830, 288
    scene_top, scene_bottom = 42, H - 28
    center_y = (scene_top + scene_bottom) / 2
    tilt = fly_tilt if camera == "flyover" else 26
    ux, uz = 13, 15
    half_width, half_depth = 4.35, 4.7
    x_off, z_off = (max(1, len(weeks)) - 1) / 2, 3
    ground_x, ground_z = x_off * ux + 15, z_off * uz + 14
    ground = [(-ground_x, 0, -ground_z), (ground_x, 0, -ground_z),
              (ground_x, 0, ground_z), (-ground_x, 0, ground_z)]
    palettes = [
        ("#80636C", "#47303F", "#2F2C43"),
        ("#C89277", "#6A444A", "#413047"),
        ("#F6B471", "#925750", "#5C3A52"),
        ("#FFE19B", "#B87751", "#774653"),
    ]
    bars = []
    for wi, week in enumerate(weeks):
        for di, count in enumerate(week):
            if count > 0:
                level = math.sqrt(count / peak)
                bars.append(((wi - x_off) * ux, (di - z_off) * uz,
                             4 + 74 * level, min(3, int(4 * level)), wi + di))
    tallest = max(bars, key=lambda bar: bar[2], default=None)

    def roof(x, z, height):
        return [(x - half_width, height, z - half_depth), (x + half_width, height, z - half_depth),
                (x + half_width, height, z + half_depth), (x - half_width, height, z + half_depth)]

    # Include the roofs and platform in the fit so a new peak cannot get cropped.
    bounds = ground + [(x, -6, z) for x, _, z in ground]
    for bar in bars:
        x, z, height, _, _ = bar
        bounds.extend(roof(x, z, height + (14 if bar is tallest else 0)))

    def projection(phi, pitch=tilt):
        cp, sp = math.cos(phi), math.sin(phi)
        ct, st = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

        def rotate(x, y, z):
            x2 = x * cp + z * sp
            z2 = -x * sp + z * cp
            return x2, z2 * st - y * ct, z2 * ct

        xs, ys, _ = zip(*(rotate(*point) for point in bounds))
        scale = min((W - 60) / (max(xs) - min(xs)),
                    (scene_bottom - scene_top - 22) / (max(ys) - min(ys)), 1.24)
        dx = W / 2 - (min(xs) + max(xs)) * scale / 2
        dy = center_y - (min(ys) + max(ys)) * scale / 2

        def project(x, y, z):
            px, py, depth = rotate(x, y, z)
            return dx + px * scale, dy + py * scale, depth

        return project

    def path(points, project, close=False):
        coords = (project(*point) for point in points)
        return "M" + "L".join(f"{px:.1f},{py:.1f}" for px, py, _ in coords) + ("Z" if close else "")

    css = [
        ".sky-top{fill:var(--roof);stroke:#251D2B;stroke-width:.55;stroke-linejoin:round}",
        ".sky-front{fill:var(--front)}.sky-side{fill:var(--side)}",
        ".sky-windows{fill:none;stroke:#FFE8B8;stroke-width:.68;stroke-opacity:.54}",
        ".sky-title{font-size:17px;font-weight:700}.sky-meta{font-size:12px}",
        "@media (max-width:500px){.sky-title{font-size:26px}.sky-meta{font-size:20px}.sky-snapshot{display:none}}",
        "@keyframes roof-beacon{0%,100%{opacity:.28}42%{opacity:.9}}",
    ]
    for i, (top, front, side) in enumerate(palettes):
        css.append(f".sky-tier{i}{{--roof:{top};--front:{front};--side:{side}}}")

    def render_tower(bar, project, front, side, show_roof=True, pane_height=0):
        bx, bz, height, tier, offset = bar
        x0, x1 = bx - half_width, bx + half_width
        z0, z1 = bz - half_depth, bz + half_depth
        front_z = bz + front * half_depth
        side_x = bx + side * half_width
        tower = [f'<g class="sky-tier{tier}">']
        if front:
            facade = [(x0, height, front_z), (x1, height, front_z), (x1, 0, front_z), (x0, 0, front_z)]
            tower.append(f'<path class="sky-front" d="{path(facade, project, True)}"/>')
        if side:
            facade = [(side_x, height, z0), (side_x, height, z1), (side_x, 0, z1), (side_x, 0, z0)]
            tower.append(f'<path class="sky-side" d="{path(facade, project, True)}"/>')
        if show_roof:
            tower.append(f'<path class="sky-top" d="{path(roof(bx, bz, height), project, True)}"/>')

        def window(a, b):
            if pane_height:
                ax, ay, az = a
                bx, by, bz = b
                return path([a, b, (bx, by + pane_height, bz), (ax, ay + pane_height, az)], project, True)
            return path([a, b], project)

        windows = []
        floor_gap = 5 if pane_height else 8
        for floor, y in enumerate(range(floor_gap, int(height - 5), floor_gap)):
            if front:
                for col, start in enumerate((1.4, 4.9)):
                    if (offset + 2 * floor + col) % 5:
                        windows.append(window((x0 + start, y, front_z), (x0 + start + 2, y, front_z)))
            if side:
                if pane_height:
                    for col, start in enumerate((1.4, 4, 6.6)):
                        if (offset + floor + col) % 4:
                            windows.append(window((side_x, y, z0 + start), (side_x, y, z0 + start + 1.35)))
                elif (offset + floor) % 3 == 0:
                    windows.append(window((side_x, y, z0 + 2.2), (side_x, y, z1 - 2.2)))
        if windows:
            window_class = "sky-panes" if pane_height else "sky-windows"
            tower.append(f'<path class="{window_class}" d="{"".join(windows)}"/>')
        return "".join(tower) + "</g>"

    def render_beacon(project):
        if not tallest:
            return ""
        tx, tz, th, _, _ = tallest
        x, y, _ = project(tx, th + 11, tz)
        mast = path([(tx, th, tz), (tx, th + 11, tz)], project)
        return (
            f'<path d="{mast}" fill="none" stroke="#FFE19B" stroke-width="1.1"/>'
            f'<circle cx="{f(x)}" cy="{f(y)}" r="5.2" fill="#FFE19B" opacity=".32" '
            'style="animation:roof-beacon 2.8s ease-in-out infinite"/>'
            f'<circle cx="{f(x)}" cy="{f(y)}" r="1.7" fill="#FFF2CD"/>'
        )

    def render_frame(phi, project, traffic=""):
        cp, sp = math.cos(phi), math.sin(phi)
        scene = []

        for i, facing in enumerate((-cp, -sp, cp, sp)):
            if facing > .001:
                a, b = ground[i], ground[(i + 1) % 4]
                skirt = (a, b, (b[0], -6, b[2]), (a[0], -6, a[2]))
                scene.append(f'<path d="{path(skirt, project, True)}" fill="url(#sky-skirt)" stroke="#40505C" stroke-width=".7"/>')
        scene.append(f'<path d="{path(ground, project, True)}" fill="url(#sky-streets)" stroke="#507485" stroke-width=".85"/>')

        avenues = []
        for day in range(6):
            z = (day + .5 - z_off) * uz
            avenues.append(path([(-ground_x + 4, .1, z), (ground_x - 4, .1, z)], project))
        scene.append(f'<path d="{"".join(avenues)}" fill="none" stroke="#497084" stroke-opacity=".35" stroke-width=".65"/>')
        for quarter in range(1, 4):
            x = ((len(weeks) - 1) * quarter / 4 - x_off) * ux
            divider = path([(x, .1, -ground_z + 3), (x, .1, ground_z - 3)], project)
            scene.append(f'<path d="{divider}" fill="none" stroke="#618D98" stroke-opacity=".64" stroke-width=".75" stroke-dasharray="2 3"/>')
        route = path([(-ground_x + 5, .1, ground_z - 5), (ground_x - 5, .1, ground_z - 5)], project)
        scene.append(f'<path d="{route}" fill="none" stroke="#6DD9CF" stroke-opacity=".55" stroke-width=".85"/>')
        scene.append(traffic)

        front = 1 if cp > .001 else -1 if cp < -.001 else 0
        side = -1 if sp > .001 else 1 if sp < -.001 else 0
        for bar in sorted(bars, key=lambda bar: project(bar[0], 0, bar[1])[2]):
            scene.append(render_tower(bar, project, front, side))
        scene.append(render_beacon(project))
        return "".join(scene)

    def street_lights(project):
        lights = []
        for lane, z, duration, direction in ((0, -2.5 * uz, 13, 1), (1, .5 * uz, 17, -1),
                                             (2, ground_z - 5, 15, 1)):
            start = project(direction * (-ground_x + 7), .7, z)
            end = project(direction * (ground_x - 7), .7, z)
            dx, dy = end[0] - start[0], end[1] - start[1]
            distance = math.hypot(dx, dy)
            trail_x, trail_y = dx * 11 / distance, dy * 11 / distance
            name = f"skylane{lane}"
            css.append(f"@keyframes {name}{{to{{transform:translate({f(dx)}px,{f(dy)}px)}}}}")
            for car in range(2):
                delay = -duration * (.18 + .43 * car + .07 * lane)
                x, y, _ = start
                tint = "#6DD9CF" if lane != 1 else "#FFCF84"
                lights.append(
                    f'<g style="animation:{name} {duration}s linear {f(delay)}s infinite">'
                    f'<path d="M{f(x - trail_x)} {f(y - trail_y)}L{f(x)} {f(y)}" '
                    f'stroke="{tint}" stroke-width="1.25" stroke-opacity=".68"/>'
                    f'<circle cx="{f(x)}" cy="{f(y)}" r="2.7" fill="{tint}" opacity=".22"/>'
                    f'<circle cx="{f(x)}" cy="{f(y)}" r="1.24" fill="{tint}"/></g>'
                )
        return "".join(lights)

    def render_street():
        # The camera is in the gap between two rows, looking along the week axis.
        street_z, eye_y, focal_length = -uz / 2, 19, 240
        start = max(-ground_x, tallest[0] - 12.5 * ux)
        eye_x = start - 26
        horizon = center_y + 12
        advance = 12

        def project(x, y, z):
            depth = x - eye_x
            scale = focal_length / depth
            return W / 2 + (z - street_z) * scale, horizon + (eye_y - y) * scale, depth

        def moving_row(x, art):
            depth = x - eye_x
            zoom = depth / (depth - advance)
            return (f'<g class="sky-street-row sky-shot-motion" style="--street-zoom:{f(zoom)};'
                    f'transform-origin:{f(W / 2)}px {f(horizon)}px">{art}</g>')

        street = [(start, 0, -ground_z), (ground_x, 0, -ground_z),
                  (ground_x, 0, ground_z), (start, 0, ground_z)]
        scene = [f'<path d="{path(street, project, True)}" fill="url(#sky-streets)"/>']
        for z in (street_z - 2.7, street_z + 2.7):
            lane_edge = path([(start, .1, z), (ground_x, .1, z)], project)
            scene.append(f'<path d="{lane_edge}" stroke="#6DD9CF" stroke-opacity=".5" stroke-width="1"/>')
        for x in range(math.ceil(start / 8) * 8, int(ground_x), 8):
            dash = path([(x, .1, street_z), (x + 3, .1, street_z)], project)
            marker = f'<path d="{dash}" stroke="#6DD9CF" stroke-opacity=".36" stroke-width="1"/>'
            scene.append(moving_row(x, marker))

        for lane, z, color in ((0, street_z - 1.35, "#6DD9CF"), (1, street_z + 1.35, "#FFE19B")):
            far_x, far_y, _ = project(ground_x, .6, z)
            near_x, near_y, _ = project(start, .6, z)
            name = f"sky-headlight{lane}"
            css.append(f"@keyframes {name}{{0%{{opacity:0;transform:scale(.42)}}"
                       "20%{opacity:.88}86%{opacity:1}"
                       f"100%{{opacity:0;transform:translate({f(near_x - far_x)}px,{f(near_y - far_y)}px) scale(3)}}}}")
            delay = -lane * 1.8
            scene.append(
                f'<g style="animation:{name} 3.6s cubic-bezier(.55,0,.98,.56) {f(delay)}s infinite;'
                f'transform-origin:{f(far_x)}px {f(far_y)}px">'
                f'<circle cx="{f(far_x)}" cy="{f(far_y)}" r="3.5" fill="{color}" opacity=".3"/>'
                f'<circle cx="{f(far_x)}" cy="{f(far_y)}" r="1.4" fill="{color}"/></g>'
            )
        # A row scales about the vanishing point as the camera advances. Near
        # rows pass faster than distant rows without a full SVG for every frame.
        rows = {}
        for bar in reversed(bars):
            x, z, height, _, _ = bar
            if x - half_width >= start:
                front = 1 if street_z > z else -1
                art = render_tower(bar, project, front, -1, show_roof=height < eye_y, pane_height=1.15)
                rows.setdefault(x, []).append(art)
        scene.extend(moving_row(x, "".join(towers)) for x, towers in rows.items())
        return "".join(scene)

    def render_shots(overview):
        loop = 18
        css.extend((
            f".sky-shot{{animation-duration:{loop}s;animation-delay:{f(BOOT)}s;"
            "animation-iteration-count:infinite;animation-timing-function:step-end}",
            f".sky-shot-motion{{animation-duration:{loop}s;animation-delay:{f(BOOT)}s;"
            "animation-iteration-count:infinite;animation-timing-function:ease-in-out}",
            ".sky-overview{animation-name:sky-overview-shot}.sky-overview>.sky-shot-motion{animation-name:sky-overview-drift}",
            ".sky-street{animation-name:sky-street-shot}.sky-street>.sky-shot-motion{animation-name:sky-street-drift}",
            ".sky-peak{animation-name:sky-peak-shot}.sky-peak>.sky-shot-motion{animation-name:sky-peak-drift}",
            ".sky-street .sky-side{fill:var(--front)}.sky-street .sky-front{fill:var(--side)}",
            ".sky-panes{fill:#FFDEA4;fill-opacity:.52}.sky-street-row{animation-name:sky-street-travel;animation-timing-function:linear}",
            "@keyframes sky-overview-shot{0%,87%,100%{opacity:1}28%{opacity:0}}",
            "@keyframes sky-street-shot{0%,63%,100%{opacity:0}28%{opacity:1}}",
            "@keyframes sky-peak-shot{0%,87%,100%{opacity:0}63%{opacity:1}}",
            "@keyframes sky-overview-drift{0%,100%{transform:translate(0,0) scale(1)}"
            "28%{transform:translate(-33px,-12px) scale(1.08)}87%{transform:translate(-20px,-7px) scale(1.05)}}",
            "@keyframes sky-street-drift{0%,28%{transform:translate(0,0)}63%,100%{transform:translate(7px,-3px)}}",
            "@keyframes sky-street-travel{0%,28%{transform:scale(1)}63%,100%{transform:scale(var(--street-zoom))}}",
        ))
        tx, tz, th, _, _ = tallest
        peak_phi = math.radians(-34)
        peak_project = projection(peak_phi, 19)
        x, base, _ = peak_project(tx, 0, tz)
        _, beacon, _ = peak_project(tx, th + 11, tz)
        y = (base + beacon) / 2
        zoom = 146 / (base - beacon)
        peak_target = W * (.58 if tx >= 0 else .42)
        poses = []
        for stop, scale, target_x, target_y in (
            ("0%,63%", zoom, peak_target, center_y + 8),
            ("87%,100%", zoom * 1.17, peak_target - 24, center_y - 4),
        ):
            dx, dy = target_x - x * scale, target_y - y * scale
            poses.append(f"{stop}{{transform:translate({f(dx)}px,{f(dy)}px) scale({f(scale)})}}")
        css.append("@keyframes sky-peak-drift{" + "".join(poses) + "}")

        scenes = (
            ("overview", 1, overview),
            ("street", 0, render_street()),
            ("peak", 0, render_frame(peak_phi, peak_project)),
        )
        return "".join(
            f'<g class="sky-shot sky-{name}" opacity="{opacity}">'
            f'<g class="sky-shot-motion">{art}</g></g>'
            for name, opacity, art in scenes
        )

    if camera in ("flyover", "fixed"):
        phi = math.radians(fly_phi if camera == "flyover" else 34)
        project = projection(phi)
        scene = render_frame(phi, project, street_lights(project) if camera == "flyover" else "")
        if camera == "flyover" and tallest and len(bars) >= 5:
            scene = render_shots(scene)
    else:
        num_frames, duration = (96, 22) if camera == "turntable" else (72, 12)
        frames = []
        for i in range(num_frames):
            turn = 2 * math.pi * i / num_frames
            phi = math.radians(28) + turn if camera == "turntable" else math.radians(28 + 18 * math.sin(turn))
            name = f"skyframe{i}"
            begin, end = 100 * i / num_frames, 100 * (i + 1) / num_frames
            keyframes = f"{f(begin)}%{{opacity:1}}{f(end)}%{{opacity:0}}"
            if i:
                keyframes = "0%{opacity:0}" + keyframes
            css.append(f"@keyframes {name}{{{keyframes}}}")
            frames.append(f'<g opacity="{1 if i == 0 else 0}" style="animation:{name} {duration}s steps(1) infinite">'
                          + render_frame(phi, projection(phi)) + "</g>")
        scene = "".join(frames)

    peak_label = ""
    if peak:
        peak_label = f'<text x="807" y="29" text-anchor="end" class="sky-meta" fill="#FFE19B">Peak day {peak:,}</text>'
    out = f"""
<defs>
  <clipPath id="sky-view"><rect x="10" y="{scene_top}" width="{W - 20}" height="{scene_bottom - scene_top}" rx="6"/></clipPath>
  <radialGradient id="sky-night" cx=".73" cy=".24" r=".86">
    <stop stop-color="#26324B"/><stop offset=".58" stop-color="#111C2B"/><stop offset="1" stop-color="#0D121E"/>
  </radialGradient>
  <linearGradient id="sky-streets" x2=".2" y2="1">
    <stop stop-color="#27354A"/><stop offset="1" stop-color="#172131"/>
  </linearGradient>
  <linearGradient id="sky-skirt" x2="0" y2="1">
    <stop stop-color="#25394A"/><stop offset="1" stop-color="#10131E"/>
  </linearGradient>
  <pattern id="sky-grid" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(-9)">
    <path d="M0 0h28M0 0v28" stroke="#769CAD" stroke-opacity=".17" stroke-width="1"/>
  </pattern>
</defs>
{frame(W, H)}
<text x="21" y="29" class="sky-title" fill="{WHITE}">Contribution skyline</text>
{peak_label}
<g clip-path="url(#sky-view)">
  <rect x="10" y="{scene_top}" width="{W - 20}" height="{scene_bottom - scene_top}" fill="url(#sky-night)"/>
  <rect x="10" y="{scene_top}" width="{W - 20}" height="{scene_bottom - scene_top}" fill="url(#sky-grid)"/>
  {scene}
</g>
<text x="22" y="{H - 10}" class="sky-meta" fill="{AMBER}">{data["total"]:,}<tspan fill="{SLATE}"> contributions</tspan></text>
<text x="{W / 2:g}" y="{H - 10}" class="sky-snapshot" text-anchor="middle" font-size="11" fill="{SLATE2}">Nightly snapshot</text>
<text x="808" y="{H - 10}" class="sky-meta" fill="{SLATE}" text-anchor="end">1 tower per active day</text>
"""
    label = f"Contribution skyline. {data['total']:,} contributions visualized as a city with one tower per active day."
    if peak:
        label += f" The busiest day had {peak:,} contributions."
    return shell(W, H, css, out, label, shift)


# ------------------------------------------------------------- main

def main():
    args = sys.argv[1:]
    shift = None
    if "--shift" in args:
        i = args.index("--shift")
        shift = float(args[i + 1])

    outputs = {
        "hero-header": build_hero_header(shift),
        "story": build_story(shift),
        "skyline": build_skyline(shift),
        "featured-reciped": featured_reciped(shift),
        "launch-oberon": launch_oberon(shift),
        "launch-worldmesh": launch_worldmesh(shift),
        "launch-uschedule": launch_uschedule(shift),
        "launch-navsim": launch_navsim(shift),
        "launch-game-networking": launch_game_networking(shift),
        "launch-lightbound": launch_lightbound(shift),
        "launch-dice-knight": launch_dice_knight(shift),
        "launch-factory": launch_factory(shift),
        "launch-polybot": launch_polybot(shift),
        "launch-crossword": launch_crossword(shift),
        "launch-addons": launch_addons(shift),
        "launch-construction-map": launch_construction_map(shift),
        "launch-earlier": launch_earlier(shift),
        "gadget-api-upgrades": gadget_api_upgrades(shift),
        "gadget-support-bot": gadget_support_bot(shift),
        "gadget-job-cancellation": gadget_job_cancellation(shift),
        "gadget-data-exporter": gadget_data_exporter(shift),
        "service-radio": service_radio(shift),
    }
    outputs.update(build_text_panels(shift))
    outputs.update(build_buttons(shift))
    outputs.update(build_socials(shift))
    outputs.update(build_hero_modules(shift))
    outputs.update(build_header_tiles(shift))
    for fn in (card_reciped, card_uschedule, card_factory, card_polybot,
               card_navsim, card_netcode, card_earlier):
        name, svg = fn(shift)
        outputs[name] = svg

    for name, svg in outputs.items():
        path = os.path.join(ROOT, "assets", f"{name}.svg")
        with open(path, "w") as fh:
            fh.write(svg)
        print(f"wrote assets/{name}.svg ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
