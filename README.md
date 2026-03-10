# ruanyifeng-email-rss

<p align="center">
  <img src="https://img.icons8.com/?size=100&id=SLyEErG3AwF8&format=png&color=000000" width="120">
</p>一个自动化工具，用于 将阮一峰周刊 RSS 转换为高可读性的邮件，并发送到 Email 邮箱。

邮件内容为 完整 RSS 正文，并自动按照文章中的 h2 标题拆分为多张卡片，使阅读体验更接近博客或文章页面。

项目使用 GitHub Actions 定时运行 + Resend 发信 API，无需服务器即可稳定运行。


---

✨ 特性

📖 完整 RSS 内容

邮件中包含完整周刊内容，而不是摘要。

🧩 智能卡片布局

自动根据文章 h2 标题拆分内容：

主卡片（标题 + 导语）
内容卡片 1（h2）
内容卡片 2（h2）
内容卡片 3（h2）

🖥 Email 阅读体验优化

Windows 11 风格卡片布局

图片自适应

代码块样式优化

深色 / 浅色模式自动适配


⚡ 完全自动化

每周五自动检查 RSS 更新并发送邮件。

🧠 避免重复发送

使用状态文件记录最近发送的文章。

🔧 支持手动强制发送

手动运行 workflow 时会强制发送最新周刊。



---

🏗 项目结构

ruanyifeng-email-rss
│
├─ .github
│  └─ workflows
│     └─ rss-email.yml
│
├─ scripts
│  └─ rss_to_email.py
│
├─ data
│  └─ last_sent.json
│
├─ requirements.txt
└─ README.md


---

⚙️ 工作原理

GitHub Actions
      │
      ▼
定时检查 RSS
      │
      ▼
解析最新周刊
      │
      ▼
按 h2 拆分文章
      │
      ▼
生成 HTML 邮件
      │
      ▼
Resend API 发送
      │
      ▼
Email 收件


---

⏱ 自动运行

GitHub Actions 每周五运行两次：

周五 12:00
周五 18:00

如果 RSS 没有更新：

不会发送邮件


---

🔧 手动运行

在 GitHub：

Actions
→ RSS to Email
→ Run workflow

手动运行时会：

强制发送最新周刊

适合测试或重新发送。


---

🔑 配置 Secrets

在仓库：

Settings
→ Secrets and variables
→ Actions

添加以下变量：

Name	说明

RESEND_API_KEY	Resend API Key
FROM_EMAIL	发信邮箱
FROM_NAME	发信名称
TO_EMAIL	收件邮箱



---

📦 依赖

feedparser
requests
beautifulsoup4


---

📮 RSS 来源

https://feeds.feedburner.com/ruanyifeng


---

🚀 部署步骤

1️⃣ Fork 或创建仓库

2️⃣ 添加 GitHub Secrets

3️⃣ Push 代码

4️⃣ 手动运行一次 workflow 测试


---

📷 邮件效果

邮件内容会被自动拆分为多个卡片：

标题 + 导语

科技动态

教程资源

工具推荐

阅读体验接近文章页面。


---

📄 License

MIT License


---

🙏 致谢

阮一峰的网络日志

Resend

GitHub Actions

Icons8



---
