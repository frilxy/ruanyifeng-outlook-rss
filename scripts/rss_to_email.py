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


def normalize_content_html(content_html: str) -> str:
    soup = BeautifulSoup(content_html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    # 删除正文里可能重复出现的 h1，避免和邮件主标题冲突
    first_h1 = soup.find("h1")
    if first_h1:
        first_h1.decompose()

    # 给 h2 增加统一 class，便于邮件内统一样式
    for h2 in soup.find_all("h2"):
        existing = h2.get("class", [])
        h2["class"] = list(existing) + ["section-heading"]

    return "".join(str(node) for node in soup.contents).strip()


def build_html(item):
    normalized_html = normalize_content_html(item["content_html"])

    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{item["title"]}</title>
<style>
  body {{
    margin: 0;
    padding: 0;
    background: #ffffff;
    color: #111111;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue",
      Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    -webkit-text-size-adjust: 100%;
    text-size-adjust: 100%;
  }}

  .page {{
    width: 100%;
    background: #ffffff;
  }}

  .wrap {{
    max-width: 680px;
    margin: 0 auto;
    padding: 0 20px;
  }}

  .header {{
    padding: 32px 0 18px 0;
    border-bottom: 1px solid #ececec;
  }}

  .title {{
    margin: 0;
    font-size: 30px;
    line-height: 1.22;
    font-weight: 700;
    color: #111111;
    letter-spacing: -0.02em;
  }}

  .meta {{
    margin-top: 10px;
    font-size: 13px;
    line-height: 1.5;
    color: #666666;
  }}

  .content {{
    padding: 24px 0 12px 0;
    font-size: 16px;
    line-height: 1.8;
    color: #222222;
    word-break: break-word;
    overflow-wrap: break-word;
  }}

  .content p {{
    margin: 0 0 1em 0;
  }}

  .content h2.section-heading {{
    margin: 2em 0 0.8em 0;
    font-size: 22px;
    line-height: 1.35;
    font-weight: 700;
    color: #111111;
    letter-spacing: -0.01em;
  }}

  .content h3,
  .content h4,
  .content h5,
  .content h6 {{
    margin: 1.5em 0 0.7em 0;
    color: #111111;
    line-height: 1.4;
  }}

  .content ul,
  .content ol {{
    margin: 0 0 1em 0;
    padding-left: 1.35em;
  }}

  .content li {{
    margin-bottom: 0.35em;
  }}

  .content a {{
    color: #0f62fe;
    text-decoration: none;
    word-break: break-word;
  }}

  .content blockquote {{
    margin: 1.2em 0;
    padding: 0 0 0 14px;
    border-left: 3px solid #d9d9d9;
    color: #555555;
  }}

  .content hr {{
    border: none;
    border-top: 1px solid #ececec;
    margin: 1.6em 0;
  }}

  .content pre {{
    margin: 1em 0;
    padding: 14px 16px;
    background: #f7f7f8;
    border: 1px solid #ebebed;
    border-radius: 10px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 14px;
    line-height: 1.7;
  }}

  .content code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
    word-break: break-word;
  }}

  .content table {{
    width: 100% !important;
    max-width: 100% !important;
    border-collapse: collapse !important;
    table-layout: fixed !important;
    margin: 1em 0;
  }}

  .content img {{
    max-width: 100% !important;
    height: auto !important;
    display: block;
    margin: 1em 0;
    border-radius: 10px;
  }}

  .footer {{
    padding: 18px 0 32px 0;
    border-top: 1px solid #ececec;
    font-size: 12px;
    line-height: 1.7;
    color: #777777;
  }}

  @media (prefers-color-scheme: dark) {{
    body, .page {{
      background: #0b0b0c !important;
      color: #f5f5f5 !important;
    }}

    .header {{
      border-bottom-color: #2a2a2d !important;
    }}

    .title {{
      color: #f5f5f5 !important;
    }}

    .meta {{
      color: #a1a1aa !important;
    }}

    .content {{
      color: #e5e5e5 !important;
    }}

    .content h2.section-heading,
    .content h3,
    .content h4,
    .content h5,
    .content h6 {{
      color: #f5f5f5 !important;
    }}

    .content a {{
      color: #8ab4ff !important;
    }}

    .content blockquote {{
      border-left-color: #3a3a3d !important;
      color: #b8b8bd !important;
    }}

    .content hr {{
      border-top-color: #2a2a2d !important;
    }}

    .content pre {{
      background: #141416 !important;
      border-color: #2a2a2d !important;
      color: #e5e5e5 !important;
    }}

    .footer {{
      border-top-color: #2a2a2d !important;
      color: #9a9aa1 !important;
    }}
  }}

  @media screen and (max-width: 600px) {{
    .wrap {{
      padding: 0 14px;
    }}

    .header {{
      padding: 22px 0 14px 0;
    }}

    .title {{
      font-size: 24px;
      line-height: 1.28;
    }}

    .meta {{
      margin-top: 8px;
      font-size: 12px;
    }}

    .content {{
      padding: 18px 0 10px 0;
      font-size: 15px;
      line-height: 1.76;
    }}

    .content h2.section-heading {{
      font-size: 20px;
      margin-top: 1.7em;
    }}

    .footer {{
      padding: 16px 0 24px 0;
    }}
  }}
</style>
</head>
<body>
  <div class="page">
    <div class="wrap">
      <div class="header">
        <h1 class="title">{item["title"]}</h1>
        <div class="meta">发布时间：{item["published"]}</div>
      </div>

      <div class="content">
        {normalized_html}
      </div>

      <div class="footer">
        由 GitHub Actions + Resend 自动发送。<br>
        来源：{FEED_URL}
      </div>
    </div>
  </div>
</body>
</html>
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
        print("No new item")
        return 0

    send_email(latest)
    save_state({"last_link": latest["link"]})
    print("Email sent and state updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
