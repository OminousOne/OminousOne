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

# the page cold-boots: the header plays a terminal initialization sequence
# and every other graphic stays dark until this moment, then flickers alive
BOOT = 7.0


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

def shell(w, h, css, body, label, shift=None, hold=None, overlay=True):
    dev = f"<style>*{{animation-delay:-{f(shift)}s !important}}</style>" if shift else ""
    scan = f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="10" fill="url(#scan)" opacity="0.14"/>' if overlay else ""
    if hold:
        css = list(css)
        css.append("@keyframes bootrev{0%{opacity:0}30%{opacity:.8}55%{opacity:.15}100%{opacity:1}}")
        # the scanline overlay hides with the body, or it ghosts during boot
        body = f'<g style="animation:bootrev .5s linear both;animation-delay:{f(hold)}s">{body}{scan}</g>'
        scan = ""
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
{scan}
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
    body, gcss = globe(x + w / 2, y + 92, 52, 210, 14, "atc", _coast())
    out.append(body)
    css += gcss
    out.append(f'<text x="{x + 12}" y="{y + h - 12}" font-size="10" fill="{SLATE2}">1,000 real flights on a globe</text>')
    return "".join(out), css


def build_hero_header(shift=None):
    """the boot terminal: seven seconds of over-the-top initialization,
    then it wipes and settles into the permanent wordmark header."""
    W, H = 900, 250
    css, out = [], [frame(W, H, rx=10)]

    def at(t, dur=0.06):
        return f"animation:pop .01s linear both;animation-delay:{f(t)}s"

    css.append("@keyframes pop{from{opacity:0}to{opacity:1}}")
    css.append("@keyframes poweron{0%{transform:scaleX(0);opacity:1}55%{transform:scaleX(1);opacity:1}100%{transform:scaleX(1);opacity:0}}")
    out.append(
        f'<rect x="20" y="124" width="{W - 40}" height="2.5" fill="#EDE6D6" filter="url(#glow)" '
        f'style="animation:poweron .55s cubic-bezier(.2,.8,.3,1) both;transform-origin:{W / 2}px 0"/>'
    )
    css.append("@keyframes gone{from{opacity:1}to{opacity:0}}")
    css.append("@keyframes cursor{0%,49%{opacity:1}50%,100%{opacity:0}}")

    # ---- the spew: appears line by line, then the whole group wipes at 6.1s
    LINES = [
        (0.10, "OMINOUSONE.SYS BIOS v5.0 · phosphor check", "OK", SLATE, 0.30),
        (0.38, "memory map 0x0000..0xFFFF", "OK", SLATE, 0.55),
        (0.62, "4a 44 20 62 6f 6f 74 20 73 65 71 75 65 6e 63 65 20 1f 8b 08", None, "#2E3944", None),
        (0.80, "mount /dev/profile", "OK", SLATE, 1.00),
        (1.55, "decrypt identity", "OK", SLATE, 1.80),
        (1.90, "netlink uschedule.ca", "ONLINE", SLATE, 2.15),
        (2.20, "netlink nav-canada-simulator", "ONLINE", SLATE, 2.45),
        (2.50, "netlink reciped", "PRIVATE", SLATE, 2.75),
        (2.80, "e8 03 00 00 c7 45 fc 00 00 00 00 8b 45 fc 3b 45", None, "#2E3944", None),
        (2.95, "spawn agents [plan] [code] [code] [review]", "OK", SLATE, 3.25),
        (3.30, "calibrate globe projection 48.0deg", "OK", SLATE, 3.55),
        (3.60, "charge flux capacitor for skyline flyover", "OK", SLATE, 3.85),
        (3.90, "feed BLOB", "SQUISH", SLATE, 4.15),
        (4.20, "wake raid boss", "GRRRR", SLATE, 4.45),
        (4.50, "count crowd", "+1 (you)", SLATE, 4.75),
        (5.02, "integrity check", "PASS", SLATE, 5.55),
    ]
    spew = []
    # a bright band rolls down the terminal while it boots
    css.append("@keyframes sweep{from{transform:translateY(-30px)}to{transform:translateY(255px)}}")
    spew.append(
        f'<rect x="10" y="0" width="{W - 20}" height="24" fill="{AMBER}" opacity=".05" '
        f'style="animation:sweep 2.3s linear infinite"/>'
    )
    y = 34
    kernel_y = None
    for t, txt, stamp, color, t_stamp in LINES:
        if t == 1.55:
            kernel_y = y      # the kernel progress line takes this row
            y += 13
        spew.append(f'<text x="24" y="{y}" font-size="11" fill="{color}" style="{at(t)}">&gt; {txt}</text>')
        if stamp:
            dots = "." * max(2, 58 - len(txt))
            spew.append(f'<text x="{24 + 9 + len(txt) * 6.7}" y="{y}" font-size="11" fill="#2E3944" style="{at(t)}">{dots}</text>')
            spew.append(f'<text x="{W - 340}" y="{y}" font-size="11" fill="{AMBER}" style="{at(t_stamp)}">{stamp}</text>')
        y += 13

    # kernel progress bar between mount and decrypt
    spew.append(f'<text x="24" y="{kernel_y}" font-size="11" fill="{SLATE}" style="{at(1.05)}">&gt; load kernel dewolfe.ko</text>')
    spew.append(f'<rect x="220" y="{kernel_y - 9}" width="150" height="8" rx="2" fill="{BARBG}" style="{at(1.05)}"/>')
    css.append("@keyframes kload{from{transform:scaleX(0)}to{transform:scaleX(1)}}")
    spew.append(f'<rect x="220" y="{kernel_y - 9}" width="150" height="8" rx="2" fill="{AMBER}" style="animation:pop .01s both, kload .45s linear both;animation-delay:1.08s;transform-origin:220px 0"/>')
    spew.append(f'<text x="382" y="{kernel_y}" font-size="11" fill="{AMBER}" style="{at(1.5)}">100%</text>')

    # line one types itself out: a panel-colored cover retreats in steps
    css.append("@keyframes typed{from{transform:scaleX(1)}to{transform:scaleX(0)}}")
    spew.append(
        f'<rect x="30" y="24" width="440" height="13" fill="{BG}" '
        f'style="animation:typed .85s steps(30) both;animation-delay:.12s;transform-origin:470px 0"/>'
    )

    # spinner while the integrity check runs
    css.append("@keyframes spin4{0%,24%{opacity:1}25%,100%{opacity:0}}")
    spinner = "".join(
        f'<text x="{W - 340}" y="{y - 13}" font-size="11" fill="{AMBER}" '
        f'style="animation:spin4 .32s steps(1) infinite;animation-delay:{f(i * 0.08)}s" opacity="0">{ch}</text>'
        for i, ch in enumerate(("|", "/", "-", "\\"))
    )
    spew.append(f'<g style="animation:pop .01s both 5.02s, gone .01s both 5.5s">{spinner}</g>')

    # blinking cursor riding the bottom of the spew
    spew.append(f'<rect x="24" y="{y - 2}" width="7" height="11" fill="{AMBER}" style="animation:cursor .7s steps(1) infinite"/>')

    # ACCESS GRANTED, then the wipe
    css.append("@keyframes granted{0%{opacity:0;transform:scale(.85)}12%{opacity:1;transform:scale(1.04)}20%{opacity:1;transform:scale(1)}100%{opacity:1;transform:scale(1)}}")
    spew.append(
        f'<g style="animation:granted .5s cubic-bezier(.2,.8,.3,1) both;animation-delay:5.5s;transform-origin:{W / 2}px 130px" opacity="0">'
        f'<rect x="{W / 2 - 160}" y="104" width="320" height="52" rx="6" fill="{PANEL}" stroke="{AMBER}" stroke-opacity=".8"/>'
        f'<text x="{W / 2}" y="136" font-size="22" letter-spacing="6" fill="{AMBER}" text-anchor="middle" filter="url(#glow)">ACCESS GRANTED</text></g>'
    )
    css.append("@media (prefers-reduced-motion:reduce){.spew{display:none}}")
    css.append("@keyframes shake{0%,100%{transform:translate(0,0)}20%{transform:translate(-3px,2px)}40%{transform:translate(3px,-2px)}60%{transform:translate(-2px,-1px)}80%{transform:translate(2px,1px)}}")
    css.append("@keyframes flash{0%{opacity:0}30%{opacity:.18}100%{opacity:0}}")
    spew.append(f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="9" fill="#EDE6D6" opacity="0" style="animation:flash .22s linear both;animation-delay:5.52s"/>')
    out.append(f'<g class="spew" style="animation:gone .35s linear both;animation-delay:6.15s">'
               f'<g style="animation:shake .3s linear both;animation-delay:5.55s">{"".join(spew)}</g></g>')

    # ---- the permanent header state: wordmark boots in after the wipe
    css.append("@keyframes wmboot{0%{opacity:0}20%{opacity:.9}40%{opacity:.2}70%{opacity:1}100%{opacity:1}}")
    name = "JULIEN DEWOLFE"
    u = 5
    wm_x = (W - pixel_width(name, u)) / 2
    final = [f'<g filter="url(#glow)">{pixel_text(name, wm_x, 78, u, AMBER, cls_prefix="wm")}</g>']
    for i in range(len(name)):
        css.append(f".wm{i}{{animation:wmboot .55s linear both;animation-delay:{f(6.4 + 0.045 * i)}s;}}")
    final.append(f'<text x="{W / 2}" y="146" font-size="13" fill="{SLATE}" text-anchor="middle" style="{at(6.9)}">swe intern @ gadget.dev · software engineering @ uOttawa</text>')
    css.append("@keyframes hpulse{0%,100%{opacity:1}50%{opacity:.25}}")
    final.append(f'<circle cx="24" cy="226" r="3" fill="{AMBER}" style="animation:pop .01s both;animation-delay:7s"/>')
    final.append(f'<text x="34" y="230" font-size="11" fill="{SLATE2}" style="{at(7.0)}">boot complete in 7.0s · all systems nominal · scroll down</text>')
    final.append(f'<text x="{W - 24}" y="230" font-size="11" fill="{SLATE2}" text-anchor="end" style="{at(7.0)}">refresh to reboot</text>')
    final.append(f'<g style="{at(7.1)}"><rect x="352" y="221" width="6" height="10" fill="{AMBER}" style="animation:cursor .8s steps(1) infinite"/></g>')
    out.append("".join(final))

    label = ("Boot terminal: a seven second initialization sequence with BIOS checks, netlinks coming "
             "online, agents spawning and an access granted stamp, which then wipes into the permanent "
             "header: Julien DeWolfe, swe intern at gadget.dev, software engineering at uOttawa.")
    return shell(W, H, css, "".join(out), label, shift)


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
        pieces[name] = shell(268, 170, css, body, label, shift)
    return pieces


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
        ("I'm Julien DeWolfe, a Software Engineering student at the University of Ottawa who started", 12.5, SLATE),
        ("making games in Blender's node-based engine at age 9. That turned into Unity, C#, game jams,", 12.5, SLATE),
        ("networking rabbit holes, and eventually a fascination with systems and engineering in general.", 12.5, SLATE),
        ("Right now I'm an intern at gadget.dev while finishing my degree.", 12.5, SLATE),
    ]
    panels.append(_text_panel("text-intro", bio,
                              "Bio: Julien DeWolfe, Software Engineering student at the University of Ottawa, started "
                              "making games in Blender's node-based engine at age 9, then Unity, C#, game jams and "
                              "networking rabbit holes. Currently an intern at gadget.dev.", shift=shift))

    def section(name, title, sub, label):
        W, H = 830, 56
        out = [
            f'<text x="0" y="24" font-size="15" letter-spacing="2.5" fill="{AMBER}">{title}</text>',
            f'<text x="{W}" y="24" font-size="10.5" fill="{SLATE2}" text-anchor="end">{sub}</text>',
            f'<line x1="0" y1="38" x2="{W}" y2="38" stroke="#262E36"/>',
            f'<line x1="0" y1="38" x2="120" y2="38" stroke="{AMBER}" stroke-opacity=".7" stroke-width="1.5"/>',
        ]
        return name, shell(W, H, [], "".join(out), label, shift, hold=BOOT + 0.4, overlay=False)

    panels.append(section("sect-projects", "PROJECTS", "selected work, most recent first",
                          "Section: projects. Selected work, most recent first."))
    panels.append(section("sect-stats", "A YEAR ON GITHUB", "fetched live from the api on every view",
                          "Section: a year on GitHub, fetched live from the API on every view."))
    panels.append(section("sect-guestbook", "GUESTBOOK", "signed by visitors, through github issues",
                          "Section: guestbook, signed by visitors through GitHub issues."))
    panels.append(section("sect-games", "FUN AND GAMES", "everyone plays the same board · moves land in about a minute",
                          "Section: fun and games. Everyone plays the same board, each move is a pre-filled GitHub "
                          "issue and the page updates within a minute or two."))

    outro = [
        ("I made Conway's Game of Life run inside Minecraft as a teenager.", 12.5, SLATE),
        ("Now it runs inside my GitHub profile, and you are all gardening it.", 12.5, SLATE),
    ]
    panels.append(_text_panel("text-life", outro,
                              "I made Conway's Game of Life run inside Minecraft as a teenager. Now it runs inside "
                              "my GitHub profile, and you are all gardening it.", shift=shift))
    return dict(panels)


# ------------------------------------------------------------- buttons
# every link button, regenerated with the boot hold baked in

BUTTONS = {
    "btn-linkedin": "[ linkedin ]",
    "btn-uschedule": "[ uschedule.ca ]",
    "btn-gadget": "[ gadget.dev ]",
    "btn-sign": "[ sign the guestbook ]",
    "btn-attack": "[ attack the boss ]",
    "btn-feed": "[ feed blob ]",
    "btn-pet": "[ pet blob ]",
    "btn-pixel": "[ place a pixel ]",
    "btn-cell": "[ plant a cell ]",
}


def build_buttons(shift=None):
    pieces = {}
    for name, text in BUTTONS.items():
        w = len(text) * 8 + 36
        body = (
            f'<rect x="0.75" y="0.75" width="{f(w - 1.5)}" height="34.5" rx="4" fill="{BG}" stroke="{AMBER}" stroke-opacity="0.45"/>'
            f'<path d="M5 9 V5 H9 M{w - 9} 5 H{w - 5} V9 M{w - 5} 27 V31 H{w - 9} M9 31 H5 V27" fill="none" stroke="{AMBER}" stroke-opacity="0.7" stroke-width="1.4"/>'
            f'<text x="{f(w / 2)}" y="22.5" text-anchor="middle" font-size="13" fill="{AMBER}">{text}</text>'
        )
        pieces[name] = shell(w, 36, [], body, text.strip("[ ]"), shift, hold=BOOT + 0.5)
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
    return shell(W, H, css, "".join(out), label, shift, hold=BOOT + 0.4)


# ------------------------------------------------------------- 3d skyline
# the contribution year extruded into a bar city, rendered in real 3D the
# same way as the globe: rotate, project, painter-sort, bake frames.

def build_skyline(shift=None, camera="flyover", fly_phi=48, fly_tilt=35):
    data = json.load(open(os.path.join(ROOT, "tools", "skyline-data.json")))
    weeks = data["weeks"]
    counts = sorted(c for w in weeks for c in w if c > 0)
    vmax = counts[-1] if counts else 1

    W, H = 830, 260
    cx, cy = W / 2, 170 if camera == "flyover" else 158
    N, DUR = 44, 10.0
    TILT = math.radians(fly_tilt if camera == "flyover" else 26)
    ct, st = math.cos(TILT), math.sin(TILT)
    ux, uz = 13.0, 15.0          # week and weekday spacing
    bw, bd = 8.6, 9.4            # bar footprint, gapped so towers read apart
    x_off, z_off = (len(weeks) - 1) / 2, 3.0

    # a full turntable brings the long axis toward the camera, which needs
    # a smaller scale to stay inside the card; the flyover renders larger
    # than the card and lets the camera glide along it
    scale = {"turntable": 0.78, "flyover": 1.42}.get(camera, 1.0)

    def project(x, y, z, phi):
        cp, sp = math.cos(phi), math.sin(phi)
        x2 = x * cp + z * sp
        z2 = -x * sp + z * cp
        py = y * ct - z2 * st
        depth = y * st + z2 * ct
        return cx + x2 * scale, cy - py * scale, depth

    def bucket(c):
        return min(3, int(4 * counts.index(c) / len(counts)))

    bars = []
    tallest = None
    for wi, week in enumerate(weeks):
        for di, c in enumerate(week):
            if c > 0:
                h = 5 + 58 * math.sqrt(c / vmax)
                bar = ((wi - x_off) * ux, (di - z_off) * uz, h, bucket(c))
                bars.append(bar)
                if c == vmax and tallest is None:
                    tallest = bar

    def face(corners, phi, cls):
        pts = [project(x, y, z, phi) for x, y, z in corners]
        d = "M" + "L".join(f"{round(px)},{round(py)}" for px, py, _ in pts) + "Z"
        return f'<path class="{cls}" d="{d}"/>'

    # lighting: brightness follows the day's count, same scale as the heatmap
    css = []
    tops = (0.5, 0.66, 0.83, 1.0)
    for b, a in enumerate(tops):
        css.append(f".kt{b}{{fill:{AMBER};fill-opacity:{f(a)}}}")
        css.append(f".kl{b}{{fill:{AMBER};fill-opacity:{f(a * 0.48)}}}")
        css.append(f".kr{b}{{fill:{AMBER};fill-opacity:{f(a * 0.22)}}}")
    sel = ",".join(f".kt{b},.kl{b},.kr{b}" for b in range(4))
    css.append(f"{sel}{{stroke:#05070A;stroke-width:.6;stroke-linejoin:round}}")
    css.append("@keyframes skyrise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}")

    out = [frame(W, H, rx=10)]
    out.append('<g style="animation:skyrise .8s cubic-bezier(.25,.6,.3,1) both;animation-delay:.15s">')

    px2, pz2 = x_off * ux + 15, z_off * uz + 13

    def render_frame(phi, mid_extra=""):
        """one fully-culled render of the city at rotation phi (any angle).
        mid_extra is injected between the platform and the towers, so things
        like street traffic pass behind the buildings."""
        cp, sp = math.cos(phi), math.sin(phi)
        el = []

        # platform slab: top plus whichever two skirts face the camera
        top = [(-px2, 0, -pz2), (px2, 0, -pz2), (px2, 0, pz2), (-px2, 0, pz2)]
        skirts = [
            (cp, [top[3], top[2], (px2, -7, pz2), (-px2, -7, pz2)]),       # +z
            (-cp, [top[1], top[0], (-px2, -7, -pz2), (px2, -7, -pz2)]),    # -z
            (-sp, [top[2], top[1], (px2, -7, -pz2), (px2, -7, pz2)]),      # +x
            (sp, [top[0], top[3], (-px2, -7, pz2), (-px2, -7, -pz2)]),     # -x
        ]
        for vis, quad in skirts:
            if vis > 0.001:
                pts = [project(*p, phi) for p in quad]
                d = "M" + "L".join(f"{round(px)},{round(py)}" for px, py, _ in pts) + "Z"
                el.append(f'<path d="{d}" fill="#0B0E12" stroke="#232B33" stroke-width=".6"/>')
        tp = [project(*p, phi) for p in top]
        d = "M" + "L".join(f"{round(px)},{round(py)}" for px, py, _ in tp) + "Z"
        el.append(f'<path d="{d}" fill="{PANEL}" stroke="#2A333C" stroke-width=".8"/>')
        for qw in (13, 26, 39):
            qx = (qw - x_off) * ux
            a = project(qx, 0.3, -pz2 + 3, phi)
            b = project(qx, 0.3, pz2 - 3, phi)
            el.append(f'<line x1="{round(a[0])}" y1="{round(a[1])}" x2="{round(b[0])}" y2="{round(b[1])}" stroke="#1E262E" stroke-width=".7"/>')
        if mid_extra:
            el.append(mid_extra)

        for bx, bz, h, bk in sorted(bars, key=lambda b: project(b[0], 0, b[1], phi)[2]):
            x0, x1 = bx - bw / 2, bx + bw / 2
            z0, z1 = bz - bd / 2, bz + bd / 2
            zface = [(x0, h, z1), (x1, h, z1), (x1, 0, z1), (x0, 0, z1)] if cp > 0 else \
                    [(x1, h, z0), (x0, h, z0), (x0, 0, z0), (x1, 0, z0)]
            xface = [(x0, h, z0), (x0, h, z1), (x0, 0, z1), (x0, 0, z0)] if sp > 0 else \
                    [(x1, h, z1), (x1, h, z0), (x1, 0, z0), (x1, 0, z1)]
            if abs(cp) > 0.001:
                el.append(face(zface, phi, f"kl{bk}"))
            if abs(sp) > 0.001:
                el.append(face(xface, phi, f"kr{bk}"))
            el.append(face([(x0, h, z0), (x1, h, z0), (x1, h, z1), (x0, h, z1)], phi, f"kt{bk}"))
        return el

    def tag(phi):
        # tag the tallest tower: a small backed chip so it reads at any zoom
        tx, tz, th, _ = tallest
        tp1 = project(tx, th, tz, phi)
        tipy = max(round(tp1[1]) - 18, 40)
        label_txt = f"{vmax} in one day"
        tw = len(label_txt) * 5.6 + 12
        bx0 = round(tp1[0]) - 8 - tw
        return (
            f'<line x1="{round(tp1[0])}" y1="{round(tp1[1])}" x2="{round(tp1[0])}" y2="{tipy + 2}" stroke="{AMBER}" stroke-opacity=".6" stroke-width=".8"/>'
            f'<circle cx="{round(tp1[0])}" cy="{tipy}" r="1.6" fill="{AMBER}"/>'
            f'<rect x="{f(bx0)}" y="{tipy - 9}" width="{f(tw)}" height="16" rx="3" fill="{PANEL}" fill-opacity=".92" stroke="#2A333C" stroke-width=".7"/>'
            f'<text x="{f(bx0 + tw / 2)}" y="{tipy + 3}" font-size="9" fill="{AMBER}" text-anchor="middle">{label_txt}</text>'
        )

    if camera == "flyover":
        # one fixed-angle render, then the CAMERA moves: pure CSS pan and
        # zoom, browser-interpolated, so motion is smooth with no frames
        PHI = math.radians(34)

        # street traffic: cars run the lanes between tower rows, drawn under
        # the buildings so they disappear behind them
        cars = []
        lanes = [(-2.5, 11.0, 1), (-0.5, 14.0, -1), (1.5, 9.5, 1), (3.4, 12.5, -1)]
        for li, (lane, dur, direction) in enumerate(lanes):
            zl = lane * uz
            a = project(-px2 + 6, 0.8, zl, PHI)
            bpt = project(px2 - 6, 0.8, zl, PHI)
            if direction < 0:
                a, bpt = bpt, a
            dx, dy = bpt[0] - a[0], bpt[1] - a[1]
            for ci in range(2):
                p = f"car{li}_{ci}"
                css.append(f"@keyframes {p}{{from{{transform:translate(0,0)}}to{{transform:translate({f(dx)}px,{f(dy)}px)}}}}")
                delay = -(dur * (0.13 + 0.47 * ci + 0.19 * li))
                op = 0.9 if (li + ci) % 2 == 0 else 0.55
                cars.append(
                    f'<circle cx="{f(a[0])}" cy="{f(a[1])}" r="1.7" fill="{AMBER}" opacity="{op}" '
                    f'style="animation:{p} {f(dur)}s linear infinite;animation-delay:{f(delay)}s"/>'
                )

        # the chip-backed tag stays readable at any zoom, so it flies along
        scene = "".join(render_frame(PHI, mid_extra="".join(cars))) + tag(PHI)

        # a slow beacon on the tallest tower
        css.append("@keyframes beacon{0%,100%{opacity:1}50%{opacity:.15}}")
        tx_, tz_, th_, _ = tallest
        bp = project(tx_, th_ + 2, tz_, PHI)
        scene += f'<circle cx="{f(bp[0])}" cy="{f(bp[1])}" r="1.5" fill="{AMBER}" style="animation:beacon 2.4s ease-in-out infinite"/>'

        # camera path: whole city, dive to the quiet end, glide the year,
        # hold on downtown, pull back out. focus points are computed, not guessed
        s = 1.45
        C = (W / 2, 145)
        jan = project((2 - x_off) * ux, 16, 0, PHI)
        jun = project((47 - x_off) * ux, 30, 0, PHI)
        focus = {13: jan, 17: jan, 63: jun, 71: jun}
        stops = [
            (0, True, "ease-in-out"), (13, False, "ease-in-out"), (17, False, "linear"),
            (63, False, "ease-in-out"), (71, False, "ease-in-out"), (86, True, "ease-in-out"),
            (100, True, "linear"),
        ]
        kf = []
        for t, whole, ease in stops:
            if whole:
                tx, ty, sc = 0, 0, 1.0
            else:
                px, py = focus[t][0], focus[t][1]
                tx, ty, sc = C[0] - s * px, C[1] - s * py, s
            kf.append(f"{t}%{{transform:translate({f(tx)}px,{f(ty)}px) scale({f(sc)});animation-timing-function:{ease}}}")
        css.append("@keyframes flyover{" + "".join(kf) + "}")
        out.append(f'<clipPath id="skclip"><rect x="8" y="36" width="{W - 16}" height="{H - 62}" rx="6"/></clipPath>')
        out.append(f'<g clip-path="url(#skclip)"><g style="animation:flyover 28s infinite">{scene}</g></g>')
        frames = []
    elif camera == "fixed":
        out.append("".join(render_frame(math.radians(34))) + tag(math.radians(34)))
        frames = []
    elif camera == "flyover":
        # one static render, camera motion is a pure CSS glide: perfectly
        # smooth because nothing is re-rendered, just translated
        phi = math.radians(fly_phi)
        cp, sp = math.cos(phi), math.sin(phi)
        amp = 80.0
        ax, ay = amp * cp, -amp * sp * st * 0.5
        css.append(
            f"@keyframes fly{{0%{{transform:translate({f(ax)}px,{f(ay)}px) scale(1)}}"
            f"50%{{transform:translate({f(-ax)}px,{f(-ay)}px) scale(1.06)}}"
            f"100%{{transform:translate({f(ax)}px,{f(ay)}px) scale(1)}}}}"
        )
        out.append(f'<clipPath id="skc"><rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="9"/></clipPath>')
        out.append(
            f'<g clip-path="url(#skc)"><g style="animation:fly 30s cubic-bezier(.42,0,.58,1) infinite;'
            f'transform-origin:{f(cx)}px {f(cy - 30)}px">'
            + "".join(render_frame(phi)) + tag(phi) + "</g></g>"
        )
        frames = []
    else:
        if camera == "turntable":
            N, DUR = 96, 22.0
        else:
            N, DUR = 72, 12.0
        frames = []
        for fi in range(N):
            if camera == "turntable":
                phi = math.radians(28) + 2 * math.pi * fi / N
            else:
                # swing between 10 and 46 degrees: always oblique, never edge-on
                phi = math.radians(28 + 18 * math.sin(2 * math.pi * fi / N))
            frames.append("".join(render_frame(phi)) + tag(phi))

    # hard frame cuts: partial-opacity blends of line art shimmer, so
    # smoothness comes from frame count and small angle steps instead
    for fi, content in enumerate(frames):
        p = f"skf{fi}"
        t0, t1 = fi / N * 100, (fi + 1) / N * 100
        if fi == 0:
            css.append(f"@keyframes {p}{{0%{{opacity:1}}{f(t1 - 0.004)}%{{opacity:1}}{f(t1)}%{{opacity:0}}100%{{opacity:0}}}}")
            base = 1
        else:
            css.append(
                f"@keyframes {p}{{0%,{f(t0 - 0.004)}%{{opacity:0}}{f(t0)}%{{opacity:1}}"
                f"{f(t1 - 0.004)}%{{opacity:1}}{f(t1)}%{{opacity:0}}100%{{opacity:0}}}}"
            )
            base = 0
        css.append(f".{p}{{animation:{p} {f(DUR)}s linear infinite;}}")
        out.append(f'<g class="{p}" opacity="{base}">{content}</g>')

    out.append("</g>")
    out.append(f'<text x="18" y="29" font-size="12" letter-spacing="1.6" fill="{AMBER}">SKYLINE</text>')
    out.append(f'<text x="{W - 18}" y="29" font-size="10" fill="{SLATE2}" text-anchor="end">the same year, extruded</text>')
    out.append(f'<text x="18" y="{H - 14}" font-size="10" fill="{SLATE2}">{data["total"]:,} contributions as a city · one tower per day</text>')
    label = (f"Skyline: the contribution year as a 3D bar city, one tower per active day, "
             f"{data['total']:,} contributions total.")
    return shell(W, H, css, "".join(out), label, shift, hold=BOOT + 0.4)


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
    }
    outputs.update(build_text_panels(shift))
    outputs.update(build_buttons(shift))
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
