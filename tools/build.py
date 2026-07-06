#!/usr/bin/env python3
"""
build.py generates every SVG asset for the profile README.

No JavaScript, no GIFs: each graphic is a single SVG whose animation is baked
into CSS keyframes, which GitHub preserves inside <img>-embedded SVGs.

Outputs:
  assets/hero.svg          mission-control board, one animated module per project
  assets/banner-*.svg      one slim animated banner per project section
  assets/stats.svg         contribution heatmap + language mix from real data
                           (refresh tools/github-data.json to update the numbers)

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
    out.append(f'<text x="{W - 24}" y="32" font-size="12" fill="{SLATE}" text-anchor="end">software engineer @ gadget.dev</text>')
    out.append(f'<text x="{W - 24}" y="48" font-size="12" fill="{SLATE}" text-anchor="end">software engineering @ uOttawa</text>')
    return shell(W, H, css, "".join(out), "Julien DeWolfe, software engineer at gadget.dev, software engineering student at uOttawa", shift)


def build_hero_footer(gh, shift=None):
    W, H = 900, 44
    css, out = [], [frame(W, H, rx=10)]
    total = f"{gh['total_contributions_past_year']:,}"
    out.append(
        f'<text x="24" y="27" font-size="11.5" fill="{SLATE}">past year on github: '
        f'<tspan fill="{AMBER}">{total}</tspan> contributions · busiest day: <tspan fill="{AMBER}">{gh["busiest_day"]}</tspan></text>'
    )
    css.append("@keyframes hpulse{0%,100%{opacity:1}50%{opacity:.25}}")
    out.append(f'<circle cx="745" cy="23" r="3" fill="{AMBER}" style="animation:hpulse 2s ease-in-out infinite"/>')
    out.append(f'<text x="{W - 24}" y="27" font-size="11.5" fill="{SLATE}" text-anchor="end">selected projects</text>')
    return shell(W, H, css, "".join(out), f"Past year on GitHub: {total} contributions, busiest day {gh['busiest_day']}", shift)


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


# ------------------------------------------------------------- banners

def banner_shell(name, title, status, motif, motif_css, label, shift=None):
    W, H = 830, 64
    css = list(motif_css)
    out = [frame(W, H, rx=8)]
    out.append(f'<text x="18" y="39" font-size="14" letter-spacing="2" fill="{AMBER}">{title}</text>')
    out.append(f'<text x="{W - 18}" y="39" font-size="10" letter-spacing="1" fill="{SLATE2}" text-anchor="end">{status}</text>')
    out.append(f'<g transform="translate(-118,0)">{motif}</g>')
    return name, shell(W, H, css, "".join(out), label, shift)


def banner_reciped(shift=None):
    css, out = [], []
    for i, to in enumerate((0.86, 0.76, 0.44)):
        by = 20 + i * 9
        p = f"brc{i}"
        out.append(f'<rect x="560" y="{by}" width="150" height="4" rx="1.5" fill="{BARBG}"/>')
        out.append(f'<rect x="560" y="{by}" width="150" height="4" rx="1.5" fill="{AMBER}" opacity="0.9" class="{p}" style="transform:scaleX({f(to)});transform-origin:560px 0"/>')
        css.append(f"@keyframes {p}{{0%,{6 + i * 5}%{{transform:scaleX(0)}}{30 + i * 5}%,88%{{transform:scaleX({f(to)})}}96%,100%{{transform:scaleX(0)}}}}")
        css.append(f".{p}{{animation:{p} 9s cubic-bezier(.3,.6,.3,1) infinite;}}")
    return banner_shell("banner-reciped", "RECIPED", "IN DEVELOPMENT", "".join(out), css,
                        "Reciped banner with three build progress bars", shift)


def banner_uschedule(shift=None):
    css, out = [], []
    for i in range(8):
        p = f"bus{i}"
        bx = 560 + (i % 4) * 40
        by = 16 + (i // 4) * 18
        css.append(f"@keyframes {p}{{0%,{5 + i * 6}%{{opacity:0}}{9 + i * 6}%,86%{{opacity:1}}93%,100%{{opacity:0}}}}")
        css.append(f".{p}{{animation:{p} 10s linear infinite;}}")
        out.append(f'<rect x="{bx}" y="{by}" width="34" height="14" rx="2" fill="{AMBER}" fill-opacity="0.28" stroke="{AMBER}" stroke-opacity="0.8" class="{p}"/>')
    return banner_shell("banner-uschedule", "USCHEDULE.CA", "LIVE", "".join(out), css,
                        "uschedule.ca banner with course blocks filling a timetable", shift)


def banner_factory(shift=None):
    css, out = [], []
    xs = [566, 630, 694, 758]
    labels = ["plan", "code", "review", "PR"]
    for nx, lb in zip(xs, labels):
        out.append(f'<rect x="{nx}" y="22" width="44" height="20" rx="3" fill="{SCREEN}" stroke="#2A333C"/>')
        out.append(f'<text x="{nx + 22}" y="35" font-size="9" fill="{SLATE}" text-anchor="middle">{lb}</text>')
    for i in range(3):
        out.append(f'<line x1="{xs[i] + 44}" y1="32" x2="{xs[i + 1]}" y2="32" stroke="#232B33"/>')
    css.append(
        f"@keyframes bsf{{0%{{transform:translateX(610px);opacity:0}}6%{{opacity:1}}"
        f"30%{{transform:translateX(630px)}}45%{{transform:translateX(674px)}}"
        f"66%{{transform:translateX(694px)}}80%{{transform:translateX(738px)}}"
        f"92%{{transform:translateX(758px);opacity:1}}100%{{opacity:0}}}}"
    )
    css.append(".bsf{animation:bsf 4.5s linear infinite;}")
    out.append(f'<circle cy="32" r="2.4" fill="{AMBER}" class="bsf" opacity="0"/>')
    return banner_shell("banner-factory", "SOFTWARE FACTORY", "AI DEV PIPELINE", "".join(out), css,
                        "Software Factory banner with work flowing from plan to code to review to PR", shift)


def banner_polybot(shift=None):
    css, out = [], []
    css.append("@keyframes bpb{from{transform:translateX(0)}to{transform:translateX(-230px)}}")
    out.append(
        '<clipPath id="bpbc"><rect x="560" y="14" width="230" height="36"/></clipPath>'
        f'<g clip-path="url(#bpbc)"><g transform="translate(560,32)">'
        f'<path d="{spark_path(seed=23, width=230, amp=9)}" fill="none" stroke="{AMBER}" stroke-width="1.2" opacity="0.75" style="animation:bpb 16s linear infinite"/></g></g>'
    )
    return banner_shell("banner-polybot", "POLYBOT", "PAPER TRADING", "".join(out), css,
                        "Polybot banner with a scrolling market sparkline", shift)


def banner_navsim(shift=None):
    coast = [ring[::2] for ring in _coast() if len(ring) >= 12]
    body, css = globe(700, 32, 25, 48, 12, "bng", coast, meridian_step=60,
                      coast_width=0.7, routes=ROUTES[:2], dots=False)
    return banner_shell("banner-navsim", "NAV CANADA SIMULATOR", "AIR TRAFFIC CONTROL", body, css,
                        "NAV Canada simulator banner with a small rotating 3D globe", shift)


def banner_netcode(shift=None):
    css, out = [], []
    out.append(f'<rect x="560" y="14" width="230" height="36" fill="{SCREEN}" stroke="{LINE}"/>')
    out.append(f'<line x1="675" y1="18" x2="675" y2="46" stroke="{LINE}" stroke-dasharray="2 4"/>')
    css.append(
        "@keyframes bnc{0%{transform:translate(572px,40px)}25%{transform:translate(640px,20px)}"
        "50%{transform:translate(778px,34px)}75%{transform:translate(690px,46px)}100%{transform:translate(572px,40px)}}"
    )
    css.append(".bnc{animation:bnc 4.6s linear infinite;}")
    out.append(f'<rect x="-2" y="-2" width="4" height="4" fill="{AMBER}" class="bnc" style="transform:translate(572px,40px)"/>')
    css.append("@keyframes bncl{0%,100%{transform:translateY(38px)}40%{transform:translateY(24px)}}")
    css.append("@keyframes bncr{0%,100%{transform:translateY(30px)}50%{transform:translateY(36px)}}")
    out.append(f'<rect x="566" y="-7" width="3" height="14" fill="{AMBER}" style="animation:bncl 4.6s ease-in-out infinite;transform:translateY(38px)"/>')
    out.append(f'<rect x="783" y="-7" width="3" height="14" fill="{AMBER}" style="animation:bncr 4.6s ease-in-out infinite;transform:translateY(30px)"/>')
    return banner_shell("banner-netcode", "MULTIPLAYER NETCODE", "C# · KUBERNETES", "".join(out), css,
                        "Multiplayer netcode banner with a miniature pong rally", shift)


def banner_earlier(shift=None):
    css, out = [], []
    cells = [(0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (1, 1), (2, 1), (4, 1), (2, 0)]
    for i, (c, r) in enumerate(cells):
        p = f"bev{i}"
        css.append(f"@keyframes {p}{{0%,{4 + i * 5}%{{opacity:0}}{8 + i * 5}%,88%{{opacity:1}}94%,100%{{opacity:0}}}}")
        css.append(f".{p}{{animation:{p} 12s linear infinite;}}")
        op = 0.9 if r == 2 else 0.65 if r == 1 else 0.45
        out.append(f'<rect x="{620 + c * 15}" y="{18 + (2 - r) * 11}" width="13" height="9" fill="{AMBER}" opacity="{op}" class="{p}"/>')
    return banner_shell("banner-earlier", "EARLIER WORK", "2018 TO 2024", "".join(out), css,
                        "Earlier work banner with pixel blocks stacking up", shift)


# ------------------------------------------------------------- stats

def build_stats(gh, shift=None):
    W, H = 830, 172
    css, out = [], [frame(W, H, rx=10)]
    weeks = gh["weeks"]
    nz = sorted(c for w in weeks for c in w if c > 0)

    def level(c):
        if c == 0:
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
    total = f"{gh['total_contributions_past_year']:,}"
    out.append(f'<text x="24" y="{f(ty)}" font-size="12" fill="{SLATE}"><tspan fill="{AMBER}" font-size="15">{total}</tspan> contributions in the past year</text>')
    out.append(f'<text x="{W - 24}" y="{f(ty)}" font-size="12" fill="{SLATE}" text-anchor="end">busiest day: <tspan fill="{AMBER}" font-size="15">{gh["busiest_day"]}</tspan></text>')

    label = (f"GitHub activity: {total} contributions in the past year shown as a heatmap, "
             f"busiest day {gh['busiest_day']}.")
    return shell(W, H, css, "".join(out), label, shift)


# ------------------------------------------------------------- fun cards

SW, SH = 268, 170  # stat cards match the hero modules


def build_stat_clock(gh, shift=None):
    hours = gh["commit_hours"]
    total = gh["commit_hours_total"]
    peak = hours.index(max(hours))
    evening = round(sum(v for h, v in enumerate(hours) if h >= 18 or h < 4) / total * 100)
    css, out = [], [module_box(0, 0, SW, SH, "COMMIT CLOCK", "BY HOUR")]

    cx, cy, r0 = 70, 96, 20
    vmax = max(hours)
    css.append("@keyframes cbar{from{transform:scaleY(0)}to{transform:scaleY(1)}}")
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r0 - 4}" fill="none" stroke="{LINE}"/>')
    for h, v in enumerate(hours):
        ln = 3 + 22 * v / vmax
        a = 0.28 + 0.72 * v / vmax
        w_ = 3.2 if h == peak else 2.2
        out.append(
            f'<g transform="translate({cx},{cy}) rotate({h * 15})">'
            f'<line x1="0" y1="{-r0}" x2="0" y2="{f(-r0 - ln)}" stroke="{AMBER}" stroke-opacity="{f(a)}" '
            f'stroke-width="{w_}" style="animation:cbar .6s cubic-bezier(.3,.6,.3,1) both;'
            f'animation-delay:{f(0.04 * h)}s;transform-origin:0px {-r0}px"/></g>'
        )
    out.append(f'<text x="{cx}" y="{cy - 49}" font-size="7" fill="{SLATE2}" text-anchor="middle">00</text>')
    out.append(f'<text x="{cx}" y="{cy + 55}" font-size="7" fill="{SLATE2}" text-anchor="middle">12</text>')

    # quietest stretch: the longest circular run of hours under 10% of peak
    lo = [v < 0.1 * vmax for v in hours]
    best_len = best_start = 0
    for start in range(24):
        ln = 0
        while ln < 24 and lo[(start + ln) % 24]:
            ln += 1
        if ln > best_len:
            best_len, best_start = ln, start
    q0, q1 = best_start, (best_start + best_len) % 24
    hr = lambda h: f"{h % 12 if h % 12 else 12}"
    quiet = f"{hr(q0)} to {hr(q1)} {'am' if q1 < 12 else 'pm'}"

    fx = 134
    ampm = lambda h: f"{h % 12 if h % 12 else 12} {'am' if h < 12 else 'pm'}"
    out.append(f'<text x="{fx}" y="66" font-size="11" fill="{SLATE}">peak: <tspan fill="{AMBER}" font-size="14">{ampm(peak)}</tspan></text>')
    out.append(f'<text x="{fx}" y="94" font-size="11" fill="{SLATE}"><tspan fill="{AMBER}" font-size="14">{evening}%</tspan> after 6 pm</text>')
    out.append(f'<text x="{fx}" y="122" font-size="11" fill="{SLATE}">quiet: <tspan fill="{AMBER}">{quiet}</tspan></text>')
    out.append(f'<text x="12" y="{SH - 12}" font-size="10" fill="{SLATE2}">{total:,} commits, by hour of day</text>')
    label = f"Commit clock: a 24 hour dial of {total:,} commits. Peak hour {ampm(peak)}, {evening} percent after 6 pm."
    return shell(SW, SH, css, "".join(out), label, shift)


def odometer(x, y, value, size, dur, prefix, css):
    """digits roll up to their final value once, odometer style."""
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


def build_stat_streaks(gh, shift=None):
    s = gh["streaks"]
    css, out = [], [module_box(0, 0, SW, SH, "STREAKS", "PAST YEAR")]
    out.append(f'<text x="16" y="52" font-size="11" fill="{SLATE}">longest streak</text>')
    out.append(odometer(16, 90, s["longest"], 30, 0.9, "odl_", css))
    out.append(f'<text x="{16 + len(str(s["longest"])) * 19 + 8}" y="90" font-size="11" fill="{SLATE2}">days in a row</text>')
    out.append(f'<text x="16" y="124" font-size="11" fill="{SLATE}">active days</text>')
    out.append(odometer(102, 124, s["active_days"], 16, 0.7, "oda_", css))
    out.append(f'<text x="{102 + len(str(s["active_days"])) * 10 + 8}" y="124" font-size="11" fill="{SLATE2}">of {s["window_days"]}</text>')
    out.append(f'<text x="12" y="{SH - 12}" font-size="10" fill="{SLATE2}">from the contribution calendar</text>')
    label = f"Streaks: longest streak {s['longest']} days, {s['active_days']} active days of {s['window_days']}."
    return shell(SW, SH, css, "".join(out), label, shift)


def build_stat_weekdays(gh, shift=None):
    vals = gh["commit_days_mon_sun"]
    total = sum(vals)
    weekend = round((vals[5] + vals[6]) / total * 100)
    vmax = max(vals)
    peak_i = vals.index(vmax)
    css, out = [], [module_box(0, 0, SW, SH, "WEEKDAYS", "COMMITS")]
    css.append("@keyframes wbar{from{transform:scaleY(0)}to{transform:scaleY(1)}}")
    bx, base, bw = 26, 122, 22
    for i, v in enumerate(vals):
        h_ = 8 + 66 * v / vmax
        a = 1.0 if i == peak_i else 0.45 + 0.3 * v / vmax
        out.append(
            f'<rect x="{bx + i * 31}" y="{f(base - h_)}" width="{bw}" height="{f(h_)}" rx="2" fill="{AMBER}" '
            f'opacity="{f(a)}" style="animation:wbar .55s cubic-bezier(.3,.6,.3,1) both;'
            f'animation-delay:{f(0.06 * i)}s;transform-origin:0px {base}px"/>'
        )
        out.append(f'<text x="{bx + i * 31 + bw / 2}" y="136" font-size="8" fill="{SLATE2}" text-anchor="middle">{"mtwtfss"[i]}</text>')
    daynames = ["mondays", "tuesdays", "wednesdays", "thursdays", "fridays", "saturdays", "sundays"]
    out.append(f'<text x="12" y="{SH - 12}" font-size="10" fill="{SLATE2}">{daynames[peak_i]} lead · weekends get {weekend}%</text>')
    label = f"Commits by weekday: {daynames[peak_i]} lead, weekends get {weekend} percent."
    return shell(SW, SH, css, "".join(out), label, shift)


def build_stat_langs(gh, shift=None):
    import math as _m
    langs = gh["languages_active_projects"]
    css, out = [], [module_box(0, 0, SW, SH, "LANGUAGES", "ACTIVE REPOS")]
    cx, cy, r = 64, 96, 34
    circ = 2 * _m.pi * r
    ops = {"TypeScript": 1.0, "JavaScript": 0.45, "Dart": 0.3, "GraphQL": 0.2, "other": None}
    css.append("@keyframes din{from{opacity:0;transform:rotate(-40deg)}to{opacity:1;transform:rotate(0deg)}}")
    segs = []
    acc = 0.0
    for name, pct_ in langs.items():
        seg = circ * pct_ / 100
        color = f'stroke="{AMBER}" stroke-opacity="{ops[name]}"' if ops[name] else 'stroke="#2A333C"'
        segs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" {color} stroke-width="11" '
            f'stroke-dasharray="{f(max(seg - 2, 1))} {f(circ - max(seg - 2, 1))}" '
            f'stroke-dashoffset="{f(-acc)}" transform="rotate(-90 {cx} {cy})"/>'
        )
        acc += seg
    out.append(
        f'<g style="animation:din .9s cubic-bezier(.3,.6,.3,1) both;transform-origin:{cx}px {cy}px">'
        + "".join(segs) + "</g>"
    )
    top = max(langs, key=lambda k: langs[k] if k != "other" else 0)
    out.append(f'<text x="{cx}" y="{cy + 4}" font-size="12" fill="{AMBER}" text-anchor="middle">{f(round(langs[top]))}%</text>')
    ry = 56
    for name, pct_ in langs.items():
        if name == "other":
            continue
        sw = f'fill="{AMBER}" opacity="{ops[name]}"'
        out.append(f'<rect x="128" y="{ry - 8}" width="9" height="9" rx="2" {sw}/>')
        out.append(f'<text x="144" y="{ry}" font-size="10.5" fill="{SLATE}">{name.lower()} <tspan fill="{SLATE2}">{f(round(pct_))}%</tspan></text>')
        ry += 24
    out.append(f'<text x="12" y="{SH - 12}" font-size="10" fill="{SLATE2}">by lines of code, repos I work in now</text>')
    lbl = ", ".join(f"{n} {round(p)} percent" for n, p in langs.items() if n != "other")
    return shell(SW, SH, css, "".join(out), f"Languages across active repos by lines of code: {lbl}.", shift)


def build_stat_commits(gh, shift=None):
    words = gh["commit_words"]
    vmax = max(words.values())
    css, out = [], [module_box(0, 0, SW, SH, "COMMIT MESSAGES", "FIRST WORD")]
    css.append("@keyframes rbar{from{transform:scaleX(0)}to{transform:scaleX(1)}}")
    ry = 48
    for i, (word, v) in enumerate(words.items()):
        bw = 6 + 104 * v / vmax
        out.append(f'<text x="14" y="{ry + 4}" font-size="10" fill="{SLATE}">{word}</text>')
        out.append(
            f'<rect x="76" y="{ry - 5}" width="{f(bw)}" height="9" rx="2" fill="{AMBER}" opacity="0.85" '
            f'style="animation:rbar .6s cubic-bezier(.3,.6,.3,1) both;animation-delay:{f(0.09 * i)}s;'
            f'transform-origin:76px 0"/>'
        )
        out.append(f'<text x="{f(80 + bw + 4)}" y="{ry + 4}" font-size="9" fill="{AMBER}" opacity="0.9">{v}</text>')
        ry += 21
    out.append(f'<text x="12" y="{SH - 12}" font-size="10" fill="{SLATE2}">{gh["commit_mention_fix_pct"]}% of all {gh["commit_words_total"]:,} mention a fix</text>')
    top = ", ".join(f"{w} {v}" for w, v in words.items())
    label = (f"How my commit messages start: {top}. "
             f"{gh['commit_mention_fix_pct']} percent of all {gh['commit_words_total']:,} mention a fix.")
    return shell(SW, SH, css, "".join(out), label, shift)


def build_stat_numbers(gh, shift=None):
    s = gh["streaks"]
    avg = gh["total_contributions_past_year"] / s["active_days"]
    css, out = [], [module_box(0, 0, SW, SH, "BY THE NUMBERS", "MISC")]
    css.append("@keyframes numin{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}")
    rows = [
        (f"{gh['lines_active_projects']:,}", "lines of code in active projects"),
        (f(round(avg, 1)), "contributions per active day"),
        (str(gh["busiest_day"]), "contributions on the busiest day"),
    ]
    ry = 62
    for i, (num, lbl) in enumerate(rows):
        out.append(
            f'<g style="animation:numin .5s cubic-bezier(.3,.6,.3,1) both;animation-delay:{f(0.15 * i)}s">'
            f'<text x="16" y="{ry}" font-size="17" fill="{AMBER}">{num}</text>'
            f'<text x="16" y="{ry + 15}" font-size="9.5" fill="{SLATE2}">{lbl}</text></g>'
        )
        ry += 40
    label = (f"By the numbers: {gh['lines_active_projects']:,} lines of code in active projects, "
             f"{f(round(avg, 1))} contributions per active day, {gh['busiest_day']} on the busiest day.")
    return shell(SW, SH, css, "".join(out), label, shift)


def build_story(shift=None):
    W, H = 830, 64
    stops = ["blender games", "minecraft plugins", "unity + c#", "uottawa", "gadget", "reciped"]
    css, out = [], [frame(W, H, rx=8)]
    n = len(stops)
    xs = [40 + i * (W - 80) / (n - 1) for i in range(n)]
    out.append(f'<line x1="{f(xs[0])}" y1="28" x2="{f(xs[-1])}" y2="28" stroke="{LINE}"/>')
    css.append("@keyframes stline{0%{transform:scaleX(0)}82%,100%{transform:scaleX(1)}}")
    out.append(
        f'<line x1="{f(xs[0])}" y1="28" x2="{f(xs[-1])}" y2="28" stroke="{AMBER}" stroke-opacity="0.5" '
        f'style="animation:stline 9s linear infinite;transform-origin:{f(xs[0])}px 0"/>'
    )
    css.append("@keyframes stpulse{0%,100%{opacity:.35}50%{opacity:1}}")
    for i, (sx, lbl) in enumerate(zip(xs, stops)):
        out.append(
            f'<circle cx="{f(sx)}" cy="28" r="3.2" fill="{AMBER}" '
            f'style="animation:stpulse 9s ease-in-out infinite;animation-delay:{f(i * 1.5)}s;opacity:.35"/>'
        )
        anchor = "start" if i == 0 else "end" if i == n - 1 else "middle"
        ax = sx if anchor != "start" else sx - 16
        ax = ax if anchor != "end" else sx + 16
        out.append(f'<text x="{f(ax)}" y="50" font-size="10.5" fill="{SLATE}" text-anchor="{anchor}">{lbl}</text>')
    return shell(W, H, css, "".join(out), "Timeline: blender games, minecraft plugins, unity and c sharp, uOttawa, gadget, reciped", shift)


# ------------------------------------------------------------- main

def main():
    args = sys.argv[1:]
    shift = None
    if "--shift" in args:
        i = args.index("--shift")
        shift = float(args[i + 1])

    gh = json.load(open(os.path.join(ROOT, "tools", "github-data.json")))
    outputs = {
        "hero-header": build_hero_header(shift),
        "hero-footer": build_hero_footer(gh, shift),
        "stats": build_stats(gh, shift),
        "stat-clock": build_stat_clock(gh, shift),
        "stat-streaks": build_stat_streaks(gh, shift),
        "stat-weekdays": build_stat_weekdays(gh, shift),
        "stat-langs": build_stat_langs(gh, shift),
        "stat-commits": build_stat_commits(gh, shift),
        "stat-numbers": build_stat_numbers(gh, shift),
        "story": build_story(shift),
    }
    outputs.update(build_hero_modules(shift))
    for fn in (banner_reciped, banner_uschedule, banner_factory, banner_polybot,
               banner_navsim, banner_netcode, banner_earlier):
        name, svg = fn(shift)
        outputs[name] = svg

    for name, svg in outputs.items():
        path = os.path.join(ROOT, "assets", f"{name}.svg")
        with open(path, "w") as fh:
            fh.write(svg)
        print(f"wrote assets/{name}.svg ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
