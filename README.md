# 🔐 ResumeVault

> **Secure resume management with AES-256 encryption, blockchain verification, and session-based authentication — built with simple HTML, CSS, and Python.**

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Plain HTML5 + CSS3 (glassmorphism dark UI) |
| Backend | Python + Flask |
| Templates | Jinja2 |
| Database | PostgreSQL + SQLAlchemy ORM |
| Auth | Flask-Login + bcrypt sessions |
| Email | Flask-Mail (SMTP) |

---

## 🚀 Quick Start

### Prerequisites
- **Python** 3.10+
- **PostgreSQL** installed and running

### 1 — Clone & Enter Project

```bash
cd ResumeVault
```

### 2 — Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### 4 — Configure Environment

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Mac/Linux
```

Edit `.env` with your values:

```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/resumevault
SECRET_KEY=any-long-random-string
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
BASE_URL=http://localhost:5000
```

> **Gmail App Password**: Google Account → Security → 2-Step Verification → App passwords

### 5 — Create PostgreSQL Database

```sql
-- In psql or pgAdmin:
CREATE DATABASE resumevault;
```

### 6 — Run the App

```bash
python run.py
```

Open **http://localhost:5000** in your browser 🎉

---

## 📁 Project Structure

```
ResumeVault/
├── app/
│   ├── __init__.py          ← Flask app factory
│   ├── models.py            ← SQLAlchemy models (User, AuditLog)
│   ├── routes/
│   │   ├── auth.py          ← /auth/* endpoints
│   │   └── main.py          ← / and /dashboard
│   ├── templates/
│   │   ├── base.html        ← Shared layout (navbar, flash msgs)
│   │   ├── index.html       ← Landing page
│   │   ├── login.html       ← Sign in
│   │   ├── signup.html      ← Register
│   │   ├── forgot_password.html
│   │   ├── reset_password.html
│   │   └── dashboard.html   ← Protected dashboard
│   └── static/
│       ├── css/style.css    ← All styling (dark glassmorphism)
│       └── js/main.js       ← Password toggle + strength meter
├── .env                     ← Your secrets (not committed)
├── .env.example             ← Template
├── requirements.txt
├── run.py                   ← Start server here
└── README.md
```

---

## 🗺️ Roadmap

| Phase | Status | Features |
|-------|--------|---------|
| Phase 1 | ✅ Done | Flask, HTML/CSS, PostgreSQL, Auth, Email |
| Phase 2 | 🔜 | Resume upload to AWS S3, dashboard CRUD |
| Phase 3 | 🔜 | AES-256 encryption, SHA-256 hashing |
| Phase 4 | 🔜 | Solidity smart contract, Polygon blockchain |
| Phase 5 | 🔜 | Docker, GitHub Actions, cloud deployment |
