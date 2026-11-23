# LOANER – Multi-Shop Pawn Management System

LOANER is a Django REST Framework-based backend application designed to simplify pawn shop operations. It helps shop owners manage multiple shops, customers, loans, gold items, payments, settlements, and excess interest credits through a centralized system.

## Project Overview

LOANER is designed around a multi-shop architecture where a single owner can manage multiple pawn shops using one account. The backend applies owner-based and shop-based access control to keep shop data separated.

## Key Features

### 1. Authentication
- User registration and login
- JWT-based authentication
- Protected API endpoints

### 2. Shop Management
- Manage multiple shops under one owner
- Shop-specific data management
- Shop settings

### 3. Customer Management
- Create and view customer records
- Retrieve and update customer details
- Activate and deactivate customers
- Customer information management

### 4. Loan Management
- Create and manage pawn loans
- Track principal amounts and interest rates
- Manage loan dates and due dates
- Retrieve loan details and update loan information
- Shop-specific loan access

### 5. Gold Item Management
- Store gold item details against loans
- Track gross weight, net weight, and purity
- Update gold item information

### 6. Payment Management
- Record loan payments
- Maintain payment history
- Track principal and interest payments
- Generate PDF payment receipts

### 7. Loan Settlement
- Calculate outstanding principal and interest
- Track advance interest credits
- Calculate settlement amounts
- Support loan closure based on settlement conditions

### 8. Excess Interest Credit Management
- Record excess interest as customer credit
- Track available credit balance
- Maintain credit transaction history
- Support credit adjustments and refunds
- Require customer confirmation for adjustments and refunds

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Django | Backend framework |
| Django REST Framework | REST API development |
| MySQL | Database |
| Simple JWT | Authentication |
| drf-spectacular | API schema and documentation |
| ReportLab | PDF receipt generation |
| Git & GitHub | Version control |

## Project Structure

```text
LOANER/
│
├── accounts/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── tests.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Mkirubakar11/LOANER.git
cd LOANER
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows (Git Bash):**
```bash
source venv/Scripts/activate
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the backend root directory and configure the environment variables required by `config/settings.py`.

Do not commit `.env` or expose database passwords and Django secret keys.

### 5. Run database migrations

```bash
python manage.py migrate
```

### 6. Start the development server

```bash
python manage.py runserver
```

The backend will be available at:

`http://127.0.0.1:8000/`

## API Documentation

Interactive API documentation is available through Swagger UI.

- **Swagger UI:** http://127.0.0.1:8000/api/docs/
- **OpenAPI Schema:** http://127.0.0.1:8000/api/schema/
- **ReDoc:** http://127.0.0.1:8000/api/redoc/

Use the documentation to explore and test the available API endpoints.

## Running Tests

Run the automated test suite:

```bash
python manage.py test --verbosity 1
```

**Current test status:**
- 35 automated tests passed.
- Django system check completed without issues.
- Migration check completed with no model changes detected.

## Security and Data Access

- JWT authentication for protected endpoints.
- Owner-based access control.
- Shop-level data isolation.
- Environment-based secret and database configuration.
- Transaction-based handling of important financial operations.

## Current Project Status

The Django REST Framework backend has implemented core pawn shop management modules and passed its current automated test suite.

Frontend development, production deployment, and additional future enhancements are not included in the current implementation.

## Future Enhancements

- React + Vite frontend
- Advanced dashboard and analytics
- Multilingual interface (Tamil, English, and Tanglish)
- AI-powered search and assistance
- Production deployment and monitoring

## Author

**Kirubakar**

GitHub: https://github.com/Mkirubakar11

---

*LOANER – Simplifying Pawn Shop Management Through Technology.*