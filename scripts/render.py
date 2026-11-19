"""카드뉴스 그리기: content/<글>/post.json 의 slides 를 읽어서 slide_1.png ... 를 만든다.

사용법:  python scripts/render.py content/001-freedom-intro
         python scripts/render.py --missing      (그림이 없는 글만 전부 그림)

노안 배려 규칙: 가장 작은 글씨 36px 이상, 본문 58px 이상, 밝은 대비.
글이 길면 글씨를 자동으로 줄이되, 최소 크기 밑으로는 줄이지 않고 줄바꿈한다.
"""
import json, os, sys, glob
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
NAVY, RED, WHITE, GOLD, BLUE = "#0F1E3D", "#FF4D5E", "#FFFFFF", "#FFD166", "#5BB8FF"
SUB = "#E3E8F2"
PAPER, INK, INK2, DEEPRED = "#FBF8F1", "#0F1E3D", "#33384A", "#D7263D"
HANDLE = "@weight.of.facts"
BRAND = "팩트의 무게"
MARGIN = 60

FONT_DIRS = ["/usr/share/fonts/opentype/noto", "/usr/share/fonts/noto-cjk", "/usr/share/fonts/opentype/noto-cjk"]
_cache = {}


def F(weight, size):
    key = (weight, size)
    if key in _cache:
        return _cache[key]
    for d in FONT_DIRS:
        p = os.path.join(d, f"NotoSansCJK-{weight}.ttc")
        if os.path.exists(p):
            _cache[key] = ImageFont.truetype(p, size, index=1)  # index 1 = KR
            return _cache[key]
    raise SystemExit("한글 글꼴(Noto Sans CJK)을 찾을 수 없어요. sudo apt-get install fonts-noto-cjk")


def wrap(d, text, font, max_w):
    """글자 단위 줄바꿈 (띄어쓰기 우선)."""
    out = []
    for para in text.split("\n"):
        words, line = para.split(" "), ""
        for w in words:
            cand = (line + " " + w).strip()
            if d.textlength(cand, font=font) <= max_w:
                line = cand
            else:
                if line:
                    out.append(line)
                line = w
                while d.textlength(line, font=font) > max_w:  # 아주 긴 단어
                    cut = len(line)
                    while cut > 1 and d.textlength(line[:cut], font=font) > max_w:
                        cut -= 1
                    out.append(line[:cut]); line = line[cut:]
        out.append(line)
    return out


def fit(d, lines, weight, size, min_size, max_w, max_h, gap):
    """lines(줄 목록)이 상자에 들어가도록 글씨 크기를 고른다."""
    text = "\n".join(lines)
    s = size
    while True:
        f = F(weight, s)
        ls = wrap(d, text, f, max_w)
        h = len(ls) * int(s * gap)
        if h <= max_h or s <= min_size:
            return f, ls
        s -= 4


def block(d, lines, weight, size, min_size, y, color, max_h, gap=1.28, max_w=W - 2 * MARGIN, center=False):
    if not lines:
        return y
    f, ls = fit(d, lines, weight, size, min_size, max_w, max_h, gap)
    lh = int(f.size * gap)
    for i, t in enumerate(ls):
        x = (W - d.textlength(t, font=f)) / 2 if center else MARGIN
        d.text((x, y + i * lh), t, font=f, fill=color)
    return y + len(ls) * lh


def base(page, total, dark=True):
    bg = NAVY if dark else PAPER
    fg = SUB if dark else INK2
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 16], fill=RED)
    d.text((MARGIN, 50), BRAND, font=F("Bold", 44), fill=fg)
    d.text((W - MARGIN, 50), f"{page}/{total}", font=F("Bold", 44), fill=fg, anchor="ra")
    d.text((W - MARGIN, H - 50), HANDLE, font=F("Bold", 40), fill=fg, anchor="rs")
    return im, d


def source(d, text, dark=True):
    if text:
        f, ls = fit(d, ["출처: " + text], "Medium", 36, 30, W - 2 * MARGIN, 100, 1.25)
        y = H - 120 - len(ls) * int(f.size * 1.25)
        for i, t in enumerate(ls):
            d.text((MARGIN, y + i * int(f.size * 1.25)), t, font=f, fill=SUB if dark else INK2)


# ---------------- 장 종류별 그리기 ----------------

def s_cover(s, p, n):
    im, d = base(p, n)
    y = block(d, s.get("lines", []), "Black", 130, 96, 230, WHITE, 470, 1.2)
    y = block(d, s.get("accent", []), "Black", 130, 96, y + 10, RED, 1000 - y, 1.2)
    block(d, s.get("sub", []), "Bold", 62, 54, y + 50, SUB, 1180 - y - 50)
    return im


def s_text(s, p, n):
    im, d = base(p, n)
    y = 200
    if s.get("kicker"):
        y = block(d, [s["kicker"]], "Black", 100, 64, y, GOLD, 260, 1.2) + 30
    y = block(d, s.get("lines", []), "Black", 112, 76, y, WHITE, 1100 - y, 1.25)
    block(d, s.get("sub", []), "Bold", 70, 58, y + 50, SUB, 1180 - y - 50)
    source(d, s.get("source"))
    return im


def s_stat(s, p, n):
    im, d = base(p, n)
    y = block(d, s.get("label", []), "Bold", 62, 52, 190, GOLD, 200, 1.3)
    y = max(y + 30, 400)
    y = block(d, [s.get("number", "")], "Black", 150, 96, y, RED, 230, 1.2)
    y = block(d, s.get("main", []), "Black", 92, 66, y + 10, WHITE, 300, 1.25)
    block(d, s.get("sub", []), "Bold", 66, 56, y + 40, SUB, 1150 - y - 40)
    source(d, s.get("source"))
    return im


def s_bars(s, p, n):
    im, d = base(p, n)
    y = block(d, s.get("label", []), "Bold", 62, 52, 190, GOLD, 200, 1.3)
    rows = s.get("rows", [])
    step = min(230, int((1130 - max(y + 40, 420)) / max(1, len(rows))))
    y = max(y + 40, 420)
    top = max(r["value"] for r in rows) if rows else 100
    scale_max = s.get("max", 100) or top
    for r in rows:
        col = {"good": BLUE, "bad": RED}.get(r.get("tone"), WHITE)
        f = F("Black", 84 if step >= 200 else 68)
        d.text((MARGIN, y), r["name"], font=f, fill=WHITE)
        d.text((W - MARGIN, y), r.get("text", f'{r["value"]}'), font=f, fill=col, anchor="ra")
        by = y + int(f.size * 1.4)
        d.rounded_rectangle([MARGIN, by, W - MARGIN, by + 45], radius=22, fill="#2A3B63")
        d.rounded_rectangle([MARGIN, by, MARGIN + max(45, (W - 2 * MARGIN) * r["value"] / scale_max), by + 45], radius=22, fill=col)
        y += step
    source(d, s.get("source"))
    return im


def s_compare(s, p, n):
    im, d = base(p, n)
    y = block(d, s.get("title", []), "Black", 100, 72, 135, WHITE, 260, 1.15)
    boxes = [s.get("left", {}), s.get("right", {})]
    tones = [BLUE, RED]
    top = max(y + 30, 420)
    bh = int((1250 - top - 30) / 2)
    for i, b in enumerate(boxes):
        bt = top + i * (bh + 30)
        col = tones[i] if b.get("tone") is None else {"good": BLUE, "bad": RED}.get(b["tone"], WHITE)
        d.rounded_rectangle([MARGIN, bt, W - MARGIN, bt + bh], radius=30, outline=col, width=6)
        d.text((MARGIN + 40, bt + 25), b.get("title", ""), font=F("Black", 70), fill=col)
        items = ["· " + t for t in b.get("items", [])]
        f, ls = fit(d, items, "Bold", 58, 46, W - 2 * MARGIN - 80, bh - 135, 1.35)
        for j, t in enumerate(ls):
            d.text((MARGIN + 40, bt + 115 + j * int(f.size * 1.35)), t, font=f, fill=WHITE)
    return im


def s_closing(s, p, n):
    im, d = base(p, n, dark=False)
    y = block(d, s.get("lines", ["자유는", "지키는 사람의", "것입니다"]), "Black", 124, 88, 230, INK, 500, 1.2)
    d.rectangle([MARGIN, y + 40, MARGIN + 200, y + 56], fill=DEEPRED)
    y = block(d, s.get("sub", []), "Bold", 70, 58, y + 100, INK2, 300)
    block(d, [s.get("cta", "팔로우하고 함께 기록해요")], "Black", 62, 52, y + 60, DEEPRED, 120)
    return im


KINDS = {"cover": s_cover, "text": s_text, "stat": s_stat, "bars": s_bars, "compare": s_compare, "closing": s_closing}


def render(folder):
    with open(os.path.join(folder, "post.json"), encoding="utf-8") as fp:
        post = json.load(fp)
    slides = post["slides"]
    n = len(slides)
    if not 2 <= n <= 10:
        raise SystemExit(f"{folder}: 카드는 2~10장이어야 해요 (지금 {n}장)")
    for old in glob.glob(os.path.join(folder, "slide_*.png")):
        os.remove(old)
    for i, s in enumerate(slides, 1):
        out = os.path.join(folder, f"slide_{i}.png")
        if s["type"] == "diagram":  # 박스+화살표 흐름도는 HTML 엔진으로
            from render_diagram import render_diagram
            render_diagram(s, i, n, out)
            continue
        im = KINDS[s["type"]](s, i, n)
        im.save(out, optimize=True)
    # 미리보기 한 장 (검수용)
    sw = 300; sh = int(sw * H / W); pad = 20; cols = min(4, n); rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (pad + cols * (sw + pad), pad + rows * (sh + pad)), "#DDDDDD")
    for i in range(n):
        im = Image.open(os.path.join(folder, f"slide_{i + 1}.png")).resize((sw, sh))
        sheet.paste(im, (pad + (i % cols) * (sw + pad), pad + (i // cols) * (sh + pad)))
    sheet.save(os.path.join(folder, "preview.png"), optimize=True)
    print(f"그림 완료: {folder} ({n}장)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--missing"]:
        for pj in sorted(glob.glob("content/*/post.json")):
            folder = os.path.dirname(pj)
            post = json.load(open(pj, encoding="utf-8"))
            if not os.path.exists(os.path.join(folder, f"slide_{len(post['slides'])}.png")):
                render(folder)
    else:
        for a in args:
            render(a)
