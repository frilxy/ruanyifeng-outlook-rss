import json
import os
import re
import sys
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

FEED_URL = "https://feeds.feedburner.com/ruanyifeng"
STATE_FILE = Path("data/last_sent.json")

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
TO_EMAIL = os.environ["TO_EMAIL"]
FROM_EMAIL = os.environ["FROM_EMAIL"]
FROM_NAME = os.environ.get("FROM_NAME", "RSS Bot")
FORCE_SEND = os.environ.get("FORCE_SEND", "false").lower() == "true"


def strip_html(html: str) -> str:
    if not html:
        return ""
    html = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", "", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"last_link": ""}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def fetch_latest_item():
    feed = feedparser.parse(FEED_URL)

    if not feed.entries:
        raise RuntimeError("RSS 解析失败")

    entry = feed.entries[0]

    title = entry.get("title", "").strip()
    link = entry.get("link", "").strip()
    published = entry.get("published", "").strip()

    content_html = ""

    if entry.get("content"):
        content_html = entry["content"][0]["value"]

    if not content_html:
        content_html = entry.get("summary", "")

    summary_text = strip_html(content_html)

    return {
        "title": title,
        "link": link,
        "published": published,
        "content_html": content_html,
        "summary_text": summary_text
    }


def split_content_into_sections(content_html):
    soup = BeautifulSoup(content_html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    headings = soup.find_all("h2")

    if not headings:
        return [{"title": "", "html": content_html}]

    sections = []

    current_title = ""
    current_nodes = []
    intro_nodes = []

    seen_first = False

    for node in soup.contents:

        if getattr(node, "name", None) == "h2":

            if not seen_first:
                seen_first = True

                intro_html = "".join(str(n) for n in intro_nodes)

                if strip_html(intro_html):
                    sections.append({
                        "title": "",
                        "html": intro_html
                    })

            else:
                sections.append({
                    "title": current_title,
                    "html": "".join(str(n) for n in current_nodes)
                })

            current_title = node.get_text(strip=True)
            current_nodes = []

        else:
            if seen_first:
                current_nodes.append(node)
            else:
                intro_nodes.append(node)

    if current_nodes:
        sections.append({
            "title": current_title,
            "html": "".join(str(n) for n in current_nodes)
        })

    return sections


def build_section_card(title, html):

    title_html = ""

    if title:
        title_html = f"""
        <h2 class="section-title">{title}</h2>
        <div class="section-divider"></div>
        """

    return f"""
    <div class="content-card">
        {title_html}
        <div class="content-body">
        {html}
        </div>
    </div>
    """


def build_html(item):

    sections = split_content_into_sections(item["content_html"])

    intro_html = ""
    content_sections = sections

    if sections and sections[0]["title"] == "":
        intro_html = sections[0]["html"]
        content_sections = sections[1:]

    sections_html = "".join(
        build_section_card(sec["title"], sec["html"])
        for sec in content_sections
    )

    return f"""
<div class="page">

<div class="wrap">

<div class="hero-card">

<h1 class="title">
{item["title"]}
</h1>

<div class="meta">
发布时间：{item["published"]}
</div>

<div class="content-body">
{intro_html}
</div>

</div>

{sections_html}

<div class="footer-card">

<div class="footer">
由 GitHub Actions + Resend 自动发送<br>
来源：{FEED_URL}
</div>

</div>

</div>

</div>

<style>

body {{
margin:0;
padding:0;
font-family:"Segoe UI","Microsoft YaHei",Arial,sans-serif;
background:#f3f3f3;
}}

.page {{
padding:32px 0;
}}

.wrap {{
max-width:820px;
margin:auto;
padding:0 20px;
}}

.hero-card,
.content-card,
.footer-card {{
background:#ffffff;
border:1px solid #e5e5e5;
border-radius:24px;
padding:32px;
margin-bottom:18px;
box-shadow:
0 2px 6px rgba(0,0,0,0.04),
0 12px 32px rgba(0,0,0,0.08);
}}

.title {{
margin:0 0 10px 0;
font-size:30px;
font-weight:700;
letter-spacing:-0.02em;
color:#1b1b1b;
}}

.meta {{
font-size:13px;
color:#666;
}}

.section-title {{
margin:0;
font-size:24px;
font-weight:700;
color:#1b1b1b;
}}

.section-divider {{
height:1px;
background:#ececec;
margin:16px 0 20px 0;
}}

.content-body {{
font-size:16px;
line-height:1.9;
color:#2f2f2f;
word-break:break-word;
}}

.footer {{
font-size:12px;
color:#6a6a6a;
}}

img {{
max-width:100%!important;
height:auto!important;
display:block;
border-radius:14px;
margin:16px 0;
}}

pre {{
background:#f7f7f7!important;
border:1px solid #e6e6e6!important;
border-radius:14px!important;
padding:16px!important;
overflow:auto;
}}

blockquote {{
border-left:3px solid #b9d6f2!important;
padding-left:12px!important;
color:#5d5d5d!important;
}}

@media (prefers-color-scheme: dark) {{

body {{
background:#0a0d12!important;
}}

.hero-card,
.content-card,
.footer-card {{
background:#1a212b!important;
border:1px solid #2b3440!important;
box-shadow:
0 2px 8px rgba(0,0,0,0.28),
0 20px 44px rgba(0,0,0,0.42)!important;
}}

.title,
.section-title {{
color:#f5f7fa!important;
}}

.meta {{
color:#aab4c0!important;
}}

.content-body {{
color:#dce3ea!important;
}}

.section-divider {{
background:#2b3440!important;
}}

.footer {{
color:#97a3af!important;
}}

pre {{
background:#111720!important;
border-color:#2b3440!important;
color:#dce3ea!important;
}}

blockquote {{
border-left-color:#4f89c6!important;
color:#b9c3cf!important;
}}

}}

</style>
"""


def send_email(item):

    subject = f"阮一峰更新｜{item['title']}"

    html_body = build_html(item)

    text_body = f"""
{item['title']}

发布时间：{item['published']}

{item['summary_text']}

原文：
{item['link']}
"""

    payload = {
        "from": f"{FROM_NAME} <{FROM_EMAIL}>",
        "to": [TO_EMAIL],
        "subject": subject,
        "html": html_body,
        "text": text_body
    }

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        },
        json=payload
    )

    if not resp.ok:
        raise RuntimeError(resp.text)


def main():

    latest = fetch_latest_item()

    state = load_state()

    if not FORCE_SEND and latest["link"] == state.get("last_link"):
        print("No new item")
        return 0

    send_email(latest)

    save_state({"last_link": latest["link"]})

    print("Email sent")

    return 0


if __name__ == "__main__":
    sys.exit(main())
