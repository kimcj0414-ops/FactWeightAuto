"""승인된 카드뉴스를 인스타그램과 Threads에 올린다 (GitHub Actions에서 실행).

필요한 비밀값 (GitHub > Settings > Secrets and variables > Actions):
  THREADS_TOKEN   Threads 열쇠
  IG_TOKEN        인스타 열쇠
  IG_USER_ID      인스타 계정 번호 (모르면 check 모드로 찾을 수 있음)
선택: IG_API_HOST (기본 graph.facebook.com), IG_API_VERSION (기본 v22.0)

모드:
  python scripts/publish.py check            열쇠가 제대로 되는지 확인만
  python scripts/publish.py run              올릴 시간이 된 '승인' 글을 올림
  python scripts/publish.py now <글 폴더>    그 글을 지금 바로 올림 (시험용)
"""
import json, os, sys, time, glob, datetime, urllib.request, urllib.parse, urllib.error

KST = datetime.timezone(datetime.timedelta(hours=9))
REPO = os.environ.get("GITHUB_REPOSITORY", "kimcj0414-ops/FactWeightAuto")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
TH_TOKEN = os.environ.get("THREADS_TOKEN", "")
IG_TOKEN = os.environ.get("IG_TOKEN", "")
IG_USER = os.environ.get("IG_USER_ID", "")
IG_HOST = os.environ.get("IG_API_HOST", "graph.facebook.com")
IG_VER = os.environ.get("IG_API_VERSION", "v22.0")
TH_BASE = "https://graph.threads.net/v1.0"


def call(method, url, params=None):
    data = None
    if params:
        enc = urllib.parse.urlencode(params)
        if method == "GET":
            url += ("&" if "?" in url else "?") + enc
        else:
            data = enc.encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {url.split('?')[0]} -> {e.code}: {body[:500]}")


def wait_ready(get_status, label, tries=30):
    for _ in range(tries):
        st = get_status()
        if st in ("FINISHED", "PUBLISHED", None):
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"{label} 처리 실패: {st}")
        time.sleep(5)
    raise RuntimeError(f"{label} 처리 시간이 너무 오래 걸림")


def image_urls(folder, n):
    rel = folder.replace(os.sep, "/")
    return [f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{rel}/slide_{i}.png" for i in range(1, n + 1)]


# ---------------- Threads ----------------
def threads_post(urls, text):
    kids = []
    for u in urls:
        r = call("POST", f"{TH_BASE}/me/threads", {"media_type": "IMAGE", "image_url": u, "is_carousel_item": "true", "access_token": TH_TOKEN})
        kids.append(r["id"])
    for k in kids:
        wait_ready(lambda k=k: call("GET", f"{TH_BASE}/{k}", {"fields": "status", "access_token": TH_TOKEN}).get("status"), "Threads 사진")
    c = call("POST", f"{TH_BASE}/me/threads", {"media_type": "CAROUSEL", "children": ",".join(kids), "text": text[:500], "access_token": TH_TOKEN})
    wait_ready(lambda: call("GET", f"{TH_BASE}/{c['id']}", {"fields": "status", "access_token": TH_TOKEN}).get("status"), "Threads 묶음")
    pub = call("POST", f"{TH_BASE}/me/threads_publish", {"creation_id": c["id"], "access_token": TH_TOKEN})
    try:  # 이미 올라간 뒤라 여기서 실패해도 다시 올리지 않는다
        link = call("GET", f"{TH_BASE}/{pub['id']}", {"fields": "permalink", "access_token": TH_TOKEN}).get("permalink", "")
    except Exception:
        link = ""
    return {"id": pub["id"], "permalink": link}


def threads_post_retry(urls, text, tries=3, wait=60):
    """Threads가 사진을 못 가져오거나(일시 오류) 묶음을 못 찾을 때 처음부터 다시 시도.
    threads_publish 가 성공한 뒤에는 재시도하지 않으므로 두 번 올라가지 않는다."""
    last = None
    for n in range(1, tries + 1):
        try:
            return threads_post(urls, text)
        except Exception as e:
            last = e
            print(f"[Threads] {n}번째 시도 실패: {str(e)[:200]}")
            if n < tries:
                time.sleep(wait)
    raise last


# ---------------- Instagram ----------------
def ig_base():
    return f"https://{IG_HOST}/{IG_VER}"


def ig_post(urls, caption):
    b = ig_base()
    kids = []
    for u in urls:
        r = call("POST", f"{b}/{IG_USER}/media", {"image_url": u, "is_carousel_item": "true", "access_token": IG_TOKEN})
        kids.append(r["id"])
    for k in kids:
        wait_ready(lambda k=k: call("GET", f"{b}/{k}", {"fields": "status_code", "access_token": IG_TOKEN}).get("status_code"), "인스타 사진")
    c = call("POST", f"{b}/{IG_USER}/media", {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": caption[:2200], "access_token": IG_TOKEN})
    wait_ready(lambda: call("GET", f"{b}/{c['id']}", {"fields": "status_code", "access_token": IG_TOKEN}).get("status_code"), "인스타 묶음")
    pub = call("POST", f"{b}/{IG_USER}/media_publish", {"creation_id": c["id"], "access_token": IG_TOKEN})
    link = call("GET", f"{b}/{pub['id']}", {"fields": "permalink", "access_token": IG_TOKEN}).get("permalink", "")
    return {"id": pub["id"], "permalink": link}


# ---------------- 확인 모드 ----------------
def check():
    ok = True
    if TH_TOKEN:
        try:
            me = call("GET", f"{TH_BASE}/me", {"fields": "id,username", "access_token": TH_TOKEN})
            print(f"[Threads] 연결 OK: @{me.get('username')} (번호 {me.get('id')})")
        except Exception as e:
            ok = False; print(f"[Threads] 실패: {e}")
    else:
        ok = False; print("[Threads] THREADS_TOKEN 이 비어 있어요")
    if IG_TOKEN:
        found = False
        tries = [
            ("graph.instagram.com", "me", {"fields": "user_id,username"}),
            (IG_HOST, f"{IG_USER}" if IG_USER else "me", {"fields": "id,username" if IG_USER else "id,name"}),
            ("graph.facebook.com", "me/accounts", {"fields": "instagram_business_account{id,username}"}),
            (IG_HOST, f"{IG_USER}", {"fields": "username,followers_count,media_count"}),
            (IG_HOST, f"{IG_USER}", {"fields": "account_type"}),
            ("graph.instagram.com", "me", {"fields": "account_type,username"}),
            (IG_HOST, f"{IG_USER}/insights", {"metric": "reach", "period": "day"}),
            ("graph.facebook.com", "debug_token", {"input_token": IG_TOKEN}),
            ("graph.facebook.com", "me/permissions", {}),
        ]
        for host, path, f in tries:
            try:
                r = call("GET", f"https://{host}/{IG_VER}/{path}", dict(f, access_token=IG_TOKEN))
                print(f"[인스타] {host}/{path} 응답: {json.dumps(r, ensure_ascii=False)[:1500]}")
                found = True
            except Exception as e:
                print(f"[인스타] {host}/{path} 실패: {str(e)[:200]}")
        if not IG_USER:
            print("[인스타] IG_USER_ID 가 비어 있어요. 위 응답에 나온 인스타 계정 번호를 넣어 주세요.")
        ok = ok and found
    else:
        ok = False; print("[인스타] IG_TOKEN 이 비어 있어요")
    return ok


# ---------------- 올리기 ----------------
def publish_one(folder, post):
    n = len(post["slides"])
    urls = image_urls(folder, n)
    pubs = post.setdefault("published", {})
    errors = []
    if "instagram" not in pubs and IG_TOKEN and IG_USER:
        try:
            pubs["instagram"] = ig_post(urls, post["caption"])
            pubs["instagram"]["at"] = datetime.datetime.now(KST).isoformat(timespec="minutes")
            print(f"인스타 완료: {pubs['instagram']['permalink']}")
        except Exception as e:
            errors.append(f"인스타: {e}")
    if "threads" not in pubs and TH_TOKEN:
        try:
            pubs["threads"] = threads_post_retry(urls, post.get("threads_text") or post["caption"])
            pubs["threads"]["at"] = datetime.datetime.now(KST).isoformat(timespec="minutes")
            print(f"Threads 완료: {pubs['threads']['permalink']}")
        except Exception as e:
            errors.append(f"Threads: {e}")
    if errors:
        post["errors"] = errors
    else:
        post.pop("errors", None)
        post["status"] = "published"
        ats = [v.get("at") for v in pubs.values() if isinstance(v, dict) and v.get("at")]
        # 그 편이 '처음' 올라간 날을 게시일로 친다 (반쪽만 올라갔다가 다음 날 마저 올려도 그날 새 편이 밀리지 않게)
        post["published_at"] = min(ats) if ats else datetime.datetime.now(KST).isoformat(timespec="minutes")
    with open(os.path.join(folder, "post.json"), "w", encoding="utf-8") as fp:
        json.dump(post, fp, ensure_ascii=False, indent=2)
    return not errors


def due(post, now):
    if post.get("status") != "approved":
        return False
    at = post.get("publish_at")
    if not at:
        return True
    return datetime.datetime.fromisoformat(at) <= now


def published_today(now):
    today = now.date().isoformat()
    for p in glob.glob("content/*/post.json"):
        post = json.load(open(p, encoding="utf-8"))
        if post.get("status") == "published" and str(post.get("published_at", "")).startswith(today):
            return True
    return False


def time_slot_ok(now):
    """매일 오후 5시~6시 사이 '그날의 무작위 분'이 지나면 올린다.
    무작위 분은 날짜로 정해져서 하루 동안은 같은 값. 늦게 깨어난 경우 6시대에 따라잡기."""
    import hashlib
    target = int(hashlib.md5(now.date().isoformat().encode()).hexdigest(), 16) % 56  # 0~55분
    if now.hour == 17:
        print(f"오늘 목표 시각: 17:{target:02d}")
        return now.minute >= target
    return now.hour == 18  # 실행이 늦어졌을 때만


def finish_partial():
    """인스타만(또는 Threads만) 올라가고 나머지가 실패한 편을 마저 올린다."""
    ok = True
    for p in sorted(glob.glob("content/*/post.json")):
        post = json.load(open(p, encoding="utf-8"))
        if post.get("status") == "approved" and post.get("published"):
            folder = os.path.dirname(p)
            print(f"반쪽만 올라간 편 마저 올리기: {folder}")
            ok = publish_one(folder, post) and ok
    return ok


def run(force_folder=None):
    now = datetime.datetime.now(KST)
    ok = True
    if not force_folder:
        ok = finish_partial()
        if published_today(now):
            print("오늘은 이미 한 편 올렸어요."); return True
        if not time_slot_ok(now):
            print("아직 올릴 시간이 아니에요."); return True
    folders = [force_folder] if force_folder else sorted(os.path.dirname(p) for p in glob.glob("content/*/post.json"))
    done = 0
    for folder in folders:
        post = json.load(open(os.path.join(folder, "post.json"), encoding="utf-8"))
        if not force_folder and not due(post, now):
            continue
        if not force_folder and post.get("published"):
            continue  # 반쪽 편은 위에서 처리
        if not os.path.exists(os.path.join(folder, f"slide_{len(post['slides'])}.png")):
            print(f"{folder}: 카드 그림이 없어요"); ok = False; continue
        print(f"올리는 중: {folder}")
        ok = publish_one(folder, post) and ok
        done += 1
        if not force_folder:
            break  # 한 번 실행에 한 편만 (도배 방지)
    if done == 0:
        print("지금 올릴 글이 없어요.")
    return ok


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "check":
        sys.exit(0 if check() else 1)
    elif mode == "now":
        sys.exit(0 if run(sys.argv[2]) else 1)
    else:
        sys.exit(0 if run() else 1)
