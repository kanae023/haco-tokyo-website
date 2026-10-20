#!/usr/bin/env python3
"""
HACO+ Journal builder
---------------------
_journal/*.md  →  journal/index.html, journal/<slug>/index.html,
                        journal/feed.json, journal/sitemap-journal.xml

記事ファイルの形式（_journal/YYYY-MM-DD-slug.md）:

---
title: "日本語タイトル"
title_en: "English title"
date: 2026-10-20
category: EDITORIAL        # EDITORIAL / SHOW / CAMPAIGN / INTERVIEW / EDUCATION / GLOBAL / EVENT / PRODUCT / NEWS
cover: /assets/journal/slug.jpg
images: []                 # 追加画像（任意）
staff: ["Wataro"]          # STAFF に登録された名前ならスタッフカードを表示
credits: ["ヘア: Wataro"]
summary: "一覧・検索結果に出る説明（日本語）"
summary_en: "English summary"
instagram: "https://www.instagram.com/p/..."   # 任意
link: "https://..."        # 任意（外部リンク）
link_label: "リンク名"
status: published          # draft にすると公開されません
---

日本語本文（Markdown）

<!-- en -->

English body (Markdown)

使い方:  python3 scripts/build_journal.py
"""
import html
import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

import markdown
import yaml

# ======================================================================
# 設定 — ここを書き換えればサイト全体に反映されます
# ======================================================================
SITE_URL = "https://hacoplus.jp"
WORK_EMAIL = "s@hacohairsalon.com"   # 撮影・講師・ヘアメイク依頼の窓口
RECRUIT_URL = "/careers/"  # 採用ページ
INSTAGRAM_URL = "https://www.instagram.com/hacohairnailstokyo/"
GA_ID = "G-HB3T4GK5S1"

CATEGORIES = {
    "EDITORIAL": ("Editorial", "誌面・撮影"),
    "SHOW": ("Show / Fashion Week", "ショー・ファッションウィーク"),
    "CAMPAIGN": ("Campaign", "広告・キャンペーン"),
    "INTERVIEW": ("Interview", "インタビュー"),
    "EDUCATION": ("Education", "講師・ワークショップ"),
    "GLOBAL": ("Global", "海外の仕事"),
    "EVENT": ("Event", "イベント"),
    "PRODUCT": ("Product", "プロダクト"),
    "NEWS": ("News", "お知らせ"),
}

# スタッフ情報：記事の staff に名前を入れると、写真・肩書き・予約リンクが出ます
STAFF = {
    "Teiji":  {"role": "Founder / Hair & Make-up", "role_ja": "代表 / ヘアメイク", "photo": None, "url": None},
    "Wataro": {"role": "Art Director", "role_ja": "アートディレクター", "photo": "/assets/staff/wataro.jpg", "url": "https://www.instagram.com/wataro0821/", "booking": "https://stekina.com/reserve/UCFV-UA5F/menu"},
    "Rena":   {"role": "Senior Stylist", "role_ja": "シニアスタイリスト", "photo": "/assets/staff/rena.jpg", "url": "/stylists/#rena", "booking": "https://stekina.com/reserve/T8E4-HZY4/menu"},
    "Leo":    {"role": "Top Stylist", "role_ja": "トップスタイリスト", "photo": "/assets/staff/leo.jpg", "url": "/stylists/#leo", "booking": "https://stekina.com/reserve/STE8-LMNS/menu"},
    "Makoto": {"role": "Top Stylist", "role_ja": "トップスタイリスト", "photo": "/assets/staff/makoto.jpg", "url": "/stylists/#makoto", "booking": "https://stekina.com/reserve/8BNH-7AYM/menu"},
    "Ibuki":  {"role": "Top Stylist", "role_ja": "トップスタイリスト", "photo": "/assets/staff/ibuki.jpg", "url": "/stylists/#ibuki", "booking": "https://stekina.com/reserve/5BJH-7AZD/menu"},
    "Joi":    {"role": "Top Stylist", "role_ja": "トップスタイリスト", "photo": "/assets/staff/joi.jpg", "url": "/stylists/#joi", "booking": "https://stekina.com/reserve/FQ4Z-52GM/menu"},
    "Nova":   {"role": "Stylist", "role_ja": "スタイリスト", "photo": "/assets/staff/nova.jpg", "url": "/stylists/#nova", "booking": "https://stekina.com/reserve/6FKL-A2J8/menu"},
    "Shiho":  {"role": "Stylist", "role_ja": "スタイリスト", "photo": "/assets/staff/shiho.jpg", "url": "https://www.instagram.com/siehoh/", "booking": "https://stekina.com/reserve/7XML-A2KU/menu"},
    "Miina":  {"role": "Jr Stylist", "role_ja": "ジュニアスタイリスト", "photo": "/assets/staff/miina.jpg", "url": "/stylists/#miina", "booking": "https://stekina.com/reserve/QGBZ-7ATZ/menu"},
    "Moe":    {"role": "Assistant", "role_ja": "アシスタント", "photo": "/assets/staff/moe.jpg", "url": "https://www.instagram.com/mimg__e/"},
    "Yaya":   {"role": "Assistant", "role_ja": "アシスタント", "photo": "/assets/staff/yaya.jpg", "url": "https://www.instagram.com/xx_888y/"},
    "Kaito":  {"role": "Assistant", "role_ja": "アシスタント", "photo": "/assets/staff/kaito.jpg", "url": "https://www.instagram.com/ohnishi_kaito/"},
    "Shun":   {"role": "Stylist, HACO London", "role_ja": "スタイリスト（ロンドン店）", "photo": None, "url": None},
}

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "_journal"   # 先頭に _ が付くフォルダはGitHub Pagesで公開されません
OUT_DIR = ROOT / "journal"

e = lambda s: html.escape(str(s or ""), quote=True)


# ======================================================================
# Parsing
# ======================================================================
def load_posts():
    posts = []
    for f in sorted(POSTS_DIR.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
        if not m:
            print(f"skip (no front matter): {f.name}", file=sys.stderr)
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        if str(meta.get("status", "published")).lower() != "published":
            continue
        body = m.group(2)
        parts = re.split(r"^\s*<!--\s*en\s*-->\s*$", body, maxsplit=1, flags=re.M)
        md = lambda t: markdown.markdown(t.strip(), extensions=["extra", "sane_lists"])
        slug = meta.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", f.stem)
        d = meta.get("date")
        if isinstance(d, str):
            d = datetime.strptime(d, "%Y-%m-%d").date()
        posts.append({
            **meta,
            "slug": slug,
            "date": d,
            "category": str(meta.get("category", "NEWS")).upper(),
            "staff": meta.get("staff") or [],
            "credits": meta.get("credits") or [],
            "images": meta.get("images") or [],
            "body_ja": md(parts[0]),
            "body_en": md(parts[1]) if len(parts) > 1 else "",
        })
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


# ======================================================================
# Shared chrome (matches hacoplus.jp)
# ======================================================================
CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--black:#0a0a0a;--g700:#4a4a4a;--g500:#888;--g300:#c4c4c4;--g100:#ececec;--white:#fff;
--sans:'Barlow','Zen Kaku Gothic New',-apple-system,BlinkMacSystemFont,sans-serif;
--t:0.8125rem;--ts:0.75rem;--txs:0.6875rem;--pad:2.5rem;--max:1600px;--nav:72px;--ease:cubic-bezier(0.16,1,0.3,1)}
html{-webkit-font-smoothing:antialiased;scroll-behavior:smooth}
body{font-family:var(--sans);font-weight:500;color:var(--black);background:var(--white);font-size:var(--t);line-height:1.7;letter-spacing:.01em;overflow-x:hidden}
html:not([data-lang]) .en,html[data-lang="jp"] .en{display:none!important}
html[data-lang="en"] .jp{display:none!important}
a{color:inherit;text-decoration:none;transition:opacity .3s var(--ease)}
a:hover{opacity:.5}
img{max-width:100%;height:auto;display:block}
button{font:inherit;background:none;border:none;cursor:pointer;color:inherit}
/* nav */
.nav{position:fixed;inset:0 0 auto 0;height:var(--nav);z-index:100;display:flex;align-items:center;justify-content:space-between;padding:0 var(--pad);background:rgba(255,255,255,.95);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--g100)}
.nav-logo img{height:40px;width:auto}
.nav-menu{display:flex;gap:2rem;list-style:none}
.nav-menu a.current{text-decoration:underline;text-underline-offset:4px}
.nav-right{display:flex;gap:1.5rem;align-items:center}
.lang-option{color:var(--g300)}.lang-option.active{color:var(--black)}.lang-sep{color:var(--g300);margin:0 .25rem}
.nav-toggle{display:none;width:24px;height:16px;position:relative}
.nav-toggle span{position:absolute;left:0;right:0;height:1px;background:var(--black);transition:transform .3s var(--ease),opacity .3s}
.nav-toggle span:nth-child(1){top:0}.nav-toggle span:nth-child(2){top:7px}.nav-toggle span:nth-child(3){top:14px}
.nav-toggle.is-open span:nth-child(1){transform:translateY(7px) rotate(45deg)}.nav-toggle.is-open span:nth-child(2){opacity:0}.nav-toggle.is-open span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
.mobile-menu{position:fixed;inset:var(--nav) 0 0 0;background:var(--white);z-index:99;display:none;flex-direction:column;padding:2rem var(--pad);gap:1.25rem;font-size:1.5rem}
.mobile-menu.is-open{display:flex}
@media(max-width:768px){:root{--pad:1rem;--nav:60px}.nav-menu,.nav-right .nav-book{display:none}.nav-toggle{display:block}.nav-logo img{height:32px}}
/* layout */
main{padding-top:var(--nav)}
.section{padding:5rem var(--pad);max-width:var(--max);margin:0 auto}
.section-inner{display:grid;grid-template-columns:160px 1fr;gap:3rem;align-items:start}
.label{font-size:var(--t);font-weight:500}
.muted{color:var(--g500)}
.upper{text-transform:uppercase;letter-spacing:.06em;font-size:var(--txs)}
@media(max-width:768px){.section{padding:3rem var(--pad)}.section-inner{grid-template-columns:1fr;gap:1.25rem}}
/* index */
.intro{max-width:70ch;margin-bottom:2.5rem}
.intro .jp{display:block}
.filters{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:2.5rem}
.filters button{border:1px solid var(--g100);padding:.35rem .8rem;font-size:var(--txs);letter-spacing:.06em;text-transform:uppercase;transition:all .2s}
.filters button.active,.filters button:hover{background:var(--black);color:var(--white);border-color:var(--black)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:3rem 1.5rem}
.card-media{aspect-ratio:4/5;overflow:hidden;background:var(--g100);margin-bottom:.9rem}
.card-media img{width:100%;height:100%;object-fit:cover;transition:transform .8s var(--ease)}
.card:hover{opacity:1}.card:hover .card-media img{transform:scale(1.03)}
.meta-row time{white-space:nowrap}
.meta-row{display:flex;justify-content:space-between;gap:1rem;color:var(--g500);font-size:var(--txs);letter-spacing:.06em;text-transform:uppercase;margin-bottom:.35rem}
.card-title{font-size:var(--t);line-height:1.55}
.card[hidden]{display:none}
@media(max-width:768px){.grid{grid-template-columns:1fr 1fr;gap:2rem .75rem}}
/* article */
.crumb{font-size:var(--txs);letter-spacing:.06em;text-transform:uppercase;color:var(--g500);margin-bottom:2rem}
.article-head{max-width:46rem;margin-bottom:2.5rem}
.article-title{font-size:clamp(1.4rem,3vw,2.2rem);line-height:1.3;font-weight:500;margin:.6rem 0 1rem;letter-spacing:0}
.lede{font-size:.95rem;color:var(--g700);max-width:42rem}
.article-grid{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:4rem;align-items:start}
.article-cover img{width:100%;background:var(--g100)}
.article-images{display:grid;gap:1rem;margin-top:1rem}
.article-body{font-size:.875rem;line-height:1.95;max-width:40rem}
.article-body p+p,.article-body ul,.article-body h2,.article-body h3{margin-top:1.25rem}
.article-body h2{font-size:var(--t);text-transform:uppercase;letter-spacing:.06em;margin-top:2.25rem}
.article-body ul{padding-left:1.1rem}
.article-body a{text-decoration:underline;text-underline-offset:3px}
.block{border-top:1px solid var(--black);padding-top:1rem;margin-top:2.5rem}
.block h3{font-size:var(--txs);letter-spacing:.06em;text-transform:uppercase;font-weight:500;margin-bottom:.75rem}
.credits li{list-style:none}
.staff-card{display:flex;gap:1rem;align-items:center;margin-top:.75rem}
.staff-card img,.staff-ph{width:64px;height:80px;object-fit:cover;background:var(--g100);flex:none;display:flex;align-items:center;justify-content:center;font-size:1.2rem;color:var(--g500)}
.staff-links{display:flex;gap:1rem;margin-top:.25rem;font-size:var(--txs);letter-spacing:.06em;text-transform:uppercase}
.staff-links a{text-decoration:underline;text-underline-offset:3px}
.ext{display:inline-block;margin-top:1rem;text-decoration:underline;text-underline-offset:3px}
@media(max-width:900px){.article-grid{grid-template-columns:1fr;gap:2rem}}
/* CTA */
.cta{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--g100)}
.cta a{display:block;padding:3rem var(--pad);transition:background .3s var(--ease),color .3s var(--ease)}
.cta a+a{border-left:1px solid var(--g100)}
.cta a:hover{opacity:1;background:var(--black);color:var(--white)}
.cta-k{font-size:var(--txs);letter-spacing:.06em;text-transform:uppercase;color:var(--g500);display:block;margin-bottom:.75rem}
.cta-h{font-size:clamp(1.1rem,2.2vw,1.6rem);line-height:1.35;display:block}
.cta-p{display:block;margin-top:.75rem;color:var(--g500);max-width:36ch}
@media(max-width:768px){.cta{grid-template-columns:1fr}.cta a+a{border-left:none;border-top:1px solid var(--g100)}.cta a{padding:2rem var(--pad)}}
/* footer */
.footer{border-top:1px solid var(--g100);padding:2rem var(--pad);display:flex;justify-content:space-between;flex-wrap:wrap;gap:1rem;font-size:var(--txs);color:var(--g500)}
.footer div{display:flex;gap:1.5rem;flex-wrap:wrap}
"""

JS = """
(function(){
  var root=document.documentElement;
  function set(l){root.setAttribute('data-lang',l);
    document.querySelectorAll('.lang-option').forEach(function(o){o.classList.toggle('active',o.dataset.lang===l)});
    try{localStorage.setItem('haco-lang',l)}catch(e){}}
  var saved='jp';try{saved=localStorage.getItem('haco-lang')||'jp'}catch(e){}
  set(saved);
  document.querySelectorAll('.lang-option').forEach(function(o){o.addEventListener('click',function(ev){ev.stopPropagation();set(o.dataset.lang)})});
  var t=document.getElementById('nav-toggle'),m=document.getElementById('mobile-menu');
  if(t&&m){t.addEventListener('click',function(){t.classList.toggle('is-open');m.classList.toggle('is-open')})}
  var fb=document.querySelectorAll('.filters button');
  fb.forEach(function(b){b.addEventListener('click',function(){
    fb.forEach(function(x){x.classList.toggle('active',x===b)});
    var c=b.dataset.cat;
    document.querySelectorAll('.card').forEach(function(card){card.hidden=!(c==='ALL'||card.dataset.cat===c)});
  })});
  document.addEventListener('click',function(ev){
    var a=ev.target.closest&&ev.target.closest('a[data-ev]'); if(!a||typeof gtag!=='function')return;
    gtag('event',a.dataset.ev,{link_url:a.href,page:location.pathname,transport_type:'beacon'});
  },true);
})();
"""


def head(title, desc, url, image, extra=""):
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="HACO+ Tokyo">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(image)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0a0a0a">
<link rel="icon" href="/assets/logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;700&family=Zen+Kaku+Gothic+New:wght@400;500&display=swap" rel="stylesheet">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>
<link rel="alternate" type="application/json" href="/journal/feed.json">
{extra}
<style>{CSS}</style>
</head>
<body>
<nav class="nav" id="nav">
  <a href="/index.html" class="nav-logo"><img src="/assets/logo.png" alt="HACO+" width="120" height="40"></a>
  <ul class="nav-menu">
    <li><a href="/index.html">Hair</a></li>
    <li><a href="/nails.html">Nail</a></li>
    <li><a href="/journal/" class="current">Journal</a></li>
    <li><a href="https://www.hacomanagement.com" target="_blank" rel="noopener">Management</a></li>
  </ul>
  <div class="nav-right">
    <a class="nav-book" href="/index.html#booking">Book</a>
    <button class="lang-toggle" aria-label="Toggle language"><span class="lang-option active" data-lang="jp">JP</span><span class="lang-sep">/</span><span class="lang-option" data-lang="en">EN</span></button>
    <button class="nav-toggle" id="nav-toggle" aria-label="Menu"><span></span><span></span><span></span></button>
  </div>
</nav>
<div class="mobile-menu" id="mobile-menu">
  <a href="/index.html">Hair</a><a href="/nails.html">Nail</a><a href="/journal/">Journal</a>
  <a href="https://www.hacomanagement.com" target="_blank" rel="noopener">Management</a><a href="/index.html#booking">Book</a>
</div>
<main>
"""


def cta():
    return f"""
<section class="cta">
  <a href="mailto:{WORK_EMAIL}?subject=Work%20enquiry%20%2F%20%E3%81%8A%E4%BB%95%E4%BA%8B%E3%81%AE%E3%81%94%E4%BE%9D%E9%A0%BC" data-ev="work_enquiry_click">
    <span class="cta-k">Work with us</span>
    <span class="cta-h jp">撮影・ショー・講師のご依頼</span><span class="cta-h en">Shoots, shows &amp; education</span>
    <span class="cta-p jp">エディトリアル、広告、ファッションショーのヘアメイク、セミナー講師やワークショップのご依頼はこちらから。</span>
    <span class="cta-p en">Hair and make-up for editorial, campaigns and shows, plus seminars and workshops. Get in touch.</span>
  </a>
  <a href="{e(RECRUIT_URL)}" data-ev="recruit_click">
    <span class="cta-k">Join HACO+</span>
    <span class="cta-h jp">東京とロンドンで、<br>一緒に表現を広げる仲間を募集しています</span><span class="cta-h en">Grow your craft between<br>Tokyo and London</span>
    <span class="cta-p jp">ロンドン研修制度あり。採用情報を見る →</span>
    <span class="cta-p en">London training programme available. See careers →</span>
  </a>
</section>"""


def foot():
    return f"""
</main>
<footer class="footer">
  <span>© {date.today().year} HACO Group Co Ltd.</span>
  <div><a href="{e(INSTAGRAM_URL)}" target="_blank" rel="noopener">Instagram</a><a href="{e(RECRUIT_URL)}">Recruit</a><a href="/privacy.html">Privacy</a><a href="mailto:{WORK_EMAIL}">Contact</a></div>
</footer>
<script>{JS}</script>
</body>
</html>
"""


def bi(ja, en, tag="span"):
    """bilingual pair"""
    if not en or en == ja:
        return f"<{tag}>{e(ja)}</{tag}>"
    return f'<{tag} class="jp">{e(ja)}</{tag}><{tag} class="en">{e(en)}</{tag}>'


def cat_label(c):
    en, ja = CATEGORIES.get(c, (c.title(), c))
    return f'<span class="jp">{e(ja)}</span><span class="en">{e(en)}</span>'


# ======================================================================
# Pages
# ======================================================================
def build_index(posts):
    used = [c for c in CATEGORIES if any(p["category"] == c for p in posts)]
    chips = '<button class="active" data-cat="ALL">All</button>' + "".join(
        f'<button data-cat="{c}">{e(CATEGORIES[c][0])}</button>' for c in used)
    cards = []
    for p in posts:
        cards.append(f"""
      <a class="card" href="/journal/{p['slug']}/" data-cat="{p['category']}">
        <div class="card-media"><img src="{e(p.get('cover'))}" alt="{e(p.get('title'))}" loading="lazy" decoding="async"></div>
        <div class="meta-row"><span>{cat_label(p['category'])}</span><time datetime="{p['date']}">{p['date'].strftime('%Y.%m.%d')}</time></div>
        <div class="card-title">{bi(p.get('title'), p.get('title_en'))}</div>
      </a>""")
    desc = "HACO+（表参道・渋谷）のジャーナル。ファッションウィーク、雑誌・広告のヘアメイク、セミナー講師、海外での仕事など、スタッフの活動をお届けします。"
    ld = {"@context": "https://schema.org", "@type": "Blog", "name": "HACO+ Journal", "url": f"{SITE_URL}/journal/",
          "publisher": {"@type": "Organization", "name": "HACO Group", "logo": f"{SITE_URL}/assets/logo.png"}}
    out = head("Journal｜HACO+ 表参道・渋谷の美容室", desc, f"{SITE_URL}/journal/", f"{SITE_URL}{posts[0]['cover']}" if posts else "",
               f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')
    out += f"""
<section class="section">
  <div class="section-inner">
    <h1 class="label">Journal</h1>
    <div>
      <p class="intro">
        <span class="jp">サロンの外での仕事、学び、出会いの記録。ファッションウィークのバックステージ、雑誌や広告のヘアメイク、セミナー講師、東京・ロンドン・アジアでのプロジェクトをお届けします。</span>
        <span class="en">Notes from beyond the chair — backstage at fashion weeks, editorial and campaign work, education, and projects across Tokyo, London and Asia.</span>
      </p>
      <div class="filters">{chips}</div>
      <div class="grid">{''.join(cards)}
      </div>
    </div>
  </div>
</section>
{cta()}
{foot()}"""
    (OUT_DIR / "index.html").write_text(out, encoding="utf-8")


def staff_block(names):
    rows = []
    for n in names:
        s = STAFF.get(n)
        if not s:
            continue
        img = f'<img src="{e(s["photo"])}" alt="{e(n)}" loading="lazy">' if s.get("photo") else f'<div class="staff-ph">{e(n[0])}</div>'
        links = []
        if s.get("url"):
            links.append(f'<a href="{e(s["url"])}" data-ev="journal_staff_click">Profile</a>')
        if s.get("booking"):
            links.append(f'<a href="{e(s["booking"])}" target="_blank" rel="noopener" data-ev="book_click">Book</a>')
        rows.append(f"""<div class="staff-card">{img}<div><div>{e(n)}</div>
          <div class="muted">{bi(s.get('role_ja'), s.get('role'))}</div>
          <div class="staff-links">{''.join(links)}</div></div></div>""")
    if not rows:
        return ""
    return f'<div class="block"><h3>Artist</h3>{"".join(rows)}</div>'


def build_post(p, posts):
    url = f"{SITE_URL}/journal/{p['slug']}/"
    cover = p.get("cover") or ""
    cover_abs = cover if cover.startswith("http") else f"{SITE_URL}{cover}"
    title = f"{p.get('title')}｜HACO+ Journal"
    desc = p.get("summary") or ""
    ld = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": p.get("title"), "description": desc, "image": [cover_abs],
        "datePublished": str(p["date"]), "mainEntityOfPage": url,
        "author": [{"@type": "Person", "name": n} for n in p["staff"]] or [{"@type": "Organization", "name": "HACO+"}],
        "publisher": {"@type": "Organization", "name": "HACO Group", "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/assets/logo.png"}},
    }
    credits = ""
    if p["credits"]:
        credits = '<div class="block"><h3>Credits</h3><ul class="credits">' + "".join(f"<li>{e(c)}</li>" for c in p["credits"]) + "</ul></div>"
    ext = ""
    if p.get("link"):
        ext += f'<a class="ext" href="{e(p["link"])}" target="_blank" rel="noopener">{e(p.get("link_label") or p["link"])} →</a><br>'
    if p.get("instagram"):
        ext += f'<a class="ext" href="{e(p["instagram"])}" target="_blank" rel="noopener" data-ev="instagram_click">Instagram で見る / View on Instagram →</a>'
    imgs = "".join(f'<img src="{e(i)}" alt="{e(p.get("title"))}" loading="lazy">' for i in p["images"])
    body_en = f'<div class="en">{p["body_en"]}</div>' if p["body_en"] else ""
    body_ja_cls = "jp" if p["body_en"] else ""
    related = [q for q in posts if q["slug"] != p["slug"]]
    related = ([q for q in related if q["category"] == p["category"]] + [q for q in related if q["category"] != p["category"]])[:3]
    rel_cards = "".join(f"""
      <a class="card" href="/journal/{q['slug']}/">
        <div class="card-media"><img src="{e(q.get('cover'))}" alt="{e(q.get('title'))}" loading="lazy"></div>
        <div class="meta-row"><span>{cat_label(q['category'])}</span><time>{q['date'].strftime('%Y.%m.%d')}</time></div>
        <div class="card-title">{bi(q.get('title'), q.get('title_en'))}</div></a>""" for q in related)

    out = head(title, desc, url, cover_abs, f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')
    out += f"""
<article class="section">
  <div class="crumb"><a href="/journal/">Journal</a> / {cat_label(p['category'])}</div>
  <header class="article-head">
    <div class="meta-row" style="justify-content:flex-start;gap:1.5rem"><span>{cat_label(p['category'])}</span><time datetime="{p['date']}">{p['date'].strftime('%Y.%m.%d')}</time></div>
    <h1 class="article-title">{bi(p.get('title'), p.get('title_en'))}</h1>
    <p class="lede">{bi(p.get('summary'), p.get('summary_en'))}</p>
  </header>
  <div class="article-grid">
    <div><figure class="article-cover"><img src="{e(cover)}" alt="{e(p.get('title'))}"></figure>
      <div class="article-images">{imgs}</div></div>
    <div>
      <div class="article-body"><div class="{body_ja_cls}">{p['body_ja']}</div>{body_en}{ext}</div>
      {credits}
      {staff_block(p['staff'])}
    </div>
  </div>
</article>
{cta()}
<section class="section">
  <div class="section-inner">
    <h2 class="label">More</h2>
    <div class="grid">{rel_cards}</div>
  </div>
</section>
{foot()}"""
    d = OUT_DIR / p["slug"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(out, encoding="utf-8")


def build_feed(posts):
    feed = [{
        "slug": p["slug"], "url": f"/journal/{p['slug']}/", "date": str(p["date"]),
        "category": p["category"], "title": p.get("title"), "title_en": p.get("title_en"), "cover": p.get("cover"),
    } for p in posts[:12]]
    (OUT_DIR / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
    urls = [f"{SITE_URL}/journal/"] + [f"{SITE_URL}/journal/{p['slug']}/" for p in posts]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "".join(f"  <url><loc>{e(u)}</loc></url>\n" for u in urls) + "</urlset>\n"
    (OUT_DIR / "sitemap-journal.xml").write_text(sm, encoding="utf-8")


def main():
    posts = load_posts()
    # remove article folders whose post was deleted / set to draft
    keep = {p["slug"] for p in posts}
    for d in OUT_DIR.iterdir():
        if d.is_dir() and d.name not in keep and (d / "index.html").exists():
            shutil.rmtree(d)
    build_index(posts)
    for p in posts:
        build_post(p, posts)
    build_feed(posts)
    print(f"built {len(posts)} posts")


if __name__ == "__main__":
    main()
