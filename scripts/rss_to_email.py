import json
import os
import re
import sys
from pathlib import Path

import feedparser
import requests

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


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"last_link": ""}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def fetch_latest_item() -> dict:
    feed = feedparser.parse(FEED_URL)
    if not feed.entries:
        raise RuntimeError("RSS 解析失败：没有读取到条目")

    entry = feed.entries[0]
    title = entry.get("title", "(无标题)").strip()
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


def build_html(item: dict) -> str:
    content_html = item["content_html"]

    return f"""
<div class="bg">
  <div class="container">
    <div class="card">

      <div class="tag">RSS 更新</div>

      <h1 class="title">
        {item["title"]}
      </h1>

      <div class="meta">
        发布时间：{item["published"]}
      </div>

      <div class="divider"></div>

      <div class="content">
        {content_html}
      </div>

      <div class="footer-divider"></div>

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
}}

.bg {{
  background:#f3f2f1;
  padding:32px 0;
}}

.container {{
  max-width:760px;
  margin:auto;
  padding:0 16px;
}}

.card {{
  background:#ffffff;
  border:1px solid #edebe9;
  border-radius:20px;
  padding:32px 28px;
}}

.tag {{
  display:inline-block;
  font-size:12px;
  color:#605e5c;
  background:#f3f2f1;
  border:1px solid #edebe9;
  border-radius:999px;
  padding:4px 10px;
  margin-bottom:16px;
}}

.title {{
  margin:0 0 10px 0;
  font-size:30px;
  font-weight:700;
  color:#201f1e;
}}

.meta {{
  font-size:13px;
  color:#605e5c;
  margin-bottom:28px;
}}

.divider {{
  height:1px;
  background:#edebe9;
  margin-bottom:28px;
}}

.content {{
  font-size:16px;
  line-height:1.9;
  color:#323130;
}}

.footer-divider {{
  height:1px;
  background:#edebe9;
  margin:32px 0 20px 0;
}}

.footer {{
  font-size:12px;
  color:#605e5c;
}}

img {{
  max-width:100% !important;
  height:auto !important;
  border-radius:10px;
}}

pre {{
  background:#f8f8f8;
  border:1px solid #edebe9;
  border-radius:12px;
  padding:14px;
  overflow:auto;
}}

blockquote {{
  border-left:3px solid #c8c6c4;
  padding-left:12px;
  color:#605e5c;
}}

a {{
  color:#0f6cbd;
  text-decoration:none;
}}

@media (prefers-color-scheme: dark) {{

  .bg {{
    background:#1b1a19;
  }}

  .card {{
    background:#252423;
    border-color:#3b3a39;
  }}

  .tag {{
    background:#323130;
    border-color:#3b3a39;
    color:#d2d0ce;
  }}

  .title {{
    color:#ffffff;
  }}

  .meta {{
    color:#c8c6c4;
  }}

  .content {{
    color:#f3f2f1;
  }}

  .divider,
  .footer-divider {{
    background:#3b3a39;
  }}

  .footer {{
    color:#c8c6c4;
  }}

  pre {{
    background:#1f1f1f;
    border-color:#3b3a39;
  }}

}}

</style>
""".strip()

def send_email(item: dict) -> None:
    subject = f"阮一峰更新｜{item['title']}"
    html_body = build_html(item)
    text_body = (
        f"{item['title']}\n\n"
        f"发布时间：{item['published']}\n\n"
        f"{item['summary_text']}\n\n"
        f"原文链接：{item['link']}"
    )

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
        "text": text_body,
    }

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    print(f"Resend response: {resp.status_code} {resp.text}")

    if not resp.ok:
        raise RuntimeError(f"Resend 发信失败: {resp.status_code} {resp.text}")


def main() -> int:
    latest = fetch_latest_item()
    state = load_state()

    if not latest["link"]:
        print("No link found.")
        return 1

    if not FORCE_SEND and latest["link"] == state.get("last_link", ""):
        print("No new item.")
        return 0

    send_email(latest)
    save_state({"last_link": latest["link"]})
    print("Email sent and state updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
