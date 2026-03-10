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

    summary_html = entry.get("summary", "") or entry.get("description", "")
    summary = strip_html(summary_html)
    if len(summary) > 320:
        summary = summary[:320].rstrip() + "…"

    return {
        "title": title,
        "link": link,
        "published": published,
        "summary": summary,
    }


def build_html(item: dict) -> str:
    return f"""
<div style="margin:0;padding:0;background:#f6f8fb;">
  <div style="max-width:720px;margin:0 auto;padding:24px 16px;">
    <div style="background:#ffffff;border-radius:16px;padding:28px 24px;border:1px solid #e8edf3;">
      <div style="font-size:12px;line-height:18px;color:#667085;margin-bottom:10px;">
        阮一峰周刊 RSS 更新
      </div>

      <h1 style="margin:0 0 12px 0;font-size:26px;line-height:1.35;color:#101828;font-weight:700;">
        {item["title"]}
      </h1>

      <div style="font-size:13px;line-height:20px;color:#667085;margin-bottom:20px;">
        发布时间：{item["published"]}
      </div>

      <div style="margin-bottom:22px;">
        <a href="{item["link"]}"
           style="display:inline-block;background:#111827;color:#ffffff;text-decoration:none;
                  padding:10px 16px;border-radius:10px;font-size:14px;">
          阅读原文
        </a>
      </div>

      <div style="font-size:16px;line-height:1.8;color:#344054;">
        {item["summary"]}
      </div>

      <hr style="border:none;border-top:1px solid #eaecf0;margin:28px 0;">

      <div style="font-size:12px;line-height:20px;color:#667085;">
        这封邮件由 GitHub Actions + Resend 自动发送。<br>
        RSS 地址：{FEED_URL}
      </div>
    </div>
  </div>
</div>
""".strip()


def send_email(item: dict) -> None:
    subject = f"阮一峰更新｜{item['title']}"
    html_body = build_html(item)
    text_body = (
        f"{item['title']}\n\n"
        f"发布时间：{item['published']}\n\n"
        f"摘要：{item['summary']}\n\n"
        f"原文链接：{item['link']}"
    )

    payload = {
        "from": f"{FROM_NAME} <{FROM_EMAIL}>",
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

    if not resp.ok:
        raise RuntimeError(f"Resend 发信失败: {resp.status_code} {resp.text}")


def main() -> int:
    latest = fetch_latest_item()
    state = load_state()

    if not latest["link"]:
        print("No link found.")
        return 1

    if latest["link"] == state.get("last_link", ""):
        print("No new item.")
        return 0

    send_email(latest)
    save_state({"last_link": latest["link"]})
    print("Email sent and state updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
