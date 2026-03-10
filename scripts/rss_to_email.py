import json
import os
import re
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import feedparser


FEED_URL = "https://feeds.feedburner.com/ruanyifeng"
STATE_FILE = Path("data/last_sent.json")

SMTP_SERVER = "smtp-mail.outlook.com"
SMTP_PORT = 587

OUTLOOK_EMAIL = os.environ["OUTLOOK_EMAIL"]
OUTLOOK_APP_PASSWORD = os.environ["OUTLOOK_APP_PASSWORD"]
TO_EMAIL = os.environ["TO_EMAIL"]
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
    title = item["title"]
    link = item["link"]
    published = item["published"]
    summary = item["summary"]

    return f"""
<div style="margin:0;padding:0;background:#f6f8fb;">
  <div style="max-width:720px;margin:0 auto;padding:24px 16px;">
    <div style="background:#ffffff;border-radius:16px;padding:28px 24px;border:1px solid #e8edf3;">
      <div style="font-size:12px;line-height:18px;color:#667085;margin-bottom:10px;">
        阮一峰周刊 RSS 更新
      </div>

      <h1 style="margin:0 0 12px 0;font-size:26px;line-height:1.35;color:#101828;font-weight:700;">
        {title}
      </h1>

      <div style="font-size:13px;line-height:20px;color:#667085;margin-bottom:20px;">
        发布时间：{published}
      </div>

      <div style="margin-bottom:22px;">
        <a href="{link}"
           style="display:inline-block;background:#111827;color:#ffffff;text-decoration:none;
                  padding:10px 16px;border-radius:10px;font-size:14px;">
          阅读原文
        </a>
      </div>

      <div style="font-size:16px;line-height:1.8;color:#344054;">
        {summary}
      </div>

      <hr style="border:none;border-top:1px solid #eaecf0;margin:28px 0;">

      <div style="font-size:12px;line-height:20px;color:#667085;">
        这封邮件由 GitHub Actions 自动发送到 Outlook。<br>
        RSS 地址：{FEED_URL}
      </div>
    </div>
  </div>
</div>
""".strip()


def send_email(item: dict) -> None:
    subject = f"阮一峰更新｜{item['title']}"
    html_body = build_html(item)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{OUTLOOK_EMAIL}>"
    msg["To"] = TO_EMAIL

    text_body = f"{item['title']}\n\n发布时间：{item['published']}\n\n摘要：{item['summary']}\n\n原文链接：{item['link']}"
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(OUTLOOK_EMAIL, OUTLOOK_APP_PASSWORD)
        server.sendmail(OUTLOOK_EMAIL, [TO_EMAIL], msg.as_string())


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
