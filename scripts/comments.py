"""최근 글의 댓글을 모아서 comments/inbox.json 에 저장한다 (답글은 사람이 확인 후 따로 올림).

python scripts/comments.py
"""
import json, os, datetime
from publish import call, TH_BASE, TH_TOKEN, IG_TOKEN, IG_USER, ig_base

KST = datetime.timezone(datetime.timedelta(hours=9))
out = {"updated": datetime.datetime.now(KST).isoformat(timespec="minutes"), "instagram": [], "threads": []}

if IG_TOKEN and IG_USER:
    try:
        r = call("GET", f"{ig_base()}/{IG_USER}/media", {"fields": "id,caption,permalink,timestamp,comments{id,text,username,timestamp}", "limit": "10", "access_token": IG_TOKEN})
        for m in r.get("data", []):
            for c in (m.get("comments") or {}).get("data", []):
                out["instagram"].append({"post": m.get("permalink"), "id": c["id"], "user": c.get("username"), "text": c.get("text"), "time": c.get("timestamp")})
    except Exception as e:
        out["instagram_error"] = str(e)[:300]

if TH_TOKEN:
    try:
        r = call("GET", f"{TH_BASE}/me/threads", {"fields": "id,permalink,timestamp", "limit": "10", "access_token": TH_TOKEN})
        for t in r.get("data", []):
            rep = call("GET", f"{TH_BASE}/{t['id']}/replies", {"fields": "id,text,username,timestamp", "access_token": TH_TOKEN})
            for c in rep.get("data", []):
                out["threads"].append({"post": t.get("permalink"), "id": c["id"], "user": c.get("username"), "text": c.get("text"), "time": c.get("timestamp")})
    except Exception as e:
        out["threads_error"] = str(e)[:300]

os.makedirs("comments", exist_ok=True)
with open("comments/inbox.json", "w", encoding="utf-8") as fp:
    json.dump(out, fp, ensure_ascii=False, indent=2)
print(f"댓글 모음: 인스타 {len(out['instagram'])}개, Threads {len(out['threads'])}개")
