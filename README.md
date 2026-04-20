# FastAPI Calculator Application

A FastAPI project that includes calculator APIs, calculation persistence (BREAD), and JWT-based registration/login with template-based web pages.

## 1. Overview
This project is a web calculator built with FastAPI.

It includes:
- Template-based web pages (Home/Login/Register/Dashboard)
- REST API endpoints for add, subtract, multiply, and divide
- Input validation and structured error handling
- Logging for successful operations and errors
- User registration and login endpoints
- Calculation CRUD endpoints (BREAD)
- A minimal secure user model (SQLAlchemy + Pydantic)
- A Calculation model + schemas (SQLAlchemy + Pydantic)
- A factory for selecting calculation logic (Add/Sub/Multiply/Divide)
- Password hashing + verification (bcrypt via Passlib)
- Automated testing with unit, integration, and end-to-end tests
- Docker support and GitHub Actions CI/CD

## 2. API Endpoints

### OpenAPI
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### Users
- `POST /users/register`
  - Body (example):
    ```json
    {"username":"alice","email":"alice@example.com","password":"Password123"}
    ```
- `POST /users/login`
  - Body (example):
    ```json
    {"username":"alice","password":"Password123"}
    ```

### JWT Auth
- `POST /auth/register` (used by the web registration page)
- `POST /register` (alias)
  - Body (example):
    ```json
    {"username":"alice","email":"alice@example.com","password":"Password123","confirm_password":"Password123"}
    ```
  - Returns: `{ "access_token": "...", "token_type": "bearer" }`
- `POST /auth/login` (used by the web login page)
- `POST /login` (alias)
  - Body (example):
    ```json
    {"username":"alice@example.com","password":"Password123"}
    ```
  - Returns: `{ "access_token": "...", "token_type": "bearer" }`

### Web Pages
- `GET /` (Home)
- `GET /login`
- `GET /register`
- `GET /dashboard`

### Calculations (BREAD)
- `POST /calculations`
- `GET /calculations`
- `GET /calculations/{id}`
- `PUT /calculations/{id}`
- `DELETE /calculations/{id}`

Example create body:
```json
{"a":10,"b":5,"type":"Add"}
```

### Calculator Operations
- `POST /add`
- `POST /subtract`
- `POST /multiply`
- `POST /divide`

## 3. Project Structure

```text
is601-module13-assignment/
├── app/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt.py
│   │   └── security.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── calculation.py
│   │   └── user.py
│   ├── operations/
│   │   ├── __init__.py
│   │   └── factory.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── calculation.py
│   │   ├── token.py
│   │   └── user.py
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   └── database_init.py
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
├── templates/
│   ├── dashboard.html
│   ├── index.html
│   ├── layout.html
│   ├── login.html
│   └── register.html
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_auth_schema.py
│   │   ├── test_calculator.py
│   │   ├── test_calculation_factory.py
│   │   ├── test_calculation_model.py
│   │   ├── test_calculation_model_errors.py
│   │   ├── test_calculation_schema.py
│   │   ├── test_database.py
│   │   ├── test_database_init.py
│   │   ├── test_jwt_helpers.py
│   │   ├── test_main_api.py
│   │   ├── test_security.py
│   │   ├── test_user_model.py
│   │   └── test_user_schema.py
│   ├── integration/
│   │   ├── conftest.py
│   │   ├── test_calculation_database.py
│   │   ├── test_calculation_routes.py
│   │   ├── test_fastapi_calculator.py
│   │   ├── test_user_database.py
│   │   └── test_user_routes.py
│   └── e2e/
│       ├── conftest.py
│       ├── test_auth_e2e.py
│       ├── test_dashboard_calculation_e2e.py
│       └── test_e2e.py
├── .github/workflows/
│   └── ci.yml
├── main.py
├── pytest.ini
├── requirements.txt
├── Dockerfile
├── compose.yaml
└── README.md
```

## 4. Prerequisites
- Python 3.10 to 3.12 recommended
- Docker Desktop

## 5. Run Locally (PowerShell)

### Set up environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install
```

### Start application

```powershell
uvicorn main:app --reload
```

### Open in browser
- http://127.0.0.1:8000

## 6. Run with Docker

### Build and start

```powershell
docker compose up --build
```

### Open in browser
- http://127.0.0.1:8000

### Stop containers

```powershell
docker compose down
```

## 7. Run Tests Locally
All commands below assume your virtual environment is activated.

### Unit tests
```powershell
python -m pytest tests\unit -q
```

### Integration tests (requires a real Postgres database)
Integration tests require `DATABASE_URL` and an accessible Postgres instance.

Example:
```powershell
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/myappdb"
python -m pytest tests\integration -q
```

Note: if `DATABASE_URL` is not set, integration tests are skipped.

If you want a quick local Postgres for integration tests:
```powershell
docker compose up -d db
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/fastapi_db"
python -m pytest tests\integration -q
docker compose down
```

### End-to-end (E2E) tests
```powershell
python -m pytest tests\e2e -q
```

## 8. CI/CD
- GitHub Actions runs the pipeline on push and pull request events for main.
- Stages: test, security scan, and deploy.
- On successful deploy from main, a new Docker image is pushed to Docker Hub.

Docker Hub repository:
- https://hub.docker.com/r/jps92/is601-module13-assignment