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
  pad
