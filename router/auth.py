from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, Field
from typing import Annotated, Optional
from starlette import status
from passlib.context import CryptContext
from database import SessionLocal
from sqlalchemy.orm import Session
from models import Users
from jose import jwt, JWTError
from datetime import timedelta, datetime, timezone



router = APIRouter()

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = "1f5addbb2c42310e424a1d515e7da5a8a731249bd3728fa449078df86d41aa69"
ALGORITHM = "HS256"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

class CreateUsers(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str
    phone_number: str

class UpdateUserInfo(BaseModel):
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)

class UpdatePassword(BaseModel):
    current_password: str
    new_password: str

def authenticate_user(username, password, db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if bcrypt_context.verify(password, user.password):
        return user
    return False

def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {"sub": username, "id": user_id, "role": role}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token_to_get_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        role: str = payload.get("role")

        if username is None or user_id is None:
            raise HTTPException(status_code=404, detail="User not found")

        return {"username": username, "id": user_id, "role": role}
    except:
        raise JWTError

user_dependency = Annotated[dict, Depends(decode_token_to_get_user)]

@router.post("/createuser")
def create_user(db: db_dependency, new_user: CreateUsers):
    user_model = Users(
        username=new_user.username,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        password=bcrypt_context.hash(new_user.password),
        is_active=True,
        role=new_user.role,
        phone_number=new_user.phone_number
    )

    db.add(user_model)
    db.commit()
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "User created successfully"})

@router.post("/login")
def login_user(db: db_dependency, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(status_code=401, detail="Failed Authentication")

    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=30))
    return {"access_token": token, "token_type": "bearer"}

@router.put("/user/edit")
def edit_user(user: user_dependency, db: db_dependency, update_user_info: UpdateUserInfo):
    if not user:
        raise HTTPException(status_code=401, detail="Failed Authentication")

    get_user_info = db.query(Users).filter(Users.id == user.get("id")).first()

    update_user = update_user_info.model_dump(exclude_unset=True)

    for key, value in update_user.items():
        setattr(get_user_info, key, value)

    db.commit()

    return JSONResponse(status_code=200, content={"message": "User Updated successfully"})

@router.put("/user/change/password")
def change_password(user: user_dependency, db: db_dependency, update_password: UpdatePassword):
    if not user:
        raise HTTPException(status_code=401, detail="Failed Authentication")

    user = db.query(Users).filter(Users.id == user.get("id")).first()

    is_same = bcrypt_context.verify(update_password.current_password, user.password)

    if not is_same:
        raise HTTPException(status_code=401, detail="Password Mismatch")

    user.password = bcrypt_context.hash(update_password.new_password)

    db.commit()

    return JSONResponse(status_code=200, content={"message": "Password Updated successfully"})