#!/usr/bin/env python3
"""
Instagram → HACO+ Journal sync
------------------------------
@hacohairnailstokyo の投稿のうち、キャプションに #hacojournal が付いたものだけを
取得し、_journal/ に記事ファイル（Markdown）を作ります。画像は assets/journal/ に保存。

GitHub Actions（.github/workflows/instagram-journal.yml）から毎日実行され、
新しい記事があれば「プルリクエスト」が作られます。内容を確認してマージ＝公開です。

必要なシークレット（GitHub → Settings → Secrets and variables → Actions）
  IG_ACCESS_TOKEN         @hacohairnailstokyo の長期アクセストークン（必須）
  IG_ACCESS_TOKEN_LONDON  @hacohairsalon（ロンドン）の長期アクセストークン（任意。無ければ東京のみ）
  ANTHROPIC_API_KEY  キャプションを記事文に整える（任意。無ければキャプションをそのまま使用）
  GH_PAT             トークンの自動延長を保存するため（任意。無いと60日ごとに再発行が必要）
"""
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_journal import CATEGORIES, CATEGORY_ALIASES, STAFF  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "_journal"
ASSETS = ROOT / "assets" / "journal"
TAG = os.environ.get("JOURNAL_TAG", "hacojournal").lstrip("#").lower()
# 取り込むアカウント（シークレット名, 表示名）。トークンが未登録のアカウントは飛ばします
ACCOUNTS = [("IG_ACCESS_TOKEN", "Tokyo"), ("IG_ACCESS_TOKEN_LONDON", "London")]
TOKEN = ""
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
GRAPH = "https://graph.instagram.com"


def get(url, params=None):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as ex:  # Instagram のエラー内容をログに出す（トークンは出さない）
        detail = ex.read().decode(errors="replace")[:400]
        raise RuntimeError(f"HTTP {ex.code}: {detail}") from None


def refresh_token(secret_name):
    """長期トークンを延長（60日）。GH_PAT があればシークレットも更新。"""
    global TOKEN
    try:
        res = get(f"{GRAPH}/refresh_access_token", {"grant_type": "ig_refresh_token", "access_token": TOKEN})
    except Exception as ex:  # 24時間以内に発行されたトークンなどは延長できない
        print(f"token refresh skipped: {ex}")
        return
    new = res.get("access_token")
    days = int(res.get("expires_in", 0)) // 86400
    print(f"token refreshed, valid for ~{days} days")
    if new and new != TOKEN and os.environ.get("GH_PAT") and os.environ.get("GITHUB_REPOSITORY"):
        subprocess.run(["gh", "secret", "set", secret_name, "--repo", os.environ["GITHUB_REPOSITORY"], "--body", new],
                       check=False, env={**os.environ, "GH_TOKEN": os.environ["GH_PAT"]})
    if new:
        TOKEN = new


def fetch_media(limit=1000):
    fields = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,children{media_type,media_url,thumbnail_url}"
    url = f"{GRAPH}/me/media"
    params = {"fields": fields, "limit": 50, "access_token": TOKEN}
    items = []
    while url and len(items) < limit:
        data = get(url, params)
        items += data.get("data", [])
        url = data.get("paging", {}).get("next")
        params = None
    return items


def existing_ids():
    ids = set()
    for f in POSTS.glob("*.md"):
        m = re.search(r"^instagram_id:\s*\"?(\d+)", f.read_text(encoding="utf-8"), re.M)
        if m:
            ids.add(m.group(1))
    return ids


def has_tag(caption):
    tags = {t.lower() for t in re.findall(r"#([\w぀-ヿ一-鿿]+)", caption or "")}
    return TAG in tags


def image_urls(m):
    out = []
    if m["media_type"] == "CAROUSEL_ALBUM":
        for c in m.get("children", {}).get("data", []):
            u = c.get("media_url") if c.get("media_type") == "IMAGE" else c.get("thumbnail_url")
            if u:
                out.append(u)
    else:
        u = m.get("media_url") if m["media_type"] == "IMAGE" else m.get("thumbnail_url")
        if u:
            out.append(u)
    return out[:8]


def save_image(url, path):
    with urllib.request.urlopen(url, timeout=60) as r:
        im = Image.open(io.BytesIO(r.read())).convert("RGB")
    if im.width > 1600:
        im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=84, optimize=True, progressive=True)


def clean_caption(c):
    c = re.sub(r"(?:^|\s)#[^\s#]+", "", c or "")
    return re.sub(r"\n{3,}", "\n\n", c).strip()


def find_staff(text):
    found = []
    for name in STAFF:
        if re.search(rf"(?<![A-Za-z]){name}(?![A-Za-z])", text, re.I) and name not in found:
            found.append(name)
    return found


SYSTEM = f"""あなたは東京・表参道の美容室 HACO+ のWebサイト「Journal」の編集者です。
Instagramのキャプションから、サイト用の記事を日本語と英語で作ります。

目的：(1) 雑誌・広告・ショー・講師などの外部の仕事の依頼につなげる (2) 美容学生・新卒が「ここで働きたい」と思える見せ方。

厳守：
- キャプションに書かれていない事実（日付、媒体名、人数、場所、役割、受賞歴など）を絶対に作らない。わからないことは書かない。
- 誇張表現・絵文字・ハッシュタグは使わない。落ち着いた、ファッション誌のクレジットのような文体。
- 本文は2〜4段落。誰が・何を・どこで担当したかを最初に書く。
- category は次から1つ：{", ".join(CATEGORIES)}（雑誌表紙・誌面・インタビュー=EDITORIAL、広告・ブランド・商品撮影=CAMPAIGN、ファッションウィーク・ショー・イベント・セミナー講師・海外出張=SHOW、受賞・その他のお知らせ=NEWS）
- staff はこの名前リストに含まれる人だけ：{", ".join(STAFF)}
- credits は「役割: 名前」の形（例「ヘア: Wataro」）。キャプションに無ければ空配列。
- slug は英小文字とハイフンのみ、40文字以内。

JSONだけを返す：{{"title":"","title_en":"","slug":"","category":"","staff":[],"credits":[],"summary":"","summary_en":"","body_ja":"","body_en":""}}"""


def draft_with_claude(caption, date):
    body = json.dumps({
        "model": MODEL, "max_tokens": 2000, "system": SYSTEM,
        "messages": [{"role": "user", "content": f"投稿日: {date}\n\nキャプション:\n{caption}"}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        text = json.loads(r.read().decode())["content"][0]["text"]
    return json.loads(re.search(r"\{.*\}", text, re.S).group(0))


def draft_plain(caption, date):
    text = clean_caption(caption)
    first = next((l for l in text.splitlines() if l.strip()), "Journal")
    return {"title": first[:60], "title_en": "", "slug": "", "category": "NEWS", "staff": find_staff(text),
            "credits": [], "summary": first[:120], "summary_en": "", "body_ja": text, "body_en": ""}


def q(s):
    return json.dumps(s or "", ensure_ascii=False)


def main():
    global TOKEN
    seen = existing_ids()
    new, errors = [], []
    for secret_name, label in ACCOUNTS:
        TOKEN = os.environ.get(secret_name, "").strip()
        if not TOKEN:
            print(f"[{label}] {secret_name} が未設定のためスキップします")
            continue
        refresh_token(secret_name)
        try:
            items = [m for m in fetch_media() if has_tag(m.get("caption")) and m["id"] not in seen]
        except Exception as ex:
            print(f"[{label}] 投稿の取得に失敗しました: {ex}")
            errors.append(label)
            continue
        print(f"[{label}] {len(items)} new #{TAG} post(s)")
        for m in items:
            seen.add(m["id"])
        new += items
    report = []
    for m in sorted(new, key=lambda x: x["timestamp"]):
        d = datetime.strptime(m["timestamp"][:10], "%Y-%m-%d").date()
        try:
            a = draft_with_claude(m["caption"], d) if ANTHROPIC_KEY else draft_plain(m["caption"], d)
        except Exception as ex:
            print(f"AI draft failed ({ex}); using caption as-is")
            a = draft_plain(m["caption"], d)
        slug = re.sub(r"[^a-z0-9-]+", "-", (a.get("slug") or f"ig-{m['id'][-8:]}").lower()).strip("-")[:40] or f"ig-{m['id'][-8:]}"
        if list(POSTS.glob(f"*-{slug}.md")):
            slug = f"{slug}-{m['id'][-4:]}"
        imgs = []
        for i, u in enumerate(image_urls(m)):
            p = ASSETS / f"{slug}{'' if i == 0 else f'-{i+1}'}.jpg"
            try:
                save_image(u, p)
                imgs.append(f"/assets/journal/{p.name}")
            except Exception as ex:
                print(f"image failed: {ex}")
        cat = str(a.get("category", "NEWS")).upper()
        cat = CATEGORY_ALIASES.get(cat, cat)
        if cat not in CATEGORIES:
            cat = "NEWS"
        staff = [s for s in (a.get("staff") or []) if s in STAFF]
        fm = [
            f"title: {q(a.get('title'))}", f"title_en: {q(a.get('title_en'))}", f"date: {d}", f"category: {cat}",
            f"cover: {imgs[0] if imgs else ''}", f"images: {json.dumps(imgs[1:])}",
            f"staff: {json.dumps(staff, ensure_ascii=False)}", f"credits: {json.dumps(a.get('credits') or [], ensure_ascii=False)}",
            f"summary: {q(a.get('summary'))}", f"summary_en: {q(a.get('summary_en'))}",
            f"instagram: {q(m.get('permalink'))}", f'instagram_id: "{m["id"]}"', "status: published",
        ]
        body = (a.get("body_ja") or "").strip()
        if a.get("body_en"):
            body += "\n\n<!-- en -->\n\n" + a["body_en"].strip()
        f = POSTS / f"{d}-{slug}.md"
        f.write_text("---\n" + "\n".join(fm) + "\n---\n\n" + body + "\n", encoding="utf-8")
        report.append(f"- **{a.get('title')}**（{cat}）— `_journal/{f.name}` / [Instagram]({m.get('permalink')})")
        print(f"wrote {f.name}")
    Path(os.environ.get("REPORT_FILE", "journal-sync-report.md")).write_text(
        "\n".join(report) if report else "", encoding="utf-8")
    if errors and not report:
        sys.exit(f"取得に失敗したアカウント: {', '.join(errors)}（トークンの再発行が必要かもしれません）")


if __name__ == "__main__":
    main()
