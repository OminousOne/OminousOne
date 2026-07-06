#!/usr/bin/env python3
"""
build.py generates every SVG asset for the profile README.

No JavaScript, no GIFs: each graphic is a single SVG whose animation is baked
into CSS keyframes, which GitHub preserves inside <img>-embedded SVGs.

Outputs:
  assets/hero-header.svg   pixel wordmark strip
  assets/mod-*.svg         one animated hero module per project
  assets/card-*.svg        project cards for the grid in the Projects section
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

AMBER = "#FFB300"
WHITE = "#EDE6D6"
SLATE = "#6C7986"
SLATE2 = "#46525E"
LINE = "#1E262E"
PANEL = "#0A0D10"
SCREEN = "#05070A"
BG = "#0E1116"
BARBG = "#1B222A"

MONO = "ui-monospace,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"


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

def shell(w, h, css, body, label, shift=None):
    dev = f"<style>*{{animation-delay:-{f(shift)}s !important}}</style>" if shift else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">
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
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="10" fill="url(#scan)" opacity="0.14"/>
</svg>"""


def frame(w, h, rx=10):
    return f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx}" fill="{BG}" stroke="#262E36" stroke-width="1.5"/>'


def module_box(x, y, w, h, title, status):
    return (
        f'<rect x="{x + 0.75}" y="{y + 0.75}" width="{w - 1.5}" height="{h - 1.5}" rx="8" '
        f'fill="{PANEL}" stroke="#262E36" stroke-width="1.5"/>'
        f'<text x="{x + 12}" y="{y + 19}" font-size="11" letter-spacing="1.4" fill="{AMBER}">{title}</text>'
        f'<text x="{x + w - 12}" y="{y + 19}" font-size="9" letter-spacing="0.8" fill="{SLATE2}" text-anchor="end">{status}</text>'
    )


# ------------------------------------------------------------- hero modules
# each returns (body, css). coordinates are absolute; p = unique class prefix.

def mod_reciped(x, y, w, h):
    css, out = [], [module_box(x, y, w, h, "RECIPED", "IN DEV")]
    bars = [("api", 0.86, 0.0), ("web", 0.76, 0.9), ("mobile", 0.44, 1.8)]
    bw = w - 96
    for i, (label, fill_to, delay) in enumerate(bars):
        by = y + 44 + i * 30
        p = f"rcp{i}"
        out.append(f'<text x="{x + 12}" y="{by + 8}" font-size="10.5" fill="{SLATE}">{label}</text>')
        out.append(f'<rect x="{x + 62}" y="{by}" width="{bw}" height="8" rx="2" fill="{BARBG}"/>')
        out.append(
            f'<rect x="{x + 62}" y="{by}" width="{bw}" height="8" rx="2" fill="{AMBER}" opacity="0.9" '
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
        f'<rect x="{x + 62}" y="{y + 134}" width="6" height="11" fill="{AMBER}" '
        f'style="animation:rcpcur 1.1s steps(1) infinite"/>'
    )
    out.append(f'<text x="{x + 12}" y="{y + 144}" font-size="10" fill="{SLATE2}">next up</text>')
    return "".join(out), css


def mod_uschedule(x, y, w, h):
    css, out = [], [module_box(x, y, w, h, "USCHEDULE.CA", "LIVE ↗")]
    css.append("@keyframes uspulse{0%,100%{opacity:1}50%{opacity:.2}}")
    out.append(f'<circle cx="{x + w - 60}" cy="{y + 15.5}" r="3" fill="{AMBER}" style="animation:uspulse 2s ease-in-out infinite"/>')
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
            f'height="{f(span * (ch + gap) - gap - 4)}" rx="2" fill="{AMBER}" fill-opacity="0.28" '
            f'stroke="{AMBER}" stroke-opacity="0.85" class="{p}" opacity="1"/>'
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
    css, out = [], [module_box(x, y, w, h, "POLYBOT", "PAPER ONLY")]
    names = ["market-maker", "basket-arb", "btc-5m"]
    for i, name in enumerate(names):
        ry = y + 52 + i * 32
        p = f"pb{i}"
        css.append(f"@keyframes {p}led{{0%,100%{{opacity:1}}50%{{opacity:.15}}}}")
        out.append(f'<circle cx="{x + 18}" cy="{ry}" r="2.6" fill="{AMBER}" style="animation:{p}led {f(1.3 + i * 0.5)}s ease-in-out infinite"/>')
        out.append(f'<text x="{x + 28}" y="{ry + 3.5}" font-size="9" fill="{SLATE}">{name}</text>')
        sw = w - 122
        sx = x + 106
        css.append(f"@keyframes {p}s{{from{{transform:translateX(0)}}to{{transform:translateX(-{sw}px)}}}}")
        out.append(
            f'<clipPath id="{p}c"><rect x="{sx}" y="{ry - 12}" width="{sw}" height="24"/></clipPath>'
            f'<g clip-path="url(#{p}c)"><g transform="translate({sx},{ry})">'
            f'<path d="{spark_path(seed=11 + i * 7, width=sw)}" fill="none" stroke="{AMBER}" '
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
    out.append(f'<rect x="{rx_}" y="-10" width="4" height="20" rx="1" fill="{AMBER}" class="ncpr" style="transform:translateY({f(mid)}px)"/>')
    out.append(
        f'<rect x="{rx_}" y="-10" width="4" height="20" rx="1" fill="none" stroke="{AMBER}" '
        f'stroke-dasharray="3 2" opacity="0.5" class="ncpr nclag" style="transform:translateY({f(mid)}px)"/>'
    )
    out.append(f'<text x="{x + 12}" y="{y + h - 12}" font-size="10" fill="{SLATE2}">prediction, rollback, interpolation</text>')
    return "".join(out), css


def mod_factory(x, y, w, h):
    css, out = [], [module_box(x, y, w, h, "SOFTWARE FACTORY", "AGENTS")]
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
    out.append(f'<text x="{x + w - 16}" y="{f(my + 4)}" font-size="10" fill="{AMBER}" text-anchor="end" opacity="0.9">PR</text>')
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
        out.append(f'<circle r="2.4" fill="{AMBER}" class="{p}" opacity="0"/>')
    css.append(
        f"@keyframes sfpr{{0%,66%{{opacity:0;transform:translate({rev[0] + rev[2]}px,{my}px)}}"
        f"72%{{opacity:1}}84%{{transform:translate({x + w - 26}px,{my}px);opacity:1}}88%,100%{{opacity:0}}}}"
    )
    css.append(".sfpr{animation:sfpr 5.4s linear infinite;}")
    out.append(f'<circle r="2.4" fill="{AMBER}" class="sfpr" opacity="0"/>')
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
    css, out = [], [module_box(x, y, w, h, "ATC SIMULATOR", "CYOW ↗")]
    body, gcss = globe(x + w / 2, y + 92, 52, 96, 14, "atc", _coast())
    out.append(body)
    css += gcss
    out.append(f'<text x="{x + 12}" y="{y + h - 12}" font-size="10" fill="{SLATE2}">1,000 real flights on a globe</text>')
    return "".join(out), css


def build_hero_header(shift=None):
    W, H = 900, 68
    css, out = [], [frame(W, H, rx=10)]
    css.append("@keyframes boot{0%{opacity:.1}0.9%{opacity:.9}1.5%{opacity:.25}2.4%{opacity:1}100%{opacity:1}}")
    name = "JULIEN DEWOLFE"
    out.append(f'<g filter="url(#glow)">{pixel_text(name, 24, 20, 4, AMBER, cls_prefix="wm")}</g>')
    for i in range(len(name)):
        css.append(f".wm{i}{{animation:boot 12s linear infinite;animation-delay:{f(0.06 * i)}s;}}")
    out.append(f'<text x="{W - 24}" y="32" font-size="12" fill="{SLATE}" text-anchor="end">swe intern @ gadget.dev</text>')
    out.append(f'<text x="{W - 24}" y="48" font-size="12" fill="{SLATE}" text-anchor="end">software engineering @ uOttawa</text>')
    return shell(W, H, css, "".join(out), "Julien DeWolfe, software engineering intern at gadget.dev, software engineering student at uOttawa", shift)


HERO_MODULES = [
    ("mod-reciped", mod_reciped, "Reciped: three build progress bars filling. Links to the Reciped section below."),
    ("mod-uschedule", mod_uschedule, "uschedule.ca: a timetable assembling itself. Links to uschedule.ca."),
    ("mod-polybot", mod_polybot, "Polybot: three trading strategy sparklines. Links to the Polybot section below."),
    ("mod-netcode", mod_netcode, "Netcode: a miniature multiplayer Pong court. Links to the netcode section below."),
    ("mod-factory", mod_factory, "Software Factory: work flowing from plan through code to review and a PR. Links to the Software Factory section below."),
    ("mod-atc", mod_atc, "ATC simulator: a rotating 3D globe with Canadian flight routes. Links to the live simulator."),
]


def build_hero_modules(shift=None):
    pieces = {}
    for name, fn, label in HERO_MODULES:
        body, css = fn(0, 0, 268, 170)
        pieces[name] = shell(268, 170, css, body, label, shift)
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
    return name, shell(w, h, css, "".join(out), label, shift)


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
    body, css = globe(330, 118, 25, 48, 12, "cng", coast, meridian_step=60,
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
                        "".join(out), css, "plus game servers that survive crashes",
                        "Multiplayer netcode: client prediction, server reconciliation, and interpolation in "
                        "C#, plus Kubernetes game servers built to survive crashes.", shift)


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
    }
    outputs.update(build_hero_modules(shift))
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
