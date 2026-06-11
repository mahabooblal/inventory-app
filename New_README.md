<<<<<<< HEAD
# Flask Inventory Management System

A production-ready inventory management system built with Flask, PostgreSQL, and Bootstrap.

## Feature Highlights

- Role-based authentication for admin, manager, and staff users
- Product, category, supplier, and customer management
- Stock-in workflow with product quantity updates
- Sales tracking with automatic inventory deduction
- Low-stock alerts and dashboard attention banner
- Reorder suggestions based on recent sales velocity
- Profit and loss reporting
- Inventory, low-stock, product, category, and customer sales reports
- CSV and PDF report exports
- Activity audit log for important user actions
- In-app notifications with unread counts
- Chart.js analytics dashboard
- Alembic-ready database migrations through Flask-Migrate
- Optional Sentry error tracking and public health check endpoint

## Tech Stack

| Layer      | Technology                                     |
| ---------- | ---------------------------------------------- |
| Backend    | Python 3.12 / Flask 3.0                        |
| ORM        | SQLAlchemy + Flask-Migrate (Alembic)           |
| Database   | PostgreSQL (production) / SQLite (development) |
| Auth       | Flask-Login + Werkzeug password hashing        |
| Forms      | Flask-WTF + WTForms with CSRF protection       |
| PDF Export | ReportLab                                      |
| Email      | Flask-Mail                                     |
| Frontend   | Bootstrap + Chart.js                           |
| Deployment | Gunicorn + Render                              |

## Architecture Overview

The app uses Flask's application factory pattern, with each product domain split into its own blueprint under `app/routes/`. Business logic that belongs outside request handlers lives in `app/services/`, while SQLAlchemy models live in `app/models/`. Configuration is environment-aware, with development, production, and testing classes in `config.py`.

## Quick Start

```bash
git clone <repo-url>
cd Inventory_app
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
flask db upgrade
flask run
```

Set `ADMIN_PASSWORD` in `.env` before first run if you want the development admin user created automatically.

## Environment Variables

| Variable               | Required   | Description                                                    |
| ---------------------- | ---------- | -------------------------------------------------------------- |
| `SECRET_KEY`           | Production | Flask session and CSRF signing key                             |
| `DATABASE_URL`         | Production | PostgreSQL connection URL; SQLite is used locally when omitted |
| `DATABASE_SSL_REQUIRE` | Optional   | Adds `sslmode=require` to PostgreSQL URLs by default           |
| `ADMIN_USERNAME`       | Optional   | Default admin username                                         |
| `ADMIN_EMAIL`          | Optional   | Default admin email                                            |
| `ADMIN_PASSWORD`       | Optional   | Default admin password for local bootstrap                     |
| `MAIL_SERVER`          | Optional   | SMTP host                                                      |
| `MAIL_PORT`            | Optional   | SMTP port                                                      |
| `MAIL_USE_TLS`         | Optional   | Enable SMTP TLS                                                |
| `MAIL_USERNAME`        | Optional   | SMTP username                                                  |
| `MAIL_PASSWORD`        | Optional   | SMTP password                                                  |
| `MAIL_DEFAULT_SENDER`  | Optional   | Sender address for email alerts                                |
| `SENTRY_DSN`           | Optional   | Enables Sentry Flask and SQLAlchemy integrations               |

## Running Tests

Run the suite with pytest:

```bash
pytest tests/ -v
```

Run tests with coverage reporting:

```bash
pytest --cov=app --cov-report=term-missing tests/
```

Use the GitHub Actions workflow on push in `.github/workflows/pytest.yml`.

## Deployment

See `DEPLOYMENT.md` for full deployment details. For Render, provision PostgreSQL, set the environment variables above, run `flask db upgrade`, and start with Gunicorn.

## Project Structure

```text
app/
├── forms/
├── models/
├── routes/
├── services/
├── static/
│   ├── css/
│   └── js/
├── templates/
│   ├── admin/
│   ├── auth/
│   ├── products/
│   ├── reports/
│   └── sales/
└── utils/
```

## License

MIT
=======
# Inventory Web App

A monolithic web application for managing inventory stock — tracking incoming stock, sales, and generating date-range reports via server-rendered HTML pages. It allows users to:

- Register **incoming stock** (purchase/receive items)
- Register **outgoing stock** (sell/dispatch items)
- View **inventory levels** in real time
- Generate **reports** filtered by a date range

---

## Architecture

The application follows a classic **monolithic MVT architecture** (Model–View–Template) where Django handles routing, business logic, database access, and HTML rendering in a single deployable unit.

---

## Features

| Feature | Description |
|---|---|
| Incoming Stock | Record new stock arrivals with quantity, date, and supplier |
| Outgoing Stock | Record sales or dispatches with quantity, date, and customer |
| Inventory Dashboard | View current stock levels for all products |
| Date-Range Report | Generate stock movement reports between a from-date and to-date |
| Server-Rendered Pages | All pages are rendered on the server and returned as HTML |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Web Framework | Django 5.x |
| Template Engine | Django Templates (DTL) |
| Database | PostgreSQL / MySQL / SQLite |
| ORM | Django ORM (built-in) |
| Styling | Bootstrap 5 |

---


>>>>>>> 4394eb2f4f29ac52523e4712d2800fea18f5c8d5
