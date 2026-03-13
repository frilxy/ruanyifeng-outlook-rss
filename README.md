# ruanyifeng-rss-email

<p align="center">
  <img src="https://img.icons8.com/?size=100&id=SLyEErG3AwF8&format=png&color=000000" width="120">
</p>一个自动化工具，用于 将阮一峰周刊 RSS 转换为完整邮件并发送到任意 Email 邮箱。

邮件内容为 完整 RSS 正文，并保持原始文章结构（h1、h2 等），提供更适合移动端阅读的长文排版。

项目使用 GitHub Actions 定时运行 + Resend 邮件 API，无需服务器即可长期运行。


---

✨ 特性

📖 完整 RSS 内容

邮件中包含完整周刊正文，而不是摘要。


---

📱 移动端友好的排版

采用 单列长文布局：

无卡片分块

连续阅读体验更好

更适合手机屏幕



---

🌗 自动适配深浅色模式

邮件背景保持透明，自动适配：

Light mode
Dark mode

无需额外主题逻辑。


---

⚡ 完全自动化

GitHub Actions 每周自动检查 RSS 更新并发送邮件。


---

🧠 防止重复发送

通过状态文件记录最近发送的文章。


---

🔧 支持手动强制发送

手动运行 workflow 时可强制重新发送最新周刊。


---

🏗 项目结构

```
ruanyifeng-rss-email
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
```

---

⚙️ 工作原理

```
GitHub Actions
      │
      ▼
检查 RSS 更新
      │
      ▼
获取最新周刊
      │
      ▼
生成 HTML 邮件
      │
      ▼
Resend API 发送
      │
      ▼
Email 客户端接收
```

---

⏱ 自动运行

GitHub Actions 每周五运行两次：

周五 9:00
周五 14:00

如果 RSS 没有更新：

不会发送邮件


---

🔧 手动运行

在 GitHub：

Actions
→ RSS to Email
→ Run workflow

手动运行会：

强制发送最新周刊

适合测试或重新发送。


---

🔑 配置 Secrets

在仓库：

Settings
→ Secrets and variables
→ Actions

添加以下变量：

| Name | 说明 |
| ------------- | ------------- |
| RESEND_API_KEY | Resend API Key |
| FROM_EMAIL | 发信邮箱 |
| FROM_NAME | 发信名称 |
| TO_EMAIL | 收件邮箱 |


---

📦 依赖

```
feedparser
requests
beautifulsoup4
```

---

📮 RSS 来源

https://feeds.feedburner.com/ruanyifeng


---

🚀 部署步骤

1️⃣ Fork 或创建仓库

2️⃣ 配置 GitHub Secrets

3️⃣ Push 代码

4️⃣ 手动运行一次 workflow 测试


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

