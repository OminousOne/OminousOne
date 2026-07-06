#!/usr/bin/env python3
"""
simulate.py — bakes a multiplayer pong match into assets/hero.svg

There is no JavaScript and no GIF in the hero image. This script simulates a
24-second rally (ball physics, paddle AI, one dropped snapshot, one rollback),
then writes every event out as CSS keyframes inside a single SVG. GitHub strips
scripts from READMEs but keeps the stylesheet inside an <img>-embedded SVG, so
the whole thing plays back as pure, deterministic CSS animation.

Usage:  python3 tools/simulate.py [output.svg]
"""

import sys

# ---------------------------------------------------------------- constants

LOOP = 24.0          # seconds, one full replay
W, H = 900, 540      # viewBox

AMBER   = "#FFB300"  # phosphor amber — client panels, chrome accents
WHITE   = "#EDE6D6"  # warm CRT white — reserved for the authoritative server
RED     = "#FF4438"  # desync red — used exactly once, at the rollback
SLATE   = "#6C7986"  # instrument chrome text
SLATE2  = "#46525E"  # dimmer chrome
LINE    = "#1E262E"  # hairlines
PANEL   = "#0A0D10"  # panel fill
COURT   = "#05070A"  # court fill (the actual phosphor screen)
BG      = "#0E1116"  # device body

MONO = "ui-monospace,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

# court geometry (local coords inside each panel's court, 244 x 130)
CW, CH = 244, 130
YLO, YHI = 3.0, 127.0          # ball-centre travel range (ball is 6x6)
XL, XR = 15.0, 229.0           # ball-centre x at left/right paddle contact
PAD_MIN, PAD_MAX = 13.0, 117.0 # paddle-centre travel range (paddle is 26 tall)

PANEL_XS = [24, 320, 616]      # three panels
PANEL_Y, PANEL_W, PANEL_H = 146, 260, 192
COURT_OX, COURT_OY = 8, 26     # court offset inside panel

INTERP_DELAY = 0.12            # remote entities render 120ms in the past

# the rally: 12 legs (6 round trips). durations sum to exactly LOOP, and the
# last hit returns the ball to its starting state, so the loop is seamless.
DURS  = [1.9, 2.1, 1.8, 2.2, 2.0, 1.9, 2.15, 1.85, 2.0, 2.1, 1.95, 2.05]
HITS  = [65, 26, 104, 48, 121, 17, 78, 121, 35, 95, 22, 82, 65]
WANT  = [1, 2, 1, 1, 2, 1, 1, 0, 1, 1, 2, 1]   # wall bounces per leg

# the story: a snapshot from server to client A is lost at ~13.3s. A keeps
# extrapolating from stale data, mispredicts the deflection off B's paddle at
# 14.05s, drifts, and gets rolled back to the server's truth at 15.1s.
T_DROP    = 13.30
T_DESYNC  = 14.05   # start of leg 7 (the direct R->L leg)
T_SNAP    = 15.10   # rollback lands
VY_WRONG  = -95.0   # client A's mispredicted deflection


# ---------------------------------------------------------------- helpers

def f(v):
    """compact float"""
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


def pct(t):
    return f(t / LOOP * 100.0)


def kf_transform(name, frames):
    """frames: list of (t, xy-or-y, easing|None). values may be (x,y) or y."""
    out = [f"@keyframes {name}{{"]
    for t, val, ease in frames:
        if isinstance(val, tuple):
            tr = f"translate({f(val[0])}px,{f(val[1])}px)"
        else:
            tr = f"translateY({f(val)}px)"
        e = f"animation-timing-function:{ease};" if ease else ""
        out.append(f"{pct(t)}%{{transform:{tr};{e}}}")
    out.append("}")
    return "".join(out)


def kf_opacity(name, windows, base=0.0):
    """windows: list of (t_on, t_off, opacity). discrete flips with 0.01% ramps."""
    first_op = windows[0][2] if windows and windows[0][0] <= 0 else base
    stops = [(0.0, first_op)]
    for t_on, t_off, op in windows:
        if t_on > 0:
            stops.append((t_on - 0.004, base))
            stops.append((t_on, op))
        stops.append((t_off - 0.004, op))
        if t_off < LOOP:
            stops.append((t_off, base))
    stops.append((LOOP, stops[-1][1]))
    body = "".join(f"{pct(t)}%{{opacity:{f(op)}}}" for t, op in stops)
    return f"@keyframes {name}{{{body}}}"


# ---------------------------------------------------------------- ball sim

def reflect_leg(t0, T, x0, x1, y0, vy):
    """walk one leg with wall reflections; return (bounce_kfs, y_end).
    bounce_kfs are (t_abs, x, y) at each wall contact."""
    pts, t, y, v = [], 0.0, y0, vy
    while True:
        if v > 0:
            dt = (YHI - y) / v
        elif v < 0:
            dt = (y - YLO) / -v
        else:
            break
        if t + dt >= T - 1e-9:
            break
        t += dt
        y = YHI if v > 0 else YLO
        v = -v
        pts.append((t0 + t, x0 + (x1 - x0) * (t / T), y))
    y_end = y + v * (T - t)
    return pts, y_end, v


def solve_leg(y0, y1, T, want):
    """find vy so the ball leaves y0 and arrives at y1 after T seconds,
    preferring `want` wall bounces. brute-force over unfolded images."""
    best = None
    S = YHI - YLO
    for n in range(0, 4):
        for image in (2 * n * S + (y1 - YLO), 2 * n * S - (y1 - YLO)):
            for sign in (1, -1):
                L = sign * image - (y0 - YLO) if sign > 0 else (y0 - YLO) + image
                if L <= 0:
                    continue
                vy = sign * L / T
                if abs(vy) > 105 or abs(vy) < 6:
                    continue
                pts, y_end, _ = reflect_leg(0, T, 0, 1, y0, vy)
                if abs(y_end - y1) > 0.5:
                    continue
                score = (abs(len(pts) - want), abs(vy))
                if best is None or score < best[0]:
                    best = (score, vy)
    if best is None:
        raise SystemExit(f"no trajectory for leg {y0}->{y1} in {T}s")
    return best[1]


def simulate_rally():
    """returns (true_kfs, hit_times). true_kfs: [(t, x, y)] incl. leg ends."""
    kfs = [(0.0, XL, float(HITS[0]))]
    t = 0.0
    for i, T in enumerate(DURS):
        x0, x1 = (XL, XR) if i % 2 == 0 else (XR, XL)
        y0, y1 = float(HITS[i]), float(HITS[i + 1])
        vy = solve_leg(y0, y1, T, WANT[i])
        bounces, y_end, _ = reflect_leg(t, T, x0, x1, y0, vy)
        kfs.extend(bounces)
        t += T
        kfs.append((t, x1, y1))
    return kfs


def wrong_prediction():
    """client A's mispredicted path from the desync hit until the rollback."""
    span = T_SNAP - T_DESYNC
    # leg 7 runs right->left; same vx as truth, wrong vy
    x_at = lambda t: XR + (XL - XR) * ((t - T_DESYNC) / DURS[7])
    pts, y_end, _ = reflect_leg(T_DESYNC, span, XR, x_at(T_SNAP), float(HITS[7]), VY_WRONG)
    return pts, (T_SNAP, x_at(T_SNAP), y_end)


def true_pos_at(kfs, t):
    for (t0, x0, y0), (t1, x1, y1) in zip(kfs, kfs[1:]):
        if t0 <= t <= t1:
            u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return (x0 + (x1 - x0) * u, y0 + (y1 - y0) * u)
    return kfs[-1][1], kfs[-1][2]


# ---------------------------------------------------------------- paddles

def paddle_frames(hit_list, opp_times):
    """hit_list: [(t, y)] for this paddle (t=0 and t=LOOP included for left).
    opp_times: times the opponent hits (ball turns back toward us).
    returns keyframes [(t, y, ease)] covering 0..LOOP seamlessly."""
    frames = []
    n = len(hit_list) - (1 if hit_list[-1][0] >= LOOP - 1e-9 else 0)
    seq = hit_list[:n]
    for i in range(len(seq)):
        ta, ya = seq[i]
        tb, yb = seq[(i + 1) % len(seq)]
        if tb <= ta:
            tb += LOOP
        tm = next((t for t in opp_times + [t + LOOP for t in opp_times] if ta < t < tb), (ta + tb) / 2)
        drift = ya + (65 - ya) * 0.55
        frames.append((ta, ya, "cubic-bezier(.35,0,.45,1)"))
        frames.append((ta + (tm - ta) * 0.5, drift, None))
        frames.append((tm, drift, "cubic-bezier(.2,.65,.25,1)"))
        frames.append((tm + (tb - tm) * 0.72, yb, None))
        frames.append((tb, yb, "cubic-bezier(.35,0,.45,1)"))
    # wrap anything past LOOP back to the front
    wrapped = []
    for t, y, e in frames:
        wrapped.append(((t - LOOP) if t >= LOOP - 1e-9 else t, y, e))
    wrapped.sort(key=lambda k: k[0])
    # dedupe & pin endpoints
    out, seen = [], set()
    for t, y, e in wrapped:
        key = round(t, 4)
        if key in seen:
            continue
        seen.add(key)
        out.append((t, y, e))
    if abs(out[0][0]) > 1e-6:
        out.insert(0, (0.0, out[0][1], None))
    if abs(out[-1][0] - LOOP) > 1e-6:
        out.append((LOOP, out[0][1], None))
    return out


# ---------------------------------------------------------------- pixel font

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
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    " ": ["00000"] * 7,
}


def pixel_text(text, x, y, u, fill, cls_prefix=None, opacity=None):
    """render text as pixel rects. returns svg string. cell = 6u wide."""
    out = []
    for ci, ch in enumerate(text):
        glyph = FONT[ch]
        cls = f' class="{cls_prefix}{ci}"' if cls_prefix else ""
        op = f' opacity="{opacity}"' if opacity is not None else ""
        rects = []
        for r, row in enumerate(glyph):
            for c, bit in enumerate(row):
                if bit == "1":
                    rects.append(f'<rect x="{f(x + ci*6*u + c*u)}" y="{f(y + r*u)}" width="{f(u*0.86)}" height="{f(u*0.86)}"/>')
        if rects:
            out.append(f'<g fill="{fill}"{cls}{op}>' + "".join(rects) + "</g>")
    return "".join(out)


def pixel_width(text, u):
    return len(text) * 6 * u - u


# ---------------------------------------------------------------- sparkline

def sparkline_path(seed, spike_at=None):
    """periodic jagged path, period 160, drawn twice. baseline y=0, amp ±7."""
    vals = []
    s = seed
    for i in range(20):
        s = (s * 1103515245 + 12345) % (2**31)
        vals.append(((s >> 16) % 1000) / 1000.0 * 12 - 6)
    pts = []
    for copy in range(2):
        for i in range(20):
            x = copy * 160 + i * 8
            y = vals[i]
            if spike_at is not None and abs((x % 160) - spike_at) < 5:
                y = -14
            elif spike_at is not None and abs((x % 160) - spike_at) < 13:
                y = -8
            pts.append(f"{f(x)},{f(y)}")
    # close the period: last point of each copy meets the first of the next
    pts.append(f"{f(320)},{f(vals[0])}")
    return "M" + " L".join(pts)


# ---------------------------------------------------------------- build

def digit_strip(x, y, values, step_h, dur, steps, name, fill, size=15):
    """vertical strip of glyphs advanced by steps(); clipped to one cell."""
    clip_id = f"clip_{name}"
    texts = "".join(
        f'<text x="{f(x)}" y="{f(y + i*step_h)}" font-size="{size}" fill="{fill}">{v}</text>'
        for i, v in enumerate(values + [values[0]])
    )
    svg = (
        f'<clipPath id="{clip_id}"><rect x="{f(x-1)}" y="{f(y-size+2)}" width="{size*0.75+2}" height="{size+4}"/></clipPath>'
        f'<g clip-path="url(#{clip_id})"><g class="{name}">{texts}</g></g>'
    )
    css = (
        f"@keyframes {name}{{from{{transform:translateY(0)}}to{{transform:translateY(-{f(len(values)*step_h)}px)}}}}"
        f".{name}{{animation:{name} {f(dur)}s steps({steps}) infinite;}}"
    )
    return svg, css


def dev_shift_css(shift):
    """dev-only: jump the whole animation clock forward by `shift` seconds so a
    headless browser can screenshot any moment of the loop."""
    rules = [f"*{{animation-delay:-{f(shift)}s !important}}"]
    rules.append(f".lag{{animation-delay:-{f(LOOP - INTERP_DELAY + shift)}s !important}}")
    rules.append(f".hop2{{animation-delay:-{f(0.8 + shift)}s !important}}")
    for i in range(14):
        d = 0.05 * i + (i * 7 % 5) * 0.012
        rules.append(f".wm{i}{{animation-delay:{f(d - shift)}s !important}}")
    return "<style>" + "".join(rules) + "</style>"


def build(shift=None):
    css = []
    body = []

    true_kfs = simulate_rally()
    wrong_pts, wrong_end = wrong_prediction()

    # ---- ball keyframes (true + client A's mispredicted variant)
    css.append(kf_transform("kbT", [(t, (x, y), None) for t, x, y in true_kfs]))

    a_kfs = [k for k in true_kfs if k[0] <= T_DESYNC + 1e-9 or k[0] >= T_SNAP + 0.02 - 1e-9]
    snap_from = wrong_end
    snap_to = true_pos_at(true_kfs, T_SNAP + 0.02)
    a_all = (
        [k for k in true_kfs if k[0] <= T_DESYNC + 1e-9]
        + wrong_pts
        + [ (wrong_end[0], wrong_end[1], wrong_end[2]) ]
        + [ (T_SNAP + 0.02, snap_to[0], snap_to[1]) ]
        + [k for k in true_kfs if k[0] > T_SNAP + 0.02]
    )
    css.append(kf_transform("kbA", [(t, (x, y), None) for t, x, y in a_all]))

    # ---- paddles
    left_hits = [(sum(DURS[:i]), min(max(HITS[i], PAD_MIN), PAD_MAX)) for i in range(0, 13, 2)]
    right_hits = [(sum(DURS[:i]), min(max(HITS[i], PAD_MIN), PAD_MAX)) for i in range(1, 12, 2)]
    lt = [t for t, _ in left_hits]
    rt = [t for t, _ in right_hits]
    css.append(kf_transform("padL", paddle_frames(left_hits, rt)))
    css.append(kf_transform("padR", paddle_frames(right_hits, lt)))

    css.append(f".ballT{{animation:kbT {f(LOOP)}s linear infinite;}}")
    css.append(f".ballA{{animation:kbA {f(LOOP)}s linear infinite;}}")
    css.append(f".padL{{animation:padL {f(LOOP)}s linear infinite;}}")
    css.append(f".padR{{animation:padR {f(LOOP)}s linear infinite;}}")
    css.append(f".lag{{animation-delay:-{f(LOOP - INTERP_DELAY)}s;}}")

    # ---- rollback dressing (panel A only)
    css.append(kf_opacity("ghostSrv", [(14.55, T_SNAP + 0.12, 0.5)]))
    css.append(kf_opacity("afterimg", [(T_SNAP, T_SNAP + 0.5, 0.85)]))
    css.append(kf_opacity("rbFlash", [(T_SNAP - 0.02, T_SNAP + 0.62, 0.9)]))
    css.append(kf_opacity("rbText", [(T_SNAP, T_SNAP + 0.22, 1.0), (T_SNAP + 0.34, T_SNAP + 1.3, 1.0)]))
    for n in ("ghostSrv", "afterimg", "rbFlash", "rbText"):
        css.append(f".{n}{{animation:{n} {f(LOOP)}s linear infinite;opacity:0;}}")

    # ---- courts / panels
    def court(px, ball_cls, ball_fill, pad_fill, remote, label, tag, sub, label_fill, extras=""):
        cx, cy = px + COURT_OX, PANEL_Y + COURT_OY
        left_remote = remote == "L"
        right_remote = remote == "R"

        # inline base transforms = the t=0 pose, shown when reduced-motion pauses the loop
        pose = 'style="transform:translateY(65px)"'

        def paddle(x, anim, is_remote):
            if is_remote:
                return (f'<rect x="{x}" y="-13" width="4" height="26" rx="1" fill="none" '
                        f'stroke="{pad_fill}" stroke-width="1.2" stroke-dasharray="3 2" '
                        f'opacity="0.55" class="{anim} lag" {pose}/>')
            return f'<rect x="{x}" y="-13" width="4" height="26" rx="1" fill="{pad_fill}" class="{anim}" {pose}/>'

        score = (
            pixel_text("04", cx + 122 - 34, cy + 8, 2, pad_fill, opacity="0.4")
            + pixel_text("02", cx + 122 + 12, cy + 8, 2, pad_fill, opacity="0.4")
        )
        return f"""
<g>
  <rect x="{px}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" rx="8" fill="{PANEL}" stroke="#232B33"/>
  <text x="{px + 10}" y="{PANEL_Y + 17}" font-size="11" letter-spacing="1.5" fill="{label_fill}">{label}</text>
  <text x="{px + 250}" y="{PANEL_Y + 17}" font-size="9" letter-spacing="0.8" fill="{SLATE2}" text-anchor="end">{tag}</text>
  <rect x="{cx}" y="{cy}" width="{CW}" height="{CH}" fill="{COURT}" stroke="{LINE}"/>
  <line x1="{cx + 122}" y1="{cy + 4}" x2="{cx + 122}" y2="{cy + CH - 4}" stroke="{LINE}" stroke-dasharray="3 5"/>
  {score}
  <g transform="translate({cx},{cy})">
    {paddle(8, "padL", left_remote)}
    {paddle(232, "padR", right_remote)}
    <rect x="-3" y="-3" width="6" height="6" fill="{ball_fill}" class="{ball_cls}" filter="url(#glow)" style="transform:translate(15px,65px)"/>
    {extras}
  </g>
  <text x="{px + 10}" y="{PANEL_Y + 184}" font-size="10.5" fill="{SLATE2}">{sub}</text>
</g>"""

    rollback_extras = f"""
    <rect x="-3" y="-3" width="6" height="6" fill="none" stroke="{WHITE}" stroke-width="1.2" class="ballT ghostSrv" style="transform:translate(15px,65px)"/>
    <rect x="{f(wrong_end[1] - 3)}" y="{f(wrong_end[2] - 3)}" width="6" height="6" fill="{RED}" class="afterimg"/>
    <rect x="0.5" y="0.5" width="243" height="129" fill="none" stroke="{RED}" stroke-width="1.4" class="rbFlash"/>
    <text x="122" y="112" font-size="10" letter-spacing="1.2" fill="{RED}" text-anchor="middle" class="rbText">ROLLBACK ▸ REWOUND 6 TICKS</text>"""

    panels = (
        court(PANEL_XS[0], "ballA", AMBER, AMBER, "R", "CLIENT A", "PREDICTED · INTERP +120MS",
              "sees B 120ms in the past", AMBER, rollback_extras)
        + court(PANEL_XS[1], "ballT", WHITE, WHITE, "", "SERVER", "AUTHORITATIVE · 60 Hz",
                "single source of truth", WHITE)
        + court(PANEL_XS[2], "ballT", AMBER, AMBER, "L", "CLIENT B", "PREDICTED · INTERP +120MS",
                "sees A 120ms in the past", AMBER)
    )

    # ---- packet lanes between panels
    css.append(
        "@keyframes hopR{0%{transform:translateX(0);opacity:0}12%{opacity:1}"
        "88%{opacity:1}100%{transform:translateX(36px);opacity:0}}"
    )
    css.append(
        "@keyframes hopL{0%{transform:translateX(0);opacity:0}12%{opacity:1}"
        "88%{opacity:1}100%{transform:translateX(-36px);opacity:0}}"
    )
    css.append(".hopR{animation:hopR 1.6s linear infinite;}")
    css.append(".hopL{animation:hopL 1.6s linear infinite;}")
    css.append(".hop2{animation-delay:-0.8s;}")
    # the dropped snapshot: server -> client A, dies mid-lane
    css.append(kf_transform("dropX", [(T_DROP, (0, 0), None), (T_DROP + 0.45, (-20, 0), None), (LOOP, (-20, 0), None)]))
    css.append(kf_opacity("dropO", [(T_DROP, T_DROP + 0.34, 1.0)]))
    css.append(f".dropP{{animation:dropX {f(LOOP)}s linear infinite,dropO {f(LOOP)}s linear infinite;opacity:0;}}")
    css.append(kf_opacity("dropM", [(T_DROP + 0.38, T_DESYNC + 0.7, 0.9)]))
    css.append(f".dropM{{animation:dropM {f(LOOP)}s linear infinite;opacity:0;}}")

    def lane(x0, y, cls):
        dots = (
            f'<circle cx="{x0 if "R" in cls else x0 + 36}" cy="{y}" r="2" fill="{AMBER}" opacity="0" class="{cls}"/>'
            f'<circle cx="{x0 if "R" in cls else x0 + 36}" cy="{y}" r="2" fill="{AMBER}" opacity="0" class="{cls} hop2"/>'
        )
        return (
            f'<line x1="{x0}" y1="{y}" x2="{x0 + 36}" y2="{y}" stroke="#2A333C" stroke-dasharray="1.5 4"/>' + dots
        )

    g1, g2 = 284, 580
    lanes = (
        lane(g1, 205, "hopR") + lane(g1, 255, "hopL")
        + lane(g2, 205, "hopL") + lane(g2, 255, "hopR")
        + f'<circle cx="{g1 + 36}" cy="255" r="2" fill="{AMBER}" class="dropP"/>'
        + f'<text x="{g1 + 12}" y="259" font-size="9" fill="{AMBER}" class="dropM">×</text>'
    )

    # ---- wordmark with per-column boot flicker
    name_txt = "JULIEN DEWOLFE"
    u = 6
    wm_x = (W - pixel_width(name_txt, u)) / 2
    wordmark = f'<g filter="url(#glow)">{pixel_text(name_txt, wm_x, 58, u, AMBER, cls_prefix="wm")}</g>'
    css.append(
        "@keyframes boot{0%{opacity:.12}0.7%{opacity:.9}1.2%{opacity:.28}1.9%{opacity:1}100%{opacity:1}}"
    )
    for i in range(len(name_txt)):
        d = 0.05 * i + (i * 7 % 5) * 0.012
        css.append(f".wm{i}{{animation:boot {f(LOOP)}s linear infinite;animation-delay:{f(d)}s;}}")

    # ---- telemetry: rtt sparklines
    css.append(f"@keyframes scroll{{from{{transform:translateX(0)}}to{{transform:translateX(-160px)}}}}")
    css.append(f".scroll{{animation:scroll {f(LOOP)}s linear infinite;}}")

    def spark(x, y, seed, spike):
        pid = f"sp{seed}"
        path = sparkline_path(seed, spike)
        return (
            f'<clipPath id="{pid}"><rect x="{x}" y="{y - 18}" width="160" height="26"/></clipPath>'
            f'<g clip-path="url(#{pid})"><g transform="translate({x},{y})">'
            f'<path d="{path}" fill="none" stroke="{AMBER}" stroke-width="1.1" opacity="0.75" class="scroll"/>'
            f"</g></g>"
        )

    # spike enters the window right after the packet drop (t≈13.5s)
    tele = []
    tele.append(f'<text x="24" y="384" font-size="12" fill="{AMBER}" opacity="0.8">rtt ▸ 47 ms</text>')
    tele.append(spark(122, 380, 7, 90))
    tele.append(f'<text x="620" y="384" font-size="12" fill="{AMBER}" opacity="0.8">rtt ▸ 63 ms</text>')
    tele.append(spark(716, 380, 12, None))

    # interp buffer squares
    def buffer_row(x, name, drain):
        cells = []
        for i in range(5):
            cls = f"{name}{i}"
            cells.append(f'<rect x="{x + i * 13}" y="402" width="9" height="9" rx="1" fill="{AMBER}" class="{cls}"/>')
            if i <= 2 and drain:
                wins = {2: [(0, 13.5, 0.9), (16.1, LOOP, 0.9)], 1: [(0, 14.1, 0.9), (15.6, LOOP, 0.9)], 0: [(0, LOOP, 0.9)]}
                css.append(kf_opacity(cls, wins[i]) if i in (1, 2) else f"@keyframes {cls}{{0%,100%{{opacity:.9}}}}")
            elif i <= 2:
                css.append(f"@keyframes {cls}{{0%,100%{{opacity:.9}}}}")
            elif i == 3:
                css.append(kf_opacity(cls, [(5.0, 8.0, 0.9), (18.5, 21.0, 0.9)], base=0.15))
            else:
                css.append(f"@keyframes {cls}{{0%,100%{{opacity:.15}}}}")
            css.append(f".{cls}{{animation:{cls} {f(LOOP)}s linear infinite;}}")
        return "".join(cells)

    tele.append(f'<text x="24" y="412" font-size="10.5" fill="{SLATE2}">interp buffer</text>')
    tele.append(buffer_row(122, "bufA", True))
    tele.append(f'<text x="620" y="412" font-size="10.5" fill="{SLATE2}">interp buffer</text>')
    tele.append(buffer_row(716, "bufB", False))

    # replay clock with rolling digit strips
    secs = [str((s // 10)) for s in range(24)], [str(s % 10) for s in range(24)]
    strip1, c1 = digit_strip(432, 384, secs[0], 18, LOOP, 24, "st1", AMBER)
    strip2, c2 = digit_strip(443, 384, secs[1], 18, LOOP, 24, "st2", AMBER)
    strip3, c3 = digit_strip(463, 384, [str(d) for d in range(10)], 18, 1.0, 10, "st3", AMBER)
    css += [c1, c2, c3]
    tele.append(f'<text x="320" y="384" font-size="11" fill="{SLATE2}">replay clock</text>')
    tele.append(f'<text x="404" y="384" font-size="15" fill="{AMBER}">00:</text>')
    tele.append(strip1 + strip2)
    tele.append(f'<text x="455" y="384" font-size="15" fill="{AMBER}">.</text>')
    tele.append(strip3)
    tele.append(f'<text x="320" y="412" font-size="10.5" fill="{SLATE2}">tick 60/s · snap 20/s · rewind 6 ticks</text>')

    # ---- event log
    msgs = [
        (0.0, 3.4, "replay restarted — dewolfe_vs_latency.bin · 24.0s window", SLATE),
        (3.4, 6.9, "input ack Δ 0.4ms · prediction stable", SLATE),
        (6.9, 10.4, "snapshot 0480 applied · drift 0.1u", SLATE),
        (10.4, T_DROP, "interp buffer 3/5 · rtt nominal", SLATE),
        (T_DROP, T_SNAP - 0.02, "WARN snapshot 0791 lost — extrapolating from stale state", AMBER),
        (T_SNAP - 0.02, 17.9, "ROLLBACK client A ▸ rewound 6 ticks · inputs replayed · reality restored", RED),
        (17.9, 21.0, "resync complete · drift 0.0u · buffer refilled", SLATE),
        (21.0, LOOP, "rally continues — nobody has scored since tick 88,241", SLATE),
    ]
    log = [f'<text x="24" y="452" font-size="12" fill="{AMBER}">▸</text>']
    for i, (t0, t1, txt, color) in enumerate(msgs):
        css.append(kf_opacity(f"log{i}", [(t0, t1, 1.0)]))
        base = 1 if i == 0 else 0  # first message survives reduced-motion
        css.append(f".log{i}{{animation:log{i} {f(LOOP)}s linear infinite;opacity:{base};}}")
        log.append(f'<text x="40" y="452" font-size="12" fill="{color}" class="log{i}">{txt}</text>')

    # ---- chrome
    css.append("@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}")
    css.append(".pulse{animation:pulse 2s ease-in-out infinite;}")

    chrome = f"""
<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="14" fill="{BG}" stroke="#262E36" stroke-width="1.5"/>
<circle cx="30" cy="23" r="3.5" fill="{AMBER}" class="pulse"/>
<text x="42" y="27" font-size="12.5" fill="{SLATE}">REPLAY ▸ dewolfe_vs_latency.bin</text>
<text x="872" y="27" font-size="12.5" fill="{SLATE}" text-anchor="end">seed 0x4A44 · 60 tick/s</text>
<line x1="24" y1="38" x2="876" y2="38" stroke="{LINE}"/>
<text x="450" y="124" font-size="13.5" fill="#8B97A3" text-anchor="middle">software engineering @ uOttawa — building multiplayer systems where clients can't lie</text>
<line x1="24" y1="352" x2="876" y2="352" stroke="{LINE}"/>
<line x1="24" y1="478" x2="876" y2="478" stroke="{LINE}"/>
<text x="24" y="507" font-size="11.5" fill="{SLATE2}">github.com/OminousOne · uschedule.ca</text>
<text x="876" y="507" font-size="11.5" fill="{AMBER}" opacity="0.65" text-anchor="end">no gifs · no js · no lies — one hand-baked svg</text>
"""

    # ---- assemble
    defs = f"""
<defs>
  <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
    <feGaussianBlur stdDeviation="2.1" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="scan" width="3" height="3" patternUnits="userSpaceOnUse">
    <rect width="3" height="1" y="2" fill="#000000"/>
  </pattern>
  <radialGradient id="vig" cx="50%" cy="42%" r="75%">
    <stop offset="62%" stop-color="#000000" stop-opacity="0"/>
    <stop offset="100%" stop-color="#000000" stop-opacity="0.30"/>
  </radialGradient>
</defs>"""

    style = (
        "<style><![CDATA[\n"
        f"text{{font-family:{MONO};}}\n"
        + "\n".join(css)
        + "\n@media (prefers-reduced-motion:reduce){*{animation:none !important;}}"
        + "\n]]></style>"
    )

    overlay = (
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="url(#scan)" opacity="0.16" pointer-events="none"/>'
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="url(#vig)" pointer-events="none"/>'
    )

    dev = dev_shift_css(shift) if shift is not None else ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Animated netcode replay viewer: a Pong match shown from two predicted client views and one authoritative server view, with packet traffic, a dropped snapshot and a rollback correction.">
{style}
{dev}
{defs}
{chrome}
{wordmark}
{panels}
{lanes}
{"".join(tele)}
{"".join(log)}
{overlay}
</svg>"""


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    shift = None
    if "--shift" in args:
        i = args.index("--shift")
        shift = float(args[i + 1])
        del args[i:i + 2]
    out = args[0] if args else "assets/hero.svg"
    svg = build(shift)
    with open(out, "w") as fh:
        fh.write(svg)
    print(f"wrote {out} ({len(svg)} bytes)")
