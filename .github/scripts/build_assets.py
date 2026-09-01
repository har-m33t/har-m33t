#!/usr/bin/env python3
"""Generate the self-hosted SVG widgets used by the profile README.

Everything animated here uses SMIL, never CSS. GitHub proxies README images
through camo, and camo-served SVGs do not run CSS animations (a card whose
text starts at opacity:0 renders blank for every visitor). SMIL <animate>
does run - verified on the live profile.

Sections are rendered as SVG rather than markdown so the accent palette holds:
GitHub's own chrome (heading rules, code-block syntax colors, blue links)
cannot be restyled from a README.
"""
import html
import json
import os
import sys
import urllib.request

ACCENT, ACCENT2, TEXT = "#b06cff", "#ff5cc8", "#ece6f5"  # violet / magenta / off-white
BG, MUTED, LINE = "#09080f", "#857d99", "#1c1826"
DIM, PANEL = "#574f6b", "#120f1a"
RAMP = ["#2a1a3d", "#40275c", "#6b3fa0", "#8f57d4", ACCENT]
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
CW = 0.601  # monospace advance width, in em

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = json.load(open(os.path.join(HERE, "icons.json")))


def esc(s):
    return html.escape(str(s), quote=True)


def text_w(s, size):
    return len(s) * size * CW


# ------------------------------------------------------------ typing title

def typing_title(cmd, x=26, base=34, size=17, dur=7.0, tid="ttl"):
    """An animated 'typed' section title. Returns (defs, body, height).

    The animation's FIRST value is the finished state, not an empty one. A
    renderer that registers the <animate> but never advances it freezes on
    values[0] - which overrides the base attribute - so a reveal starting at
    width 0 leaves the title permanently invisible. (That is exactly how the
    old third-party streak card rendered blank for every visitor.) Instead the
    title sits complete, then wipes and retypes on a loop: correct when SMIL
    runs, fully legible when it does not.
    """
    full = "$ " + cmd
    w = text_w(full, size)
    kt = "0;0.45;0.5;0.85;1"
    defs = (f'<clipPath id="{tid}"><rect x="{x}" y="{base - size}" width="{w:.1f}" height="{size * 1.7:.0f}">'
            f'<animate attributeName="width" values="{w:.1f};{w:.1f};0;{w:.1f};{w:.1f}" '
            f'keyTimes="{kt}" dur="{dur}s" repeatCount="indefinite"/></rect></clipPath>')
    cx = f"{x + w:.1f}"
    body = (
        f'<g clip-path="url(#{tid})">'
        f'<text x="{x}" y="{base}" font-family="{MONO}" font-size="{size}" font-weight="700" fill="{ACCENT}">'
        f'<tspan fill="{DIM}">$ </tspan>{esc(cmd)}</text></g>'
        f'<rect x="{cx}" y="{base - size + 3}" width="9" height="{size}" fill="{ACCENT}">'
        f'<animate attributeName="x" values="{cx};{cx};{x};{cx};{cx}" keyTimes="{kt}" '
        f'dur="{dur}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="1;1;0;0;1" dur="1.06s" repeatCount="indefinite"/></rect>'
    )
    return defs, body, base + 14


def svg(w, h, defs, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
            f'<defs>{defs}</defs><rect width="{w}" height="{h}" fill="{BG}"/>{body}</svg>')


def write(path, content):
    open(path, "w").write(content)
    return path


# ------------------------------------------------------------------- chips

ICON_PX = 15
CHIP_H = 34


def chip(label, slug, hot, x, size=13):
    """One tech chip, with an inlined brand mark when one exists."""
    pad, gapi = 13, 8
    ic = ICONS.get(slug) if slug else None
    iw = (ICON_PX + gapi) if ic else 0
    w = iw + text_w(label, size) + pad * 2
    stroke = ACCENT if hot else "#2b2440"
    fill = TEXT if hot else MUTED
    mark = ACCENT if hot else "#6d6489"
    parts = [f'<rect x="0" y="0" width="{w:.1f}" height="{CHIP_H}" rx="2" '
             f'fill="{PANEL}" stroke="{stroke}" stroke-width="1"/>']
    if ic:
        sc = ICON_PX / 24.0
        ty = (CHIP_H - ICON_PX) / 2
        parts.append(f'<g transform="translate({pad},{ty:.1f}) scale({sc:.4f})">'
                     f'<use href="#i-{slug}" fill="{mark}"/></g>')
    parts.append(f'<text x="{pad + iw:.1f}" y="{CHIP_H / 2 + 4.5:.1f}" font-family="{MONO}" '
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
    period = x
    body = "".join(seq)
    inner = f'<g>{body}</g><g transform="translate({period:.1f},0)">{body}</g>'
    frm, to = (f"0 {y}", f"-{period:.1f} {y}") if rtl else (f"-{period:.1f} {y}", f"0 {y}")
    return (
        f'<g clip-path="url(#clip{rid})"><g transform="translate({frm.split()[0]},{y})">{inner}'
        f'<animateTransform attributeName="transform" type="translate" '
        f'from="{frm}" to="{to}" dur="{period / speed:.1f}s" repeatCount="indefinite"/>'
        f'</g></g>'
    )


def icon_defs(rows):
    used = sorted({s for _, items in rows for _, s, _ in items if s and s in ICONS})
    return "".join(f'<path id="i-{g}" d="{ICONS[g]["d"]}"/>' for g in used)


# --------------------------------------------------------------- stack.svg

ROWS = [
    ("LANGUAGES & FRAMEWORKS", [
        ("Python", "python", True), ("C++", "cplusplus", True), ("C", "c", False),
        ("Java", "openjdk", False), ("TypeScript", "typescript", True),
        ("JavaScript", "javascript", False), ("SQL", "postgresql", True),
        ("R", "r", False), ("Bash", "gnubash", False), ("ROS2", "ros", True),
        ("React", "react", False), ("Node.js", "nodedotjs", False), ("Flask", "flask", False),
    ]),
    ("AI / ML", [
        ("PyTorch", "pytorch", True), ("TensorFlow", "tensorflow", True),
        ("scikit-learn", "scikitlearn", False), ("OpenCV", "opencv", True),
        ("ONNX", "onnx", True), ("TensorRT", "nvidia", True), ("CUDA", "nvidia", True),
        ("Transformers", "huggingface", True), ("Keras", "keras", False),
        ("NumPy", "numpy", True), ("Pandas", "pandas", True), ("Plotly", "plotly", False),
    ]),
    ("CLOUD & DEPLOYMENT", [
        ("AWS", "amazonwebservices", True), ("SageMaker", "amazonwebservices", False),
        ("Bedrock", "amazonwebservices", False), ("Lambda", "awslambda", False),
        ("S3", "amazons3", False), ("DynamoDB", "amazondynamodb", False),
        ("API Gateway", "amazonapigateway", False), ("Azure", None, False),
        ("Docker", "docker", True), ("Kubernetes", "kubernetes", False),
        ("CI/CD", "githubactions", False), ("Jetson", "nvidia", True),
        ("Linux", "linux", True), ("Git", "git", True),
    ]),
]

LEARNING = [
    ("CUDA", "nvidia", True), ("LangChain", "langchain", True),
    ("LangGraph", "langchain", True), ("vLLM", None, True),
    ("Kubernetes", "kubernetes", True), ("JAX", None, True),
]


def _marquee_block(path, cmd, rows, label, speed0=42):
    W = 1200
    tdefs, tbody, top = typing_title(cmd)
    top += 16                       # clear the title before the first row label
    row_gap = 62
    H = top + len(rows) * row_gap + 12
    clips, out, heads = [], [], []
    for i, (title, items) in enumerate(rows):
        y = top + i * row_gap
        if title:
            heads.append(f'<text x="26" y="{y - 6}" font-family="{MONO}" font-size="10" '
                         f'fill="{DIM}" letter-spacing="1.2">{esc(title)}</text>')
        clips.append(f'<clipPath id="clip{i}"><rect x="0" y="{y - 2}" width="{W}" height="{CHIP_H + 4}"/></clipPath>')
        out.append(marquee(items, y, rtl=(i % 2 == 1), view_w=W, speed=speed0 + i * 6, rid=i))
    edge = (f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{BG}" stop-opacity="1"/><stop offset="0.05" stop-color="{BG}" stop-opacity="0"/>'
            f'<stop offset="0.95" stop-color="{BG}" stop-opacity="0"/><stop offset="1" stop-color="{BG}" stop-opacity="1"/>'
            f'</linearGradient>')
    body = "".join(heads) + "".join(out) + f'<rect y="{top - 6}" width="{W}" height="{H - top + 6}" fill="url(#edge)" pointer-events="none"/>' + tbody
    return write(path, svg(W, H, icon_defs(rows) + edge + "".join(clips) + tdefs, body, label))


def build_stack(path):
    return _marquee_block(path, "cat stack.txt", ROWS,
                          "Technology stack: languages and frameworks, AI/ML, cloud and deployment")


def build_learning(path):
    return _marquee_block(path, "cat currently_learning.txt", [("", LEARNING)],
                          "Currently learning: CUDA, LangChain, LangGraph, vLLM, Kubernetes, JAX", speed0=34)


# ----------------------------------------------------------------- about

ABOUT = [
    ("based_in", "Irvine, CA"),
    ("studying", "B.S. Computer Science (Honors) @ UC Irvine — class of 2028 · GPA 3.78"),
    ("right_now", "Data Scientist Intern @ AbbVie · AI SWE Intern @ SecondWind · Autonomous Nav @ Legacy Robotics"),
    ("focus", "computer vision · multimodal LLMs · edge inference · agentic systems"),
    ("off_the_clock", None),
    (None, "anime and manga — Vagabond, Fullmetal Alchemist, JoJo's Bizarre Adventure, Jujutsu Kaisen, Dragon Ball"),
    (None, "sketching, mostly in the margins of lecture notes"),
    (None, "pickup basketball, volleyball, and football on weekends"),
    ("philosophy", "\"we dont need the memories\""),
]


def build_about(path):
    W, lh, size = 1200, 26, 14
    tdefs, tbody, top = typing_title("cat about.yaml")
    H = top + len(ABOUT) * lh + 18
    out = []
    for i, (k, v) in enumerate(ABOUT):
        y = top + 16 + i * lh
        if k is None:
            out.append(f'<text x="52" y="{y}" font-family="{MONO}" font-size="{size}" fill="{DIM}">-</text>')
            out.append(f'<text x="70" y="{y}" font-family="{MONO}" font-size="{size}" fill="{MUTED}">{esc(v)}</text>')
        else:
            out.append(f'<text x="26" y="{y}" font-family="{MONO}" font-size="{size}" fill="{ACCENT}">{esc(k)}:</text>')
            if v:
                out.append(f'<text x="{26 + text_w("off_the_clock:  ", size):.0f}" y="{y}" '
                           f'font-family="{MONO}" font-size="{size}" fill="{TEXT}">{esc(v)}</text>')
    return write(path, svg(W, H, tdefs, "".join(out) + tbody, "About: location, studies, current roles and focus"))


# --------------------------------------------------------------- projects

CARDS = [
    ("NIMBUS", "real-time sign language → English, in the browser",
     ["An ONNX-compiled TGCN model parses 55 MediaPipe keypoints at",
      "30 FPS in a Web Worker, behind 9+ Lambdas and API Gateway",
      "WebSockets feeding Bedrock for live multi-user captioning."],
     ["800ms → 15ms", "<1.5s end-to-end"],
     ["ONNX", "MediaPipe", "Lambda", "Bedrock"]),
    ("VIPER", "AI-generated image forensics · 1st of 120+, UCI Datathon",
     ["A 28M-parameter fine-tuned CNN concatenated with 33 engineered",
      "forensic features, made explainable with Grad-CAM heatmaps and",
      "UMAP rather than left as a black box."],
     ["98.9% accuracy", "500K+ images"],
     ["PyTorch", "ConvNeXt", "Grad-CAM", "UMAP"]),
    ("SIX EYES", "one dashboard, six drones, zero blind spots",
     ["Synchronized live video and telemetry from 6 concurrent UAVs",
      "over WebSockets, with search coverage auto-computed from",
      "operator-drawn map areas and split across the fleet."],
     ["4x less load", "<100ms latency"],
     ["Python", "YOLOv8n", "WebSockets", "React"]),
    ("LEGACY ROBOTICS", "autonomous navigation · UCI University Rover Challenge",
     ["YOLOv11 compiled to ONNX and optimized with TensorRT on a",
      "Jetson, fused with RTK-GNSS and IMU through A* global and",
      "VFH/DWA local planners."],
     ["sub-30ms", "96.5% precision"],
     ["ROS2", "TensorRT", "C++", "Jetson"]),
]


def build_card(path, card):
    """Authored at display size so text is not shrunk by GitHub's column."""
    name, tag, lines, metrics, stack = card
    W, H = 415, 238
    out = [f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" fill="{PANEL}" stroke="{LINE}"/>',
           f'<rect x="0" y="0" width="3" height="{H}" fill="{ACCENT}"/>']
    out.append(f'<text x="18" y="30" font-family="{MONO}" font-size="15" font-weight="700" fill="{ACCENT}">{esc(name)}</text>')
    out.append(f'<text x="18" y="49" font-family="{MONO}" font-size="10.5" fill="{MUTED}">{esc(tag)}</text>')
    for i, ln in enumerate(lines):
        out.append(f'<text x="18" y="{78 + i * 17}" font-family="{MONO}" font-size="10.5" fill="{TEXT}">{esc(ln)}</text>')
    x = 18
    for m in metrics:
        w = text_w(m, 10) + 16
        out.append(f'<rect x="{x}" y="{142}" width="{w:.0f}" height="20" fill="{ACCENT}"/>')
        out.append(f'<text x="{x + 8}" y="{156}" font-family="{MONO}" font-size="10" font-weight="700" fill="{BG}">{esc(m)}</text>')
        x += w + 7
    x = 18
    for t in stack:
        w = text_w(t, 10) + 14
        out.append(f'<rect x="{x}" y="{176}" width="{w:.0f}" height="19" fill="none" stroke="#2b2440"/>')
        out.append(f'<text x="{x + 7}" y="{189}" font-family="{MONO}" font-size="10" fill="{MUTED}">{esc(t)}</text>')
        x += w + 6
    out.append(f'<text x="18" y="{219}" font-family="{MONO}" font-size="10" fill="{DIM}">$ git clone →</text>')
    return write(path, svg(W, H, "", "".join(out), f"{name}: {tag}"))


# ---------------------------------------------------------------- contact

CONTACTS = [
    ("harmeet-singh.dev", "portfolio & writeups", "vercel"),
    ("harmeets130922@gmail.com", "best way to reach me", "gmail"),
    ("in/harmeet-singh-uppal", "let's connect", "linkedin"),
    ("github.com/har-m33t", "27 repositories", "github"),
]


def build_contact(path, item):
    label, sub, slug = item
    W, H = 415, 92
    ic = ICONS.get(slug)
    out = [f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" fill="{PANEL}" stroke="{LINE}"/>']
    if ic:
        out.append(f'<g transform="translate(22,30) scale({26 / 24:.4f})"><path d="{ic["d"]}" fill="{ACCENT}"/></g>')
    out.append(f'<text x="64" y="42" font-family="{MONO}" font-size="14" font-weight="700" fill="{TEXT}">{esc(label)}</text>')
    out.append(f'<text x="64" y="62" font-family="{MONO}" font-size="11" fill="{MUTED}">{esc(sub)}</text>')
    return write(path, svg(W, H, "", "".join(out), f"{label} - {sub}"))


def build_title(path, cmd, label):
    W = 1200
    tdefs, tbody, top = typing_title(cmd)
    return write(path, svg(W, top + 4, tdefs, tbody, label))


# ----------------------------------------------------------- experience.svg

ROLES = [
    ("AbbVie", "Clinical Innovation R&D", "Data Scientist Intern, CV + ML",
     "Jun 2026 - Present", "HRNetV2+OCR segmentation on SageMaker, 82% pixel acc, 9x faster inference", True),
    ("SecondWind", "AI Engineering", "AI Software Engineer Intern",
     "Aug 2026 - Present", "AI agents and the infrastructure they run on - orchestration, tooling and evaluation pipelines", True),
    ("Legacy Robotics", "URC Team @ UCI", "SWE, Autonomous Navigation",
     "Apr 2026 - Present", "YOLOv11 to TensorRT, sub-30ms on Jetson; ROS2 stack to sub-5cm localization", True),
    ("Univ. of Arizona", "College of Medicine", "AI + Bioinformatics Research Intern",
     "Jun 2026 - Aug 2026", "Two-stage multimodal LLM pipeline, 150M+ param encoders over 1.1M+ RNA samples", False),
]


def build_experience(path):
    W, row_h = 1200, 86
    tdefs, tbody, top = typing_title("cat experience.log")
    H = top + row_h * len(ROLES) + 8
    out = []
    for i, (org, unit, title, when, detail, current) in enumerate(ROLES):
        y = top + i * row_h
        out.append(f'<circle cx="32" cy="{y + 14}" r="5" fill="{ACCENT if current else "#40275c"}"/>')
        if i < len(ROLES) - 1:
            out.append(f'<line x1="32" y1="{y + 24}" x2="32" y2="{y + row_h - 4}" stroke="{LINE}"/>')
        out.append(f'<text x="54" y="{y + 19}" font-family="{MONO}" font-size="16" font-weight="700" fill="{TEXT}">{esc(org)}'
                   f'<tspan fill="{MUTED}" font-weight="400" font-size="13">  {esc(unit)}</tspan></text>')
        out.append(f'<text x="{W - 30}" y="{y + 19}" text-anchor="end" font-family="{MONO}" font-size="12" '
                   f'fill="{ACCENT if current else MUTED}">{esc(when)}</text>')
        out.append(f'<text x="54" y="{y + 40}" font-family="{MONO}" font-size="13" fill="{ACCENT}" fill-opacity="0.8">{esc(title)}</text>')
        out.append(f'<text x="54" y="{y + 60}" font-family="{MONO}" font-size="12" fill="{MUTED}">{esc(detail)}</text>')
    return write(path, svg(W, H, tdefs, "".join(out) + tbody, "Experience timeline"))


# ---------------------------------------------------------------- stats.svg

GQL = """query($login:String!){ user(login:$login){
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ contributionCount date } } } }
  repositories(first:100,ownerAffiliations:OWNER,isFork:false){ nodes{ languages(first:10){ edges{ size node{ name } } } } }
  pullRequests{ totalCount } } }"""


def collect(login, token):
    if not token:
        return None
    try:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": GQL, "variables": {"login": login}}).encode(),
            headers={"Authorization": "bearer " + token, "Content-Type": "application/json",
                     "User-Agent": "profile-asset-builder"})
        u = json.load(urllib.request.urlopen(req, timeout=45))["data"]["user"]
    except Exception as e:
        print("graphql failed:", e, file=sys.stderr)
        return None
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    langs = {}
    for n in u["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    best = cur = 0
    for d in days:
        cur = cur + 1 if d["contributionCount"] > 0 else 0
        best = max(best, cur)
    return {"total": cal["totalContributions"], "days": days,
            "langs": sorted(langs.items(), key=lambda kv: -kv[1]),
            "prs": u["pullRequests"]["totalCount"], "streak": best}


def build_stats(path, data):
    W, cell, gap = 1200, 15, 3
    tdefs, tbody, top = typing_title("gh contributions --grid")
    weeks = [data["days"][i:i + 7] for i in range(0, len(data["days"]), 7)][-53:]
    peak = max((d["contributionCount"] for d in data["days"]), default=1) or 1
    gtop = top + 22
    grid = []
    for wi, wk in enumerate(weeks):
        for di, d in enumerate(wk):
            c = d["contributionCount"]
            lvl = 0 if c == 0 else min(4, 1 + int(3 * c / peak))
            grid.append(f'<rect x="{30 + wi * (cell + gap)}" y="{gtop + di * (cell + gap)}" '
                        f'width="{cell}" height="{cell}" fill="{"#141122" if c == 0 else RAMP[lvl]}"/>')
    gx = 30 + len(weeks) * (cell + gap) + 26
    side = []
    for i, (lab, val, col) in enumerate([("contributions", f'{data["total"]:,}', ACCENT),
                                         ("longest streak", f'{data["streak"]}d', TEXT),
                                         ("pull requests", str(data["prs"]), TEXT)]):
        y = gtop + 8 + i * 58
        side.append(f'<text x="{gx}" y="{y + 22}" font-family="{MONO}" font-size="26" font-weight="700" fill="{col}">{esc(val)}</text>')
        side.append(f'<text x="{gx}" y="{y + 40}" font-family="{MONO}" font-size="11" fill="{MUTED}">{esc(lab)}</text>')
    ybar = max(gtop + 7 * (cell + gap) + 22, gtop + 8 + 3 * 58 + 14)
    tot = sum(v for _, v in data["langs"]) or 1
    bar, leg, bx, lx = [], [], 30, 30
    for i, (name, size) in enumerate(data["langs"][:5]):
        w = (size / tot) * (W - 60)
        col = RAMP[max(0, 4 - i)]
        bar.append(f'<rect x="{bx:.1f}" y="{ybar}" width="{w:.1f}" height="9" fill="{col}"/>')
        bx += w
        lbl = f"{name} {100 * size / tot:.1f}%"
        leg.append(f'<rect x="{lx}" y="{ybar + 24}" width="8" height="8" fill="{col}"/>')
        leg.append(f'<text x="{lx + 13}" y="{ybar + 32}" font-family="{MONO}" font-size="11" fill="{MUTED}">{esc(lbl)}</text>')
        lx += 13 + text_w(lbl, 11) + 22
    H = ybar + 48
    body = (f'<text x="{W - 30}" y="{top - 10}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{DIM}">last 12 months</text>'
            + "".join(grid) + "".join(side)
            + f'<line x1="30" y1="{ybar - 14}" x2="{W - 30}" y2="{ybar - 14}" stroke="{LINE}"/>'
            + "".join(bar) + "".join(leg) + tbody)
    return write(path, svg(W, H, tdefs, body, "GitHub contribution activity"))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assets"
    os.makedirs(out, exist_ok=True)
    p = lambda n: os.path.join(out, n)
    print("wrote", build_stack(p("stack.svg")))
    print("wrote", build_learning(p("learning.svg")))
    print("wrote", build_about(p("about.svg")))
    print("wrote", build_experience(p("experience.svg")))
    print("wrote", build_title(p("title-builds.svg"), "ls ~/builds", "Featured builds"))
    print("wrote", build_title(p("title-contact.svg"), "cat contact.txt", "Contact"))
    for c, slug in zip(CARDS, ["nimbus", "viper", "sixeyes", "legacy"]):
        print("wrote", build_card(p(f"card-{slug}.svg"), c))
    for c, slug in zip(CONTACTS, ["site", "email", "linkedin", "github"]):
        print("wrote", build_contact(p(f"contact-{slug}.svg"), c))
    data = collect(os.environ.get("GH_LOGIN", "har-m33t"),
                   os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    if data:
        print("wrote", build_stats(p("stats.svg"), data))
    else:
        print("skipped stats.svg (no token / API unavailable)", file=sys.stderr)
