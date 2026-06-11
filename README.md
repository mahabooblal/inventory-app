# Inventory Management System

A comprehensive Inventory Management System built using Flask, SQLAlchemy, and Bootstrap. This application helps businesses manage products, inventory, suppliers, customers, warehouses, sales, purchases, and reports through a user-friendly web interface.

## Features

### User Management

* Secure user authentication and authorization
* Role-based access control (Admin, Manager, Staff)
* User profile management
* Activity tracking and audit logs

### Inventory Management

* Product catalog management
* Stock tracking and monitoring
* Inventory adjustments
* Stock movement history
* Warehouse-wise inventory tracking

### Sales Management

* Sales order processing
* Invoice generation
* Customer management
* Payment tracking
* Sales history reports

### Purchase Management

* Purchase order management
* Supplier management
* Goods receipt tracking
* Purchase history records

### Warehouse Management

* Multiple warehouse support
* Stock transfers between warehouses
* Warehouse inventory reports
* Stock reconciliation

### Reporting & Analytics

* Inventory reports
* Sales reports
* Purchase reports
* Stock movement reports
* Dashboard analytics

### Additional Features

* Notification system
* Audit logging
* Backup and recovery support
* API integration support
* Responsive user interface

---

## Technology Stack

### Backend

* Python 3
* Flask
* SQLAlchemy
* Flask-Login
* Werkzeug

### Database

* SQLite (Development)
* PostgreSQL (Production Recommended)

### Frontend

* HTML5
* CSS3
* Bootstrap
* JavaScript

### Deployment

* Gunicorn
* Render
* Railway
* Docker

---

## Project Structure

```text
inventory-app/
│
├── app/
│   ├── models/
│   ├── routes/
│   ├── templates/
│   ├── static/
│   └── utils/
│
├── migrations/
├── tests/
├── scripts/
├── app.py
├── config.py
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/mahabooblal/inventory-app.git
cd inventory-app
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

Linux / Mac:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Configuration

Create a `.env` file in the project root.

```env
SECRET_KEY=change-this-secret-key

DATABASE_URL=sqlite:///app.db

ADMIN_USERNAME=Codeleap
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeThisPassword

MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=
MAIL_PASSWORD=
```

---

## Running the Application

```bash
python app.py
```

Application URL:

```text
http://127.0.0.1:5000
```

---

## Database

Development:

```text
SQLite
```

Production:

```text
PostgreSQL
```

Recommended for deployment on Render.

---

## Deployment on Render

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
gunicorn app:app
```

### Environment Variables

```env
SECRET_KEY=your-secret-key
ADMIN_USERNAME=Codeleap
ADMIN_EMAIL=Codeleap@example.com
ADMIN_PASSWORD=your-password
DATABASE_URL=your-database-url
```

---

## Security Recommendations

* Never commit `.env` files.
* Use strong passwords.
* Use PostgreSQL in production.
* Enable HTTPS.
* Rotate secrets regularly.

---

## Future Enhancements

* Barcode scanning
* QR code integration
* Mobile application
* Advanced analytics
* Email notifications
* Inventory forecasting
* Multi-company support

---

## Author

**Mahaboob Lal**

GitHub Repository:

https://github.com/mahabooblal/inventory-app

---

## License

This project is licensed under the MIT License.

Copyright (c) 2026 Mahaboob Lal

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.
