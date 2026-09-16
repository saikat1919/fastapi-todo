from fastapi import FastAPI, Depends, HTTPException
from models import Todos, Users
from fastapi.responses import JSONResponse
import models
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from database import engine, SessionLocal
from router import auth, admin
from router.auth import decode_token_to_get_user


app = FastAPI()

models.Base.metadata.create_all(bind=engine)
app.include_router(auth.router)
app.include_router(admin.router)

class Todo(BaseModel):
    title: str
    description: str = Field(max_length=255)
    priority: int = Field(gt=0, lt=6)
    completed: bool = Field(default=False)

class UpdateTodo(BaseModel):
    # id: Optional[int] = Field(default=None)
    title: Optional[str] = Field(default=None)
    description: Optional[str] = Field(max_length=255, default=None)
    priority: Optional[int] = Field(gt=0, lt=6, default=None)
    completed: Optional[bool] = Field(default=None)

class UpdateUserInfo(BaseModel):
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(decode_token_to_get_user)]

@app.get("/todos")
def read_todos(user: user_dependency, db: db_dependency):
    if not user:
        raise HTTPException(status_code=401, detail="Failed Authentication")

    return db.query(Todos).filter(Todos.owner_id == user.get("id")).all()

@app.get("/todos/{todo_id}")
def read_specific_todo(user: user_dependency, todo_id: int, db: db_dependency):
    if not user:
        raise HTTPException(status_code=404, detail="Failed Authentication")
    specific_todo = db.query(Todos).filter(Todos.owner_id == user.get("id")).filter(Todos.id == todo_id).first()
    if specific_todo:
        return specific_todo
    else:
        raise HTTPException(status_code=404, detail="Todo not found")

@app.post("/todos/create")
def create_todo(user: user_dependency, db: db_dependency, new_todo: Todo):
    if not user:
        raise HTTPException(status_code=401, detail="Failed Authentication")
    todo_model = Todos(**new_todo.model_dump(), owner_id=user.get("id"))
    db.add(todo_model)
    db.commit()
    return JSONResponse(status_code=201, content={"message": "Todo created successfully"})

@app.put("/todos/edit/{todo_id}")
def edit_todos(user: user_dependency, todo_id: int, db: db_dependency, update_todo: UpdateTodo ):
    if not user:
        raise HTTPException(status_code=401, detail="Failed Authentication")

    specific_todo = (db.query(Todos)
                     .filter(Todos.owner_id == user.get("id"))
                     .filter(Todos.id == todo_id).first())
    if specific_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    update_data = update_todo.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(specific_todo, key, value)

    db.commit()
    return JSONResponse(status_code=200, content={"message": "Todo Updated successfully"})

@app.delete("/todos/delete/{todo_id}")
def delete_todo(user: user_dependency, todo_id: int, db: db_dependency):
    if not user:
        raise HTTPException(status_code=401, detail="Failed Authentication")
    specific_todo = (db.query(Todos)
                     .filter(Todos.owner_id == user.get("id"))
                     .filter(Todos.id == todo_id).first())
    if specific_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    # ORM delete: honors relationship cascades and before/after_delete events, and keeps
    # the session in sync — but needs the object loaded first, so SELECT + DELETE. Use when
    # the row is already fetched, or when Todos has ORM-cascaded children.
    # db.delete(specific_todo)

    # Bulk delete: one statement, no fetch needed, returns a rowcount you can 404 on — but
    # it bypasses ORM cascades and events and leaves stale objects in the identity map.
    # Use only when you skip the SELECT entirely and cascades are handled at the DB level.
    (db.query(Todos)
     .filter(Todos.owner_id == user.get("id"))
     .filter(Todos.id == todo_id).delete())
    db.commit()
    return JSONResponse(status_code=200, content={"message": "Todo deleted successfully"})

@app.get("/user")
def get_user(user: user_dependency, db: db_dependency):
    if not user:
        raise HTTPException(status_code=401, detail="Failed Authentication")

    return db.query(Users).filter(Users.id == user.get("id")).first()
