# 🔐 ResumeVault

> **Military-grade secure resume management system built with Flask, PostgreSQL, AWS S3, and client-side AES-256 decryption, styled in a vibrant Retro Pop-Art theme.**
>
> 🌐 **Live URL:** [https://resumevault-pb8f.onrender.com](https://resumevault-pb8f.onrender.com)

---

## 🎨 Premium Retro Pop-Art UI/UX

ResumeVault features a custom-built **Retro Pop-Art Design System** built using vanilla CSS variables, transitions, and responsive grid layouts.
- **Bold Aesthetics:** Solid dark outlines (`3px solid #111`), custom flat color palettes, and playful drop-shadows.
- **Interactive Micro-Animations:** Responsive feedback hover states and popup animations on dashboard cards.
- **Fully Responsive & Phone-Friendly:**
  - On laptops: Sticky sidebar navigation locks in place while scrollable panels handle files.
  - On mobile/tablet screens: Sidebar transitions automatically into a **floating bottom navigation tab bar** (just like a native mobile app) and buttons scale down to fit small screens perfectly.

---

## 🛠️ Tech Stack & Architecture

| Layer | Technology | Description |
|-------|------------|-------------|
| **Frontend** | HTML5 + Vanilla CSS3 | Custom Retro Pop-Art style sheets, responsive layouts |
| **Backend** | Python 3.10+ + Flask | WSGI micro-framework managing routing, auth, and logic |
| **Template Engine** | Jinja2 | Dynamic HTML rendering and session state management |
| **Database** | PostgreSQL + SQLAlchemy | Persistent user metadata, file hashes, and active share links |
| **Authentication** | Flask-Login + Bcrypt | Secure password hashing, login sessions, and page guards |
| **Cloud Storage** | AWS S3 + Boto3 | Encrypted block storage for documents |
| **Crypto Library** | PyJWT / Cryptography | Secure link generation and SHA-256 integrity hashing |

---

## 🔒 Security & Data Encryption Flow

ResumeVault is built with security at its core, utilizing industry-standard cryptographic techniques to guard user data:

### 1. File Encryption (AES-256)
- When a user uploads a resume, it is encrypted using **AES-256** symmetric-key encryption prior to storage in the AWS S3 bucket.
- The decryption key is securely stored and processed in the cloud environment, ensuring files cannot be read if the S3 bucket is compromised directly.

### 2. Integrity Checking (SHA-256 Hashing)
- Upon upload, a unique **SHA-256 hash (digital fingerprint)** is computed for the document.
- Whenever a resume is downloaded or shared, the system recalculates the SHA-256 fingerprint to verify that the file has not been modified or corrupted, guaranteeing zero tampering.

### 3. Expiring Share Links
- Users can generate public sharing links for their resumes.
- The links can be configured to expire in **15 minutes, 1 hour, 24 hours, or 7 days**.
- Timezones are normalized to UTC to prevent local computer offset bugs, and links are immediately invalidated and purged once they expire.

---

## 🚀 Local Installation & Quick Start

### Prerequisites
- **Python** 3.10+
- **PostgreSQL** database server
- **AWS Account** with an S3 bucket configured

### 1 — Clone the Repository
```bash
git clone https://github.com/Charan0120/resumechain-vault.git
cd resumechain-vault
```

### 2 — Configure Virtual Environment
Create and activate a virtual environment to manage dependencies cleanly:

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3 — Install Dependencies
Install all required libraries including backend, cryptography, database drivers, and S3 wrappers:
```bash
pip install -r requirements.txt
```

### 4 — Set Up Environment Variables
Create a `.env` file in the root directory:
```bash
copy .env.example .env     # Windows
cp .env.example .env       # Mac/Linux
```

Populate the `.env` file with your credentials:
```env
# Flask Settings
SECRET_KEY=your-random-secret-key
FLASK_APP=run.py
FLASK_ENV=development

# Database Settings
DATABASE_URL=postgresql://<username>:<password>@localhost:5432/resumevault

# AWS S3 Settings
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-s3-bucket-name
AWS_S3_REGION=us-east-1

# SMTP Email Configuration (Optional / Verification)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password
```

### 5 — Run Database Migrations
Initialize your database schemas inside PostgreSQL:
```bash
# Enter python interactive mode or run schema migration
python -c "from app import create_app, db; db.create_all(app=create_app())"
```

### 6 — Launch the Server
```bash
python run.py
```
Go to [http://localhost:5000](http://localhost:5000) in your browser.

---

## 📁 Project Structure

```
ResumeVault/
├── app/
│   ├── __init__.py          # Flask application factory
│   ├── models.py            # SQLAlchemy Database Models (User, Resume, ShareLink, AuditLog)
│   ├── routes/
│   │   ├── auth.py          # Authentication routing (Login, Signup, Reset Password)
│   │   └── main.py          # Application routing (Dashboard, Uploads, Share Links)
│   ├── services/
│   │   └── s3_service.py    # AWS S3 upload/download bucket helpers
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Retro Pop-Art stylesheet
│   │   └── js/
│   │       └── main.js      # Password complexity check & modal control scripting
│   └── templates/
│       ├── base.html        # Shared base wrapper with Retro navbar
│       ├── index.html       # Landing page (with pricing & features)
│       ├── login.html       # Retro login card
│       ├── signup.html      # Retro sign-up card
│       ├── dashboard.html   # Main dashboard grid
│       └── share_links.html # Share link management layout
├── .env.example             # Template for variables
├── requirements.txt         # Server requirements list
├── run.py                   # Application entry point
├── render.yaml              # Render blueprint deployment file
└── README.md                # Project documentation
```

---

## ☁️ Cloud Deployment (Render)

To deploy this application to **Render**, you can use the configured `render.yaml` blueprint:

1. Connect your GitHub repository to your Render Account.
2. Create a new **Blueprint Route**.
3. Render will parse the `render.yaml` and provision:
   - A **PostgreSQL Web Service** database.
   - A **Python Web Service** running `gunicorn run:app`.
4. Inject your S3 Credentials, database URL, and mail password keys directly in Render's environment variable fields.
5. Deploy! Render will auto-deploy updates whenever you push commits to `main`.
