# Tempmail-MailFlow 📧

A fast, stateless disposable email service built with Python (Flask), Redis, and Cloudflare Email Routing. Generate temporary email addresses on the fly to protect your primary inbox from spam, track sign-ups, or test applications.

🌐 **Live Demo:** [https://tempmail-mailflow.onrender.com/](https://tempmail-mailflow.onrender.com/)

---

## ✨ Features

- **Instant Generation:** Create cryptographically secure, random temporary email addresses instantly.
- **Real-Time Sync:** Inbox auto-refreshes every 5 seconds without reloading the page.
- **Auto-Expiring Data:** Emails self-destruct after 3 minutes using Redis TTL—zero database bloat or memory leaks.
- **Smart Rate Limiting:** Built-in IP and Inbox-level rate limiting (`Flask-Limiter`) with automatic frontend backoff strategies.
- **Responsive UI:** Clean, minimalist interface with a built-in Dark/Light mode toggle.

## 🏗️ System Architecture

This project uses a modern, serverless-hybrid architecture to process emails quickly and cheaply without hosting a heavy SMTP server:

1. **MTA (Cloudflare Worker):** Cloudflare catches incoming raw SMTP emails and forwards them via an HTTP POST request to our webhook.
2. **Backend (Flask):** Parses the raw RFC 822 email payloads, extracts the HTML/Text bodies, and drops malicious attachments.
3. **Storage (Redis):** Stores parsed emails strictly in-memory using Lists (`lpush`). Handles atomic expiration automatically.
4. **Frontend (Vanilla JS):** Uses short-polling to fetch new messages and dynamically syncs the DOM timer with the Redis backend TTL.

## 🛠️ Tech Stack

- **Backend:** Python, Flask, Gunicorn
- **Database:** Redis (In-memory data store)
- **Email Routing:** Cloudflare Workers
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Security:** Flask-Limiter, HTML Escaping (XSS Prevention)

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- Python 3.8+
- A running instance of [Redis](https://redis.io/docs/getting-started/) (local or cloud like Upstash/Render)

### 1. Clone the repository
```bash
git clone [https://github.com/its-ap0503/Tempmail-MailFlow.git](https://github.com/its-ap0503/Tempmail-MailFlow.git)
cd Tempmail-MailFlow
