# The Inner Compass Project — Website

A full-stack mental health advocacy web platform built with Flask + PostgreSQL, deployed on Railway.

---

## 🗂 Project Structure

```
icp/
├── app.py                  # Flask backend — all routes, models, API
├── requirements.txt        # Python dependencies
├── Procfile                # Gunicorn start command for Railway
├── railway.json            # Railway deploy config
├── .gitignore
├── templates/
│   ├── base.html           # Shared layout (nav, footer)
│   ├── index.html          # Homepage
│   ├── signup.html         # Registration page
│   ├── login.html          # Login page
│   ├── dashboard.html      # Member dashboard
│   ├── admin.html          # Admin panel
│   ├── resources.html      # Resource hub
│   └── 404.html            # Custom 404 page
└── static/
    ├── css/style.css       # Full stylesheet
    └── js/main.js          # Shared JavaScript
```

---

## 🚀 Deployment Guide (GitHub → Railway)

### Step 1 — Push to GitHub

```bash
# In your project folder
git init
git add .
git commit -m "feat: full site rebuild — auth, dashboard, admin, resources"
git remote add origin https://github.com/YOUR_USERNAME/inner-compass-project.git
git push -u origin main
```

### Step 2 — Set Environment Variables on Railway

Go to your Railway project → **Variables** tab and add:

| Variable          | Value                                      |
|-------------------|--------------------------------------------|
| `DATABASE_URL`    | (auto-set by Railway PostgreSQL plugin)    |
| `SECRET_KEY`      | A long random string (e.g. 64 random chars)|
| `ADMIN_EMAIL`     | `Innercompassproject25@gmail.com`          |
| `ADMIN_PASSWORD`  | `ICP@Admin2025!` (change after first login)|

To generate a secure SECRET_KEY, run:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 3 — Add PostgreSQL on Railway

1. In your Railway project, click **+ New** → **Database** → **PostgreSQL**
2. Railway will automatically inject `DATABASE_URL` into your app

### Step 4 — Deploy

Railway auto-deploys on every `git push` to your connected branch.

---

## 👤 Default Admin Account

On first deploy, the app auto-creates an admin account:

- **Email:** `Innercompassproject25@gmail.com`
- **Password:** `ICP@Admin2025!`

> ⚠️ Change this password immediately after first login via the Admin Panel.

---

## 🔑 Key URLs

| URL            | Description                        |
|----------------|------------------------------------|
| `/`            | Homepage with stats & mood tracker |
| `/signup`      | Member registration                |
| `/login`       | Member login                       |
| `/dashboard`   | Member dashboard (auth required)   |
| `/admin`       | Admin panel (admin role required)  |
| `/resources`   | Public resource hub                |
| `/api/health`  | Health check endpoint              |

---

## 🛠 API Endpoints

| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| POST   | `/api/contact`                    | Submit contact message   |
| POST   | `/api/subscribe`                  | Newsletter subscribe     |
| POST   | `/api/mood`                       | Log a mood entry         |
| GET    | `/api/stats`                      | Get live site stats      |
| POST   | `/api/profile`                    | Update member profile    |
| POST   | `/api/admin/message/<id>/read`    | Mark message as read     |
| POST   | `/api/admin/program`              | Add outreach program     |
| POST   | `/api/admin/user/<id>/role`       | Promote/demote member    |

---

## 💻 Local Development

```bash
# Clone and set up
git clone https://github.com/YOUR_USERNAME/inner-compass-project.git
cd inner-compass-project

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY="dev-secret-key"
export DATABASE_URL="postgresql://localhost/inner_compass"

# Create local database (PostgreSQL must be installed)
createdb inner_compass

# Run the app
python app.py
# Visit http://localhost:5000
```

---

## 📦 Tech Stack

| Layer      | Technology                  |
|------------|-----------------------------|
| Frontend   | HTML5, CSS3, Vanilla JS     |
| Backend    | Python 3 + Flask            |
| Database   | PostgreSQL + SQLAlchemy ORM |
| Auth       | Flask sessions + Bcrypt     |
| Deployment | Railway + GitHub CI         |
| Server     | Gunicorn (2 workers)        |

---

## ✅ Features

- [x] Full member signup & login with password hashing
- [x] Member dashboard with mood tracker, resources, profile
- [x] Admin panel — view messages, manage members, add programs
- [x] Live stats counters (members, programs, students reached)
- [x] Mood tracker — saves to DB, returns personalised response
- [x] Contact form — saves to DB, admin can mark as read
- [x] Newsletter subscription with duplicate detection
- [x] Resource Hub with search & category filters
- [x] Custom 404 page
- [x] Mobile-responsive layout
- [x] Scroll animations & counter animations
- [x] Railway-ready (Procfile + railway.json)

---

*Built for The Inner Compass Project — Find Your True North*
