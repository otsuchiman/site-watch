#!/usr/bin/env python3
"""サイトの新着を検知して LINE (Messaging API) に通知する。"""
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urldefrag, urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from sites import SITES

STATE_FILE = "state.json"
MAX_PER_SITE = 5                                            # 1サイトあたり通知に載せる最大件数
MONTHLY_LIMIT = int(os.environ.get("MONTHLY_LIMIT", "190"))  # 無料枠200通の手前で止める
MAX_SEEN = 20000
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; personal-site-watch/1.0)"}
JST = timezone(timedelta(hours=9))


def log(*args):
    print(*args, flush=True)


def as_list(v):
    return v if isinstance(v, list) else [v]


def clean(text):
    return " ".join((text or "").split())


def http_get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r


# ---------- 取得方法ごとの処理 ----------
def fetch_rss(src):
    items = {}
    for u in as_list(src["url"]):
        feed = feedparser.parse(http_get(u).content)
        for e in feed.entries:
            link = e.get("link")
            if link:
                items.setdefault(link, clean(e.get("title", "")))
    return list(items.items())


def fetch_html(src):
    items = {}
    pat = re.compile(src["pattern"])
    for u in as_list(src["url"]):
        soup = BeautifulSoup(http_get(u).content, "html.parser")
        for a in soup.find_all("a", href=True):
            url = urldefrag(urljoin(u, a["href"]))[0]
            if not pat.search(url):
                continue
            text = clean(a.get_text(" ")) or clean(a.get("title", ""))
            if url not in items or (not items[url] and text):
                items[url] = text
        time.sleep(1)
    return list(items.items())


SKIP_SUB = re.compile(r"taxonom|users|author|categor|tag", re.I)


def fetch_sitemap(src):
    def locs(url):
        text = http_get(url).content.decode("utf-8", "ignore")
        return [html.unescape(x) for x in re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.S)]

    exclude = [re.compile(p) for p in src.get("exclude", [])]
    top = locs(src["url"])
    subs = [u for u in top if u.endswith(".xml")]
    pages = []
    if subs:
        for s in subs[:30]:
            if SKIP_SUB.search(s):
                continue
            pages += [u for u in locs(s) if not u.endswith(".xml")]
            time.sleep(1)
    else:
        pages = top
    out = {}
    for u in pages:
        if not any(p.search(u) for p in exclude):
            out[u] = ""
    items = list(out.items())
    items.reverse()  # サイトマップは古い順なので新しい順にする
    return items


FETCHERS = {"rss": fetch_rss, "html": fetch_html, "sitemap": fetch_sitemap}


def fetch_site(site):
    """上から順に試して、最初に結果が取れた方法を使う。"""
    for src in site["sources"]:
        try:
            items = FETCHERS[src["type"]](src)
            if items:
                log(f"  [{site['name']}] {src['type']} で {len(items)} 件取得")
                return items
            log(f"  [{site['name']}] {src['type']} は0件 → 次の方法へ")
        except Exception as e:  # noqa: BLE001
            log(f"  [{site['name']}] {src['type']} 失敗: {e}")
    return None


def page_title(url):
    try:
        soup = BeautifulSoup(http_get(url).content, "html.parser")
        return clean(soup.title.get_text()) if soup.title else ""
    except Exception:  # noqa: BLE001
        return ""


# ---------- 状態の保存 ----------
def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


# ---------- LINE ----------
def line_push(token, user_id, text):
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"to": user_id, "messages": [{"type": "text", "text": text[:5000]}]},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"LINE送信エラー {r.status_code}: {r.text}")


def chunk_blocks(blocks, limit=4500):
    chunks, cur = [], ""
    for b in blocks:
        if cur and len(cur) + len(b) + 2 > limit:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n\n{b}" if cur else b
    if cur:
        chunks.append(cur)
    return chunks


def main():
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token or not user_id:
        log("LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が設定されていません")
        sys.exit(1)

    state = load_state()
    sites_state = state.setdefault("sites", {})
    month = datetime.now(JST).strftime("%Y-%m")
    quota = state.setdefault("quota", {"month": month, "sent": 0})
    if quota["month"] != month:
        quota.update(month=month, sent=0)

    exit_code = 0
    try:
        baselined, blocks, pending = [], [], []
        for site in SITES:
            name = site["name"]
            items = fetch_site(site)
            time.sleep(2)
            if not items:
                log(f"  [{name}] 取得できませんでした（今回はスキップ）")
                continue

            urls = [u for u, _ in items]
            if name not in sites_state:
                # 初めて見るサイト: 今あるものは「既読」として登録し通知しない
                sites_state[name] = {"seen": urls[:MAX_SEEN]}
                baselined.append(name)
                continue

            seen = set(sites_state[name]["seen"])
            new = [(u, t) for u, t in items if u not in seen]
            if not new:
                continue

            lines = [f"【{name}】新着 {len(new)}件"]
            for u, t in new[:MAX_PER_SITE]:
                title = t or page_title(u) or unquote(u.rstrip("/").split("/")[-1])
                lines.append(f"・{title[:60]}\n{u}")
            if len(new) > MAX_PER_SITE:
                lines.append(f"…ほか {len(new) - MAX_PER_SITE} 件")
            blocks.append("\n".join(lines))
            pending.append((name, [u for u, _ in new]))
            log(f"  [{name}] 新着 {len(new)} 件")

        if baselined:
            blocks.insert(0, "✅ 監視を開始しました\n" + "\n".join(f"・{n}" for n in baselined))

        if blocks:
            chunks = chunk_blocks(blocks)
            if quota["sent"] + len(chunks) > MONTHLY_LIMIT:
                log(f"今月の送信数が上限({MONTHLY_LIMIT})に達したため送信を見送ります（来月まとめて通知）")
            else:
                for c in chunks:
                    line_push(token, user_id, c)
                    quota["sent"] += 1
                for name, new_urls in pending:
                    sites_state[name]["seen"] = (new_urls + sites_state[name]["seen"])[:MAX_SEEN]
                log(f"LINEに {len(chunks)} 通送信（今月 {quota['sent']} 通目）")
        else:
            log("新着なし")
    except Exception as e:  # noqa: BLE001
        log(f"エラー: {e}")
        exit_code = 1
    finally:
        save_state(state)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
