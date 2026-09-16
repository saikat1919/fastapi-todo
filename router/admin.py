from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Annotated
from database import SessionLocal
from sqlalchemy.orm import Session
from models import Todos
from router.auth import decode_token_to_get_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(decode_token_to_get_user)]

@router.get("/admin/todos")
def read_all_todos(user: user_dependency, db: db_dependency):
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Failed Authentication")

    return db.query(Todos).all()

@router.get("/admin/todos/delete/{todo_id}")
def delete_any_todo(user: user_dependency, todo_id: int, db: db_dependency):
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Failed Authentication")
    specific_todo = (db.query(Todos)
                     .filter(Todos.id == todo_id).first())
    if specific_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    # ORM delete: honors relationship cascades and before/after_delete events, and keeps
    # the session in sync — but needs the object loaded first, so SELECT + DELETE. Use when
    # the row is already fetched, or when Todos has ORM-cascaded children.
    db.delete(specific_todo)

    # Bulk delete: one statement, no fetch needed, returns a rowcount you can 404 on — but
    # it bypasses ORM cascades and events and leaves stale objects in the identity map.
    # Use only when you skip the SELECT entirely and cascades are handled at the DB level.
    # (db.query(Todos)
    #  .filter(Todos.owner_id == user.get("id"))
    #  .filter(Todos.id == todo_id).delete())
    db.commit()
    return JSONResponse(status_code=200, content={"message": "Todo deleted successfully"})