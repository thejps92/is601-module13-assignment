# main.py

from contextlib import asynccontextmanager
import re
from uuid import UUID
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi import Depends, status
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator  # Use @validator for Pydantic 1.x
from fastapi.exceptions import RequestValidationError
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.database_init import init_db
from app.models.calculation import Calculation
from app.models.user import User
from app.auth.jwt import create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.calculation import CalculationCreate, CalculationRead
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.operations import add, subtract, multiply, divide  # Ensure correct import path
import uvicorn
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

# Mount the static files directory (required by templates/layout.html)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates directory
templates = Jinja2Templates(directory="templates")

# Pydantic model for request data
class OperationRequest(BaseModel):
    a: float = Field(..., description="The first number")
    b: float = Field(..., description="The second number")

    @field_validator("a", "b", mode="before")
    def validate_numbers(cls, value):
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass
        raise ValueError("Both a and b must be numbers.")

# Pydantic model for successful response
class OperationResponse(BaseModel):
    result: float = Field(..., description="The result of the operation")

# Pydantic model for error response
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")

# Custom Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException on {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Extracting error messages
    error_messages = "; ".join([f"{err['loc'][-1]}: {err['msg']}" for err in exc.errors()])
    logger.error(f"ValidationError on {request.url.path}: {error_messages}")
    return JSONResponse(
        status_code=400,
        content={"error": error_messages},
    )

@app.get("/", response_class=HTMLResponse, tags=["web"], name="read_index")
async def read_root(request: Request):
    """
    Serve the index.html template.
    """
    logger.info("Serving homepage")
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse, tags=["web"])
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse, tags=["web"])
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse, tags=["web"])
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


# ------------------------------------------------------------------------------
# User Endpoints
# ------------------------------------------------------------------------------


_USERNAME_SAFE_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _derive_unique_username(email: str, db: Session) -> str:
    local_part = email.split("@", 1)[0]
    base = _USERNAME_SAFE_RE.sub("_", local_part).strip("_")
    if not base:
        base = "user"

    # Keep room for suffix to avoid exceeding the DB column limit (50).
    base = base[:40]
    candidate = base

    counter = 0
    while db.query(User).filter(User.username == candidate).first() is not None:
        counter += 1
        suffix = f"_{counter}"
        candidate = f"{base[:50 - len(suffix)]}{suffix}"

        # Safety fallback in pathological cases.
        if counter > 9999:
            rand = uuid4().hex[:6]
            suffix = f"_{rand}"
            candidate = f"{base[:50 - len(suffix)]}{suffix}"
            break

    return candidate


@app.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
@app.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
def register_jwt(payload: RegisterRequest, db: Session = Depends(get_db)):
    # Duplicate email check
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    requested_username = (payload.username or "").strip() or None
    if requested_username is not None:
        if db.query(User).filter(User.username == requested_username).first() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )
        username = requested_username
    else:
        username = _derive_unique_username(payload.email, db)
    user = User.create(username=username, email=payload.email, password=payload.password)
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists",
        )

    db.refresh(user)

    access_token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=access_token)


@app.post(
    "/login",
    response_model=TokenResponse,
    tags=["auth"],
)
@app.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["auth"],
)
def login_jwt(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(or_(User.username == payload.username, User.email == payload.username))
        .first()
    )

    if user is None or not user.verify(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=access_token)

@app.post(
    "/users/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    tags=["users"],
)
def register_user(user_create: UserCreate, db: Session = Depends(get_db)):
    user = User.create(
        username=user_create.username,
        email=user_create.email,
        password=user_create.password,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists",
        )
    db.refresh(user)
    return user


@app.post(
    "/users/login",
    response_model=UserRead,
    tags=["users"],
)
def login_user(user_login: UserLogin, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(or_(User.username == user_login.username, User.email == user_login.username))
        .first()
    )
    if user is None or not user.verify(user_login.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ------------------------------------------------------------------------------
# Calculation Endpoints (BREAD)
# ------------------------------------------------------------------------------

@app.post(
    "/calculations",
    response_model=CalculationRead,
    status_code=status.HTTP_201_CREATED,
    tags=["calculations"],
)
def create_calculation(calculation_create: CalculationCreate, db: Session = Depends(get_db)):
    calculation = Calculation.create(
        a=calculation_create.a,
        b=calculation_create.b,
        type=calculation_create.type,
    )
    db.add(calculation)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc.orig) if getattr(exc, "orig", None) else "Invalid calculation",
        )
    db.refresh(calculation)
    return calculation


@app.get(
    "/calculations",
    response_model=list[CalculationRead],
    tags=["calculations"],
)
def list_calculations(db: Session = Depends(get_db)):
    return db.query(Calculation).all()


@app.get(
    "/calculations/{calc_id}",
    response_model=CalculationRead,
    tags=["calculations"],
)
def get_calculation(calc_id: str, db: Session = Depends(get_db)):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid calculation id format",
        )

    calculation = db.query(Calculation).filter(Calculation.id == calc_uuid).first()
    if calculation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calculation not found")
    return calculation


@app.put(
    "/calculations/{calc_id}",
    response_model=CalculationRead,
    tags=["calculations"],
)
def update_calculation(
    calc_id: str,
    calculation_update: CalculationCreate,
    db: Session = Depends(get_db),
):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid calculation id format",
        )

    calculation = db.query(Calculation).filter(Calculation.id == calc_uuid).first()
    if calculation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calculation not found")

    calculation.a = calculation_update.a
    calculation.b = calculation_update.b
    calculation.type = calculation_update.type
    calculation.result = calculation.compute_result()

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc.orig) if getattr(exc, "orig", None) else "Invalid calculation",
        )
    db.refresh(calculation)
    return calculation


@app.delete(
    "/calculations/{calc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["calculations"],
)
def delete_calculation(calc_id: str, db: Session = Depends(get_db)):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid calculation id format",
        )

    calculation = db.query(Calculation).filter(Calculation.id == calc_uuid).first()
    if calculation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calculation not found")

    db.delete(calculation)
    db.commit()
    return None

@app.post("/add", response_model=OperationResponse, responses={400: {"model": ErrorResponse}})
async def add_route(operation: OperationRequest):
    """
    Add two numbers.
    """
    try:
        result = add(operation.a, operation.b)
        logger.info("Add operation completed: a=%s b=%s result=%s", operation.a, operation.b, result)
        return OperationResponse(result=result)
    except Exception as e:
        logger.error(f"Add Operation Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/subtract", response_model=OperationResponse, responses={400: {"model": ErrorResponse}})
async def subtract_route(operation: OperationRequest):
    """
    Subtract two numbers.
    """
    try:
        result = subtract(operation.a, operation.b)
        logger.info("Subtract operation completed: a=%s b=%s result=%s", operation.a, operation.b, result)
        return OperationResponse(result=result)
    except Exception as e:
        logger.error(f"Subtract Operation Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/multiply", response_model=OperationResponse, responses={400: {"model": ErrorResponse}})
async def multiply_route(operation: OperationRequest):
    """
    Multiply two numbers.
    """
    try:
        result = multiply(operation.a, operation.b)
        logger.info("Multiply operation completed: a=%s b=%s result=%s", operation.a, operation.b, result)
        return OperationResponse(result=result)
    except Exception as e:
        logger.error(f"Multiply Operation Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/divide", response_model=OperationResponse, responses={400: {"model": ErrorResponse}})
async def divide_route(operation: OperationRequest):
    """
    Divide two numbers.
    """
    try:
        result = divide(operation.a, operation.b)
        logger.info("Divide operation completed: a=%s b=%s result=%s", operation.a, operation.b, result)
        return OperationResponse(result=result)
    except ValueError as e:
        logger.error(f"Divide Operation Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Divide Operation Internal Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":  # pragma: no cover
    uvicorn.run(app, host="127.0.0.1", port=8000)