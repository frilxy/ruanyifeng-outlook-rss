import json
import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import requests


FEED_URL = "https://feeds.feedburner.com/ruanyifeng"
STATE_FILE = Path("data/last_sent.json")

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
TO_EMAIL = os.environ["TO_EMAIL"]

# 这里改成你在 Resend 中可用的发件地址
FROM_EMAIL = os.environ.get("FROM_EMAIL", "RSS Bot <onboarding@resend.dev>")


def strip_html(html: str) -> str:
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
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_latest_item() -> dict:
    resp = requests.get(FEED_URL, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)

    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("RSS 解析失败：未找到 channel")

    item = channel.find("item")
    if item is None:
        raise RuntimeError("RSS 解析失败：未找到 item")

    title = item.findtext("title", default="(无标题)").strip()
    link = item.findtext("link", default="").strip()
    pub_date = item.findtext("pubDate", default="").strip()
    description = item.findtext("description", default="").strip()

    summary = strip_html(description)
    if len(summary) > 280:
        summary = summary[:280].rstrip() + "…"

    return {
        "title": title,
        "link": link,
        "pub_date": pub_date,
        "summary": summary,
    }


def build_html(item: dict) -> str:
    title = item["title"]
    link = item["link"]
    pub_date = item["pub_date"]
    summary = item["summary"]

    return f"""
<div style="margin:0;padding:0;background:#f6f8fb;">
  <div style="max-width:720px;margin:0 auto;padding:24px 16px;">
    <div style="background:#ffffff;border-radius:16px;padding:28px 24px;border:1px solid #e8edf3;">
      <div style="font-size:12px;line-height:18px;color:#667085;margin-bottom:10px;">
        阮一峰博客 RSS 更新
      </div>

      <h1 style="margin:0 0 12px 0;font-size:26px;line-height:1.35;color:#101828;font-weight:700;">
        {title}
      </h1>

      <div style="font-size:13px;line-height:20px;color:#667085;margin-bottom:20px;">
        发布时间：{pub_date}
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
        这封邮件由 GitHub Actions 自动发送。<br>
        RSS 地址：{FEED_URL}
      </div>
    </div>
  </div>
</div>
""".strip()


def send_email(item: dict) -> None:
    subject = f"阮一峰更新｜{item['title']}"
    html = build_html(item)

    payload = {
        "from": FROM_EMAIL,
        "to": [TO_EMAIL],
        "subject": subject,
        "html": html,
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
    resp.raise_for_status()
    print("Email sent:", resp.text)


def main() -> int:
    latest = fetch_latest_item()
    state = load_state()
    last_link = state.get("last_link", "")

    if not latest["link"]:
        print("No link found in feed.")
        return 1

    if latest["link"] == last_link:
        print("No new item.")
        return 0

    send_email(latest)
    save_state({"last_link": latest["link"]})
    print("State updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
