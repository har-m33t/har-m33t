#!/usr/bin/env python3
"""Generate the self-hosted SVG widgets used by the profile README.

Everything here is SMIL-animated, never CSS-animated: GitHub proxies README
images through camo, and camo-served SVGs do not run CSS animations (a card
whose text starts at opacity:0 renders blank). SMIL <animate> does run.
"""
import html
import json
import os
import sys
import urllib.request

AMBER, ORANGE, CREAM = "#ffb000", "#ff6b35", "#f5ede1"
BG, MUTED, LINE = "#0a0908", "#8a8073", "#1f1b16"
RAMP = ["#3a2814", "#5e3c14", "#8f5a10", "#c97f0a", AMBER]
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
CW = 0.601  # monospace advance width, in em


def esc(s):
    return html.escape(str(s), quote=True)


def text_w(s, size):
    return len(s) * size * CW


# ---------------------------------------------------------------- stack.svg
#
# (label, simple-icons slug or None, is_highlight)
# Only languages, frameworks, libraries, cloud and AI/ML *technologies* -
# no individual model architectures.

ICONS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons.json")))

ROWS = [
    ("LANGUAGES & FRAMEWORKS", [
        ("Python", "python", True), ("C++", "cplusplus", True), ("C", "c", False),
        ("Java", "openjdk", False), ("TypeScript", "typescript", True),
        ("JavaScript", "javascript", False), ("SQL", "postgresql", False),
        ("R", "r", False), ("Bash", "gnubash", False), ("ROS2", "ros", True),
        ("React", "react", False), ("Node.js", "nodedotjs", False), ("Flask", "flask", False),
    ]),
    ("AI / ML", [
        ("PyTorch", "pytorch", True), ("TensorFlow", "tensorflow", False),
        ("scikit-learn", "scikitlearn", False), ("OpenCV", "opencv", True),
        ("ONNX", "onnx", True), ("TensorRT", "nvidia", True), ("CUDA", "nvidia", True),
        ("Transformers", "huggingface", True), ("Keras", "keras", False),
        ("NumPy", "numpy", False), ("Pandas", "pandas", False), ("Plotly", "plotly", False),
    ]),
    ("CLOUD & DEPLOYMENT", [
        ("AWS", "amazonwebservices", True), ("SageMaker", "amazonwebservices", True),
        ("Bedrock", "amazonwebservices", True), ("Lambda", "awslambda", False),
        ("S3", "amazons3", False), ("DynamoDB", "amazondynamodb", False),
        ("API Gateway", "amazonapigateway", False), ("Azure", None, False),
        ("Docker", "docker", True), ("Kubernetes", "kubernetes", False),
        ("CI/CD", "githubactions", False), ("Jetson", "nvidia", True),
        ("Linux", "linux", False), ("Git", "git", False),
    ]),
]

ICON_PX = 15
CHIP_H = 34


def chip(label, slug, hot, x, size=13):
    """One tech chip, with an inlined brand mark when one exists."""
    pad, gapi = 13, 8
    ic = ICONS.get(slug) if slug else None
    iw = (ICON_PX + gapi) if ic else 0
    w = iw + text_w(label, size) + pad * 2
    stroke = AMBER if hot else "#2a231c"
    fill = CREAM if hot else MUTED
    mark = AMBER if hot else "#6f6656"
    parts = [f'<rect x="0" y="0" width="{w:.1f}" height="{CHIP_H}" rx="2" '
             f'fill="#120f0d" stroke="{stroke}" stroke-width="1"/>']
    if ic:
        # reference a single shared <path> in <defs>; inlining each logo per
        # chip repetition ballooned the file past 350 KB
        sc = ICON_PX / 24.0
        ty = (CHIP_H - ICON_PX) / 2
        parts.append(f'<g transform="translate({pad},{ty:.1f}) scale({sc:.4f})">'
                     f'<use href="#i-{slug}" fill="{mark}"/></g>')
    tx = pad + iw
    parts.append(f'<text x="{tx:.1f}" y="{CHIP_H/2 + 4.5:.1f}" font-family="{MONO}" '
                 f'font-size="{size}" fill="{fill}">{esc(label)}</text>')
    return f'<g transform="translate({x:.1f},0)">' + "".join(parts) + "</g>", w


def marquee(items, y, rtl, view_w, speed, rid):
    """A seamlessly looping row.

    The y offset is baked into the animation values rather than applied as a
    base transform with additive="sum", which composites unreliably when the
    SVG is rendered inside an <img> - exactly how GitHub serves README images.
    """
    gap = 11
    seq, x = [], 0.0
    while x < view_w * 1.6:            # repeat until one copy overflows the view
        for label, slug, hot in items:
            g, w = chip(label, slug, hot, x)
            seq.append(g)
            x += w + gap
    period = x                          # width of exactly one copy
    body = "".join(seq)
    inner = f'<g>{body}</g><g transform="translate({period:.1f},0)">{body}</g>'
    if rtl:
        frm, to = f"0 {y}", f"-{period:.1f} {y}"
    else:
        frm, to = f"-{period:.1f} {y}", f"0 {y}"
    dur = period / speed
    return (
        f'<g clip-path="url(#clip{rid})">'
        f'<g transform="translate({frm.split()[0]},{y})">{inner}'
        f'<animateTransform attributeName="transform" type="translate" '
        f'from="{frm}" to="{to}" dur="{dur:.1f}s" repeatCount="indefinite"/>'
        f'</g></g>'
    )


def build_stack(path):
    W = 1200
    row_gap, head_h = 62, 20
    top = 20
    H = top + len(ROWS) * row_gap + 14
    used = sorted({slug for _, items in ROWS for _, slug, _ in items if slug and slug in ICONS})
    defs_icons = "".join(f'<path id="i-{g}" d="{ICONS[g]["d"]}"/>' for g in used)
    clips, rows, heads = [], [], []
    for i, (title, items) in enumerate(ROWS):
        y = top + i * row_gap
        heads.append(f'<text x="24" y="{y - 6}" font-family="{MONO}" font-size="10" '
                     f'fill="#5c554a" letter-spacing="1.2">{esc(title)}</text>')
        clips.append(f'<clipPath id="clip{i}"><rect x="0" y="{y - 2}" width="{W}" height="{CHIP_H + 4}"/></clipPath>')
        rows.append(marquee(items, y, rtl=(i == 1), view_w=W, speed=42 + i * 6, rid=i))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Technology stack: languages and frameworks, AI/ML, cloud and deployment">
<defs>
{defs_icons}
{"".join(clips)}
<linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="{BG}" stop-opacity="1"/><stop offset="0.05" stop-color="{BG}" stop-opacity="0"/>
<stop offset="0.95" stop-color="{BG}" stop-opacity="0"/><stop offset="1" stop-color="{BG}" stop-opacity="1"/>
</linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="{BG}"/>
{"".join(heads)}
{"".join(rows)}
<rect width="{W}" height="{H}" fill="url(#edge)" pointer-events="none"/>
</svg>'''
    open(path, "w").write(svg)
    return path


# ----------------------------------------------------------- experience.svg

ROLES = [
    ("AbbVie", "Clinical Innovation R&D", "Data Scientist Intern, CV + ML",
     "Jun 2026 - Present", "HRNetV2+OCR segmentation on SageMaker, 82% pixel acc, 9x faster inference", True),
    ("Legacy Robotics", "URC Team @ UCI", "SWE, Autonomous Navigation",
     "Apr 2026 - Present", "YOLOv11 to TensorRT, sub-30ms on Jetson; ROS2 stack to sub-5cm localization", True),
    ("Univ. of Arizona", "College of Medicine", "AI + Bioinformatics Research Intern",
     "Jun 2026 - Aug 2026", "Two-stage multimodal LLM pipeline, 150M+ param encoders over 1.1M+ RNA samples", False),
]


def build_experience(path):
    W = 1200
    row_h = 86
    H = 24 + row_h * len(ROLES) + 10
    out = []
    for i, (org, unit, title, when, detail, current) in enumerate(ROLES):
        y = 24 + i * row_h
        dot = AMBER if current else "#5e3c14"
        out.append(f'<circle cx="30" cy="{y+14}" r="5" fill="{dot}"/>')
        if i < len(ROLES) - 1:
            out.append(f'<line x1="30" y1="{y+24}" x2="30" y2="{y+row_h-4}" stroke="{LINE}" stroke-width="1"/>')
        out.append(
            f'<text x="52" y="{y+19}" font-family="{MONO}" font-size="16" font-weight="700" fill="{CREAM}">{esc(org)}'
            f'<tspan fill="{MUTED}" font-weight="400" font-size="13">  {esc(unit)}</tspan></text>')
        out.append(f'<text x="{W-30}" y="{y+19}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{AMBER if current else MUTED}">{esc(when)}</text>')
        out.append(f'<text x="52" y="{y+40}" font-family="{MONO}" font-size="13" fill="{AMBER}" fill-opacity="0.8">{esc(title)}</text>')
        out.append(f'<text x="52" y="{y+60}" font-family="{MONO}" font-size="12" fill="{MUTED}">{esc(detail)}</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Experience timeline">
<rect width="{W}" height="{H}" fill="{BG}"/>
{"".join(out)}
</svg>'''
    open(path, "w").write(svg)
    return path

# ---------------------------------------------------------------- stats.svg

GQL = """query($login:String!){ user(login:$login){
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ contributionCount date } } } }
  repositories(first:100,ownerAffiliations:OWNER,isFork:false){ nodes{ languages(first:10){ edges{ size node{ name } } } } }
  pullRequests{ totalCount } } }"""


def gh_graphql(token, login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": GQL, "variables": {"login": login}}).encode(),
        headers={"Authorization": "bearer " + token, "Content-Type": "application/json",
                 "User-Agent": "profile-asset-builder"})
    return json.load(urllib.request.urlopen(req, timeout=45))["data"]["user"]


def collect(login, token):
    """Live figures, with a static fallback so a token-less run still renders."""
    if not token:
        return None
    try:
        u = gh_graphql(token, login)
    except Exception as e:
        print("graphql failed:", e, file=sys.stderr)
        return None
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    langs = {}
    for n in u["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    # longest streak over the calendar
    best = cur = 0
    for d in days:
        cur = cur + 1 if d["contributionCount"] > 0 else 0
        best = max(best, cur)
    return {"total": cal["totalContributions"], "days": days,
            "langs": sorted(langs.items(), key=lambda kv: -kv[1]),
            "prs": u["pullRequests"]["totalCount"], "streak": best}


def build_stats(path, data):
    W, H = 1200, 300
    cell, gap = 15, 3
    weeks = [data["days"][i:i + 7] for i in range(0, len(data["days"]), 7)][-53:]
    peak = max((d["contributionCount"] for d in data["days"]), default=1) or 1
    grid = []
    for wi, wk in enumerate(weeks):
        for di, d in enumerate(wk):
            c = d["contributionCount"]
            lvl = 0 if c == 0 else min(4, 1 + int(3 * c / peak))
            col = "#161310" if c == 0 else RAMP[lvl]
            x = 30 + wi * (cell + gap)
            y = 78 + di * (cell + gap)
            grid.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{col}"/>')
    gx = 30 + len(weeks) * (cell + gap) + 26
    total = f'{data["total"]:,}'
    figs = [("contributions", total, AMBER), ("longest streak", f'{data["streak"]}d', CREAM),
            ("pull requests", str(data["prs"]), CREAM)]
    side = []
    for i, (lab, val, col) in enumerate(figs):
        y = 86 + i * 58
        side.append(f'<text x="{gx}" y="{y+22}" font-family="{MONO}" font-size="26" font-weight="700" fill="{col}">{esc(val)}</text>')
        side.append(f'<text x="{gx}" y="{y+40}" font-family="{MONO}" font-size="11" fill="{MUTED}">{esc(lab)}</text>')
    tot = sum(v for _, v in data["langs"]) or 1
    bar, bx = [], 30
    legend = []
    for i, (name, size) in enumerate(data["langs"][:5]):
        w = (size / tot) * (W - 60)
        col = RAMP[max(0, 4 - i)]
        bar.append(f'<rect x="{bx:.1f}" y="252" width="{w:.1f}" height="9" fill="{col}"/>')
        legend.append((name, 100 * size / tot, col))
        bx += w
    leg, lx = [], 30
    for name, pct, col in legend:
        leg.append(f'<rect x="{lx}" y="276" width="8" height="8" fill="{col}"/>')
        label = f"{name} {pct:.1f}%"
        leg.append(f'<text x="{lx+13}" y="284" font-family="{MONO}" font-size="11" fill="{MUTED}">{esc(label)}</text>')
        lx += 13 + text_w(label, 11) + 22
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub contribution activity">
<rect width="{W}" height="{H}" fill="{BG}"/>
<text x="{W-30}" y="34" text-anchor="end" font-family="{MONO}" font-size="11" fill="#5c554a">last 12 months</text>
{"".join(grid)}{"".join(side)}
<line x1="30" y1="232" x2="{W-30}" y2="232" stroke="{LINE}" stroke-width="1"/>
{"".join(bar)}{"".join(leg)}
</svg>'''
    open(path, "w").write(svg)
    return path


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "assets"
    os.makedirs(out_dir, exist_ok=True)
    print("wrote", build_stack(os.path.join(out_dir, "stack.svg")))
    print("wrote", build_experience(os.path.join(out_dir, "experience.svg")))
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    data = collect(os.environ.get("GH_LOGIN", "har-m33t"), tok)
    if data:
        print("wrote", build_stats(os.path.join(out_dir, "stats.svg"), data))
    else:
        print("skipped stats.svg (no token / API unavailable)", file=sys.stderr)
