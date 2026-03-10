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
<div class="page">
  <div class="wrap">
    <div class="card">

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
  margin: 0;
  padding: 0;
  font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", Arial, sans-serif;
  background: #f5f5f5;
}}

.page {{
  background: #f3f3f3;
  padding: 40px 0;
}}

.wrap {{
  max-width: 820px;
  margin: 0 auto;
  padding: 0 20px;
}}

.card {{
  background: #ffffff;
  border: 1px solid #e5e5e5;
  border-radius: 24px;
  padding: 36px 32px;
  overflow: hidden;
  box-shadow:
    0 2px 6px rgba(0, 0, 0, 0.04),
    0 12px 32px rgba(0, 0, 0, 0.08);
}}

.title {{
  margin: 0 0 12px 0;
  font-size: 30px;
  line-height: 1.3;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #1b1b1b;
}}

.meta {{
  font-size: 13px;
  line-height: 20px;
  color: #616161;
  margin-bottom: 28px;
}}

.divider {{
  height: 1px;
  background: #ececec;
  margin-bottom: 28px;
}}

.content {{
  font-size: 16px;
  line-height: 1.9;
  color: #2f2f2f;
  word-break: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
}}

.footer-divider {{
  height: 1px;
  background: #ececec;
  margin: 36px 0 20px 0;
}}

.footer {{
  font-size: 12px;
  line-height: 20px;
  color: #6a6a6a;
}}

img {{
  max-width: 100% !important;
  height: auto !important;
  display: block;
  border-radius: 14px;
  margin: 16px 0;
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
  border-radius: 14px !important;
  padding: 16px !important;
  font-size: 14px !important;
  line-height: 1.75 !important;
}}

code {{
  word-break: break-word !important;
  font-family: Consolas, "Courier New", monospace !important;
}}

blockquote {{
  margin: 16px 0 !important;
  padding: 8px 0 8px 16px !important;
  border-left: 3px solid #b9d6f2 !important;
  color: #5d5d5d !important;
}}

p {{
  margin: 0 0 1.1em 0 !important;
}}

h1, h2, h3, h4, h5, h6 {{
  color: #1b1b1b !important;
  line-height: 1.45 !important;
  margin-top: 1.35em !important;
  margin-bottom: 0.7em !important;
}}

a {{
  color: #0b57a3 !important;
  text-decoration: none !important;
  word-break: break-word !important;
}}

hr {{
  border: none !important;
  border-top: 1px solid #e6e6e6 !important;
  margin: 24px 0 !important;
}}

ul, ol {{
  padding-left: 1.4em !important;
  margin: 0 0 1.1em 0 !important;
}}

li {{
  margin-bottom: 0.45em !important;
}}

@media (prefers-color-scheme: dark) {{
  body {{
    background: #0a0d12 !important;
  }}

  .page {{
    background: #0f131a !important;
  }}

  .card {{
    background: #1a212b !important;
    border: 1px solid #2b3440 !important;
    box-shadow:
      0 2px 8px rgba(0, 0, 0, 0.28),
      0 20px 44px rgba(0, 0, 0, 0.42) !important;
  }}

  .title {{
    color: #f5f7fa !important;
  }}

  .meta {{
    color: #aab4c0 !important;
  }}

  .divider,
  .footer-divider {{
    background: #2b3440 !important;
  }}

  .content {{
    color: #dce3ea !important;
  }}

  .footer {{
    color: #97a3af !important;
  }}

  pre {{
    background: #111720 !important;
    border-color: #2b3440 !important;
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
    border-top-color: #2b3440 !important;
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
