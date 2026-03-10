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
        raise RuntimeError("RSS 解析失败：没有读取到条目")

    entry = feed.entries[0]

    title = entry.get("title", "").strip()
    link = entry.get("link", "").strip()
    published = entry.get("published", "").strip()

    content_html = ""
    if entry.get("content") and isinstance(entry.get("content"), list):
        content_html = entry["content"][0].get("value", "") or ""

    if not content_html:
        content_html = entry.get("summary", "") or entry.get("description", "") or ""

    summary_text = strip_html(content_html)

    return {
        "title": title,
        "link": link,
        "published": published,
        "content_html": content_html,
        "summary_text": summary_text,
    }


def split_content_into_sections(content_html):
    soup = BeautifulSoup(content_html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    headings = soup.find_all("h2")

    if not headings:
        return [{"title": "", "html": "".join(str(node) for node in soup.contents)}]

    sections = []
    current_title = ""
    current_nodes = []
    intro_nodes = []
    seen_first = False

    for node in soup.contents:
        if getattr(node, "name", None) == "h2":
            if not seen_first:
                seen_first = True
                intro_html = "".join(str(n) for n in intro_nodes).strip()
                if strip_html(intro_html):
                    sections.append({
                        "title": "",
                        "html": intro_html
                    })
            else:
                sections.append({
                    "title": current_title,
                    "html": "".join(str(n) for n in current_nodes).strip()
                })

            current_title = node.get_text(" ", strip=True)
            current_nodes = []
        else:
            if seen_first:
                current_nodes.append(node)
            else:
                intro_nodes.append(node)

    if seen_first:
        sections.append({
            "title": current_title,
            "html": "".join(str(n) for n in current_nodes).strip()
        })

    cleaned = []
    for sec in sections:
        if sec["title"] or strip_html(sec["html"]):
            cleaned.append(sec)

    return cleaned


def build_compact_sections(sections):
    parts = []

    for index, sec in enumerate(sections):
        title_html = ""
        if sec["title"]:
            title_html = f"""
            <h2 class="section-title">{sec["title"]}</h2>
            """

        divider_html = ""
        if index != len(sections) - 1:
            divider_html = '<div class="section-divider"></div>'

        parts.append(f"""
        <div class="section-block">
            {title_html}
            <div class="content-body">
                {sec["html"]}
            </div>
        </div>
        {divider_html}
        """)

    return "".join(parts)


def build_html(item):
    sections = split_content_into_sections(item["content_html"])

    intro_html = ""
    content_sections = sections

    if sections and sections[0]["title"] == "":
        intro_html = sections[0]["html"]
        content_sections = sections[1:]

    content_html = build_compact_sections(content_sections) if content_sections else ""

    return f"""
<div class="page">
  <div class="wrap">

    <div class="hero-card">
      <h1 class="title">{item["title"]}</h1>
      <div class="meta">发布时间：{item["published"]}</div>
      <div class="content-body hero-body">
        {intro_html}
      </div>
    </div>

    <div class="content-card">
      {content_html}
    </div>

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
  margin: 0;
  padding: 0;
  font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
  background: #f3f3f3;
}}

.page {{
  padding: 14px 0 18px 0;
  background: #f3f3f3;
}}

.wrap {{
  max-width: 760px;
  margin: 0 auto;
  padding: 0 12px;
}}

.hero-card,
.content-card,
.footer-card {{
  background: #ffffff;
  border: 1px solid #e7e7e7;
  border-radius: 16px;
  padding: 18px 16px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}}

.title {{
  margin: 0 0 8px 0;
  font-size: 24px;
  line-height: 1.32;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #1b1b1b;
}}

.meta {{
  font-size: 12px;
  line-height: 18px;
  color: #666666;
  margin-bottom: 12px;
}}

.hero-body:empty {{
  display: none;
}}

.section-block {{
  margin: 0;
}}

.section-title {{
  margin: 0 0 10px 0;
  font-size: 20px;
  line-height: 1.4;
  font-weight: 700;
  color: #1b1b1b;
}}

.section-divider {{
  height: 1px;
  background: #ececec;
  margin: 16px 0;
}}

.content-body {{
  font-size: 15px;
  line-height: 1.82;
  color: #2f2f2f;
  word-break: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
}}

.footer {{
  font-size: 12px;
  line-height: 18px;
  color: #6a6a6a;
}}

img {{
  max-width: 100% !important;
  height: auto !important;
  display: block;
  border-radius: 10px;
  margin: 12px 0;
}}

table {{
  width: 100% !important;
  max-width: 100% !important;
  border-collapse: collapse !important;
  table-layout: fixed !important;
}}

pre {{
  white-space: pre-wrap !important;
  word-break: break-word !important;
  overflow-x: auto !important;
  background: #f7f7f7 !important;
  border: 1px solid #e6e6e6 !important;
  border-radius: 10px !important;
  padding: 12px !important;
  font-size: 13px !important;
  line-height: 1.7 !important;
}}

code {{
  word-break: break-word !important;
  font-family: Consolas, "Courier New", monospace !important;
}}

blockquote {{
  margin: 12px 0 !important;
  padding: 6px 0 6px 12px !important;
  border-left: 3px solid #b9d6f2 !important;
  color: #5d5d5d !important;
}}

p {{
  margin: 0 0 0.95em 0 !important;
}}

h1, h2, h3, h4, h5, h6 {{
  color: #1b1b1b !important;
  line-height: 1.42 !important;
  margin-top: 1.15em !important;
  margin-bottom: 0.55em !important;
}}

a {{
  color: #0b57a3 !important;
  text-decoration: none !important;
  word-break: break-word !important;
}}

hr {{
  border: none !important;
  border-top: 1px solid #e6e6e6 !important;
  margin: 18px 0 !important;
}}

ul, ol {{
  padding-left: 1.3em !important;
  margin: 0 0 0.95em 0 !important;
}}

li {{
  margin-bottom: 0.35em !important;
}}

@media (prefers-color-scheme: dark) {{
  body {{
    background: #0b0f14 !important;
  }}

  .page {{
    background: #0f141b !important;
  }}

  .hero-card,
  .content-card,
  .footer-card {{
    background: #1b232d !important;
    border: 1px solid #2c3642 !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.24) !important;
  }}

  .title,
  .section-title {{
    color: #f5f7fa !important;
  }}

  .meta {{
    color: #aab4c0 !important;
  }}

  .section-divider {{
    background: #2c3642 !important;
  }}

  .content-body {{
    color: #dce3ea !important;
  }}

  .footer {{
    color: #97a3af !important;
  }}

  pre {{
    background: #111720 !important;
    border-color: #2c3642 !important;
    color: #dce3ea !important;
  }}

  blockquote {{
    border-left-color: #4f89c6 !important;
    color: #b9c3cf !important;
  }}

  h1, h2, h3, h4, h5, h6 {{
    color: #f5f7fa !important;
  }}

  a {{
    color: #8ec5ff !important;
  }}

  hr {{
    border-top-color: #2c3642 !important;
  }}
}}

@media screen and (max-width: 600px) {{
  .page {{
    padding: 10px 0 14px 0;
  }}

  .wrap {{
    padding: 0 8px;
  }}

  .hero-card,
  .content-card,
  .footer-card {{
    border-radius: 12px;
    padding: 14px 12px;
    margin-bottom: 8px;
  }}

  .title {{
    font-size: 21px;
    line-height: 1.34;
  }}

  .section-title {{
    font-size: 18px;
  }}

  .content-body {{
    font-size: 15px;
    line-height: 1.78;
  }}

  .section-divider {{
    margin: 14px 0;
  }}
}}
</style>
""".strip()


def send_email(item):
    subject = f"阮一峰更新｜{item['title']}"
    html_body = build_html(item)
    text_body = f"""{item['title']}

发布时间：{item['published']}

{item['summary_text']}

原文：
{item['link']}
"""

    from_email = FROM_EMAIL.strip()
    from_name = FROM_NAME.strip()

    if "<" in from_email or ">" in from_email:
        from_value = from_email
    elif from_name:
        from_value = f"{from_name} <{from_email}>"
    else:
        from_value = from_email

    payload = {
        "from": from_value,
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
        json=payload,
        timeout=30
    )

    print(f"Resend response: {resp.status_code} {resp.text}")

    if not resp.ok:
        raise RuntimeError(f"Resend 发信失败: {resp.status_code} {resp.text}")


def main():
    latest = fetch_latest_item()
    state = load_state()

    if not latest["link"]:
        print("No link found.")
        return 1

    if not FORCE_SEND and latest["link"] == state.get("last_link"):
        print("No new item.")
        return 0

    send_email(latest)
    save_state({"last_link": latest["link"]})
    print("Email sent and state updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
