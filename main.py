# main.py

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi import Depends, status
from fastapi.responses import JSONResponse
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
from app.schemas.calculation import CalculationCreate, CalculationRead
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

@app.get("/")
async def read_root(request: Request):
    """
    Serve the index.html template.
    """
    logger.info("Serving homepage")
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


# ------------------------------------------------------------------------------
# User Endpoints
# ------------------------------------------------------------------------------

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