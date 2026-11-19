"""'diagram' 장(박스+화살표 흐름도)을 HTML로 그린 뒤 헤드리스 크롬으로 PNG를 찍는다.
화살표 연결 엔진: vendor/html-diagram (tonywjs/html-diagram, MIT).

slide 예시:
{"type":"diagram", "kicker":"어떻게 무너졌나", "title":["계획경제가","멈춘 과정"],
 "nodes":[{"id":"a","x":80,"y":420,"w":400,"h":170,"title":"소련 붕괴","sub":"원조 중단","tone":"bad"}, ...],
 "edges":[{"from":"a","to":"b","label":"그 결과","style":"solid"}],
 "source":"출처"}
좌표는 1080x1350 카드 기준 픽셀. tone: good(파랑) / bad(빨강) / gold / plain
"""
import html, os, re, shutil

W, H = 1080, 1350
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "vendor", "html-diagram", "template.html")
HANDLE, BRAND = "@weight.of.facts", "팩트의 무게"
COLORS = {"good": "#5BB8FF", "bad": "#FF4D5E", "gold": "#FFD166", "plain": "#E3E8F2"}

STYLE = """
:root{--navy:#0F1E3D;--red:#FF4D5E;--gold:#FFD166;--blue:#5BB8FF;--sub:#E3E8F2;
  --font:'Noto Sans CJK KR','Noto Sans KR','Pretendard','Apple SD Gothic Neo','Malgun Gothic',sans-serif;}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px;overflow:hidden;background:var(--navy)}
body{font-family:var(--font);color:#fff;-webkit-font-smoothing:antialiased}
.fig-stage{width:1080px;height:1350px;padding:0;margin:0;background:var(--navy);border-radius:0;box-shadow:none;max-width:none}
.topbar{background:var(--red)}
.brand{font-size:30px;font-weight:700;color:#fff}
.pageno{font-size:30px;font-weight:700;color:#fff;text-align:right}
.kick{font-size:44px;font-weight:700;color:var(--gold);line-height:1.2}
.ttl{font-size:68px;font-weight:900;line-height:1.22;letter-spacing:-.01em}
.box{width:100%;height:100%;border-radius:24px;border:5px solid var(--c);background:rgba(255,255,255,.04);
  display:flex;flex-direction:column;justify-content:center;padding:18px 26px}
.box .bt{font-size:44px;font-weight:900;color:var(--c);line-height:1.18}
.box .bs{font-size:34px;font-weight:600;color:var(--sub);line-height:1.3;margin-top:8px}
.fig-elabel{font-size:28px!important;font-weight:800!important;padding:4px 16px!important;
  background:var(--navy)!important;color:var(--gold)!important;border:2px solid var(--gold)!important;border-radius:22px!important}
.fig-pill,.fig-dock,.fig-menu{display:none!important}
/* 손그림 잉크 느낌 (line-art-animation ink.ts의 inkDefs 필터 값, MIT) */
.ink .box{border:none;position:relative}
.ink .box::before{content:"";position:absolute;inset:0;border:5px solid var(--c);border-radius:24px;filter:url(#ink-edge)}
.ink .fig-edges{filter:url(#ink-edge)}
.ink .ttl u{text-decoration:none;background:none;position:relative}
.src{font-size:24px;color:#C9D3E6;line-height:1.3}
.handle{font-size:30px;font-weight:700;color:#fff;text-align:right}
"""


def esc(t):
    return html.escape(str(t))


def build_html(s, page, total):
    nodes = []
    add = nodes.append
    add('<div class="fig-node topbar" id="x-bar" style="left:0px;top:0px;width:1080px;height:14px"></div>')
    add(f'<div class="fig-node brand" id="x-brand" style="left:60px;top:44px;width:500px;height:44px;background:transparent;border:none">{esc(BRAND)}</div>')
    add(f'<div class="fig-node pageno" id="x-page" style="left:820px;top:44px;width:200px;height:44px;background:transparent;border:none">{page}/{total}</div>')
    y = 130
    if s.get("kicker"):
        add(f'<div class="fig-node kick" id="x-kick" style="left:60px;top:{y}px;width:960px;height:60px;background:transparent;border:none">{esc(s["kicker"])}</div>')
        y += 72
    title = s.get("title") or []
    if title:
        th = 84 * len(title)
        add(f'<div class="fig-node ttl" id="x-title" style="left:60px;top:{y}px;width:960px;height:{th}px;background:transparent;border:none">{"<br>".join(esc(t) for t in title)}</div>')
    for n in s["nodes"]:
        c = COLORS.get(n.get("tone", "plain"), COLORS["plain"])
        sub = f'<div class="bs">{"<br>".join(esc(x) for x in (n["sub"] if isinstance(n.get("sub"), list) else [n["sub"]]))}</div>' if n.get("sub") else ""
        t = "<br>".join(esc(x) for x in (n["title"] if isinstance(n["title"], list) else [n["title"]]))
        add(f'<div class="fig-node" id="n-{esc(n["id"])}" style="left:{n["x"]}px;top:{n["y"]}px;width:{n["w"]}px;height:{n["h"]}px;--c:{c}">'
            f'<div class="box"><div class="bt">{t}</div>{sub}</div></div>')
    for e in s.get("edges", []):
        col = COLORS.get(e.get("tone", "gold"), COLORS["gold"])
        attrs = [f'data-from="n-{esc(e["from"])}"', f'data-to="n-{esc(e["to"])}"', f'data-color="{col}"',
                 f'data-width="{e.get("width", 6)}"', f'data-style="{e.get("style", "solid")}"',
                 f'data-arrow="{e.get("arrow", "end")}"', f'data-curve="{e.get("curve", 0)}"']
        if e.get("label"):
            attrs.append(f'data-label="{esc(e["label"])}"')
        for k in ("anchor_from", "anchor_to"):
            if e.get(k):
                attrs.append(f'data-{k.replace("_", "-")}="{esc(e[k])}"')
        add(f'<div class="fig-edge" {" ".join(attrs)}></div>')
    if s.get("source"):
        add(f'<div class="fig-node src" id="x-src" style="left:60px;top:1230px;width:960px;height:34px;background:transparent;border:none">출처: {esc(s["source"])}</div>')
    add(f'<div class="fig-node handle" id="x-handle" style="left:560px;top:1280px;width:460px;height:42px;background:transparent;border:none">{esc(HANDLE)}</div>')

    tpl = open(TEMPLATE, encoding="utf-8").read()
    tpl = tpl.replace("<title>도식</title>", f"<title>{esc(BRAND)} {page}</title>", 1)
    tpl = re.sub(r"<style>.*?</style>", "<style>" + STYLE + "</style>", tpl, count=1, flags=re.S)
    ink = s.get("style") == "ink"
    defs = ('<svg width="0" height="0" style="position:absolute"><filter id="ink-edge" x="-3%" y="-3%" width="106%" height="106%">'
            '<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"/>'
            '<feDisplacementMap in="SourceGraphic" in2="n" scale="7" xChannelSelector="R" yChannelSelector="G" result="d"/>'
            '<feGaussianBlur in="d" stdDeviation="0.5"/></filter></svg>') if ink else ""
    content = defs + f'<div class="fig-canvas{" ink" if ink else ""}" data-size="{W}x{H}">\n' + "\n".join(nodes) + "\n</div>"
    tpl = re.sub(r"(FIG:CONTENT START.*?-->).*?(<!-- =+ FIG:CONTENT END)",
                 lambda m: m.group(1) + "\n" + content + "\n" + m.group(2), tpl, count=1, flags=re.S)
    return tpl


def find_chrome():
    for c in ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(c):
            return c
    return shutil.which("google-chrome") or shutil.which("chromium")


def render_diagram(s, page, total, out_png):
    from playwright.sync_api import sync_playwright
    doc = build_html(s, page, total)
    tmp = out_png.replace(".png", ".html")
    open(tmp, "w", encoding="utf-8").write(doc)
    with sync_playwright() as p:
        kw = {"executable_path": find_chrome()} if find_chrome() else {}
        b = p.chromium.launch(**kw)
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.goto("file://" + os.path.abspath(tmp))
        pg.wait_for_timeout(800)  # 엔진이 화살표를 그릴 시간
        pg.screenshot(path=out_png, clip={"x": 0, "y": 0, "width": W, "height": H})
        b.close()
    os.remove(tmp)
