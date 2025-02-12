from datetime import datetime
from typing import Annotated

from fastapi import Depends, APIRouter, Form, HTTPException
from jose import jwt
from passlib.hash import pbkdf2_sha256
from sqlmodel import Session, select
from starlette import status
from starlette.responses import JSONResponse

from .model import EnUser, EnUserDB, EnUserUpdate
from ..constants import token_secret, oauth2_scheme, get_db_session, decode_token

users_router = APIRouter(
    prefix="/users",
    tags=["users"],
)

@users_router.post("/auth/login")
async def user_login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db_session)):
    statement = select(EnUserDB).where(EnUserDB.username == username)
    user_db = db.exec(statement).first()

    if not user_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user_db.verify_password(password):
        user_db.last_login = datetime.now()
        db.add(user_db)
        db.commit()
        db.refresh(user_db)

        token = jwt.encode(user_db.get_token_information(), token_secret, algorithm="HS256")

        return JSONResponse(
            content={
                "message": "User login successful.",
                "user_data": user_db.get_token_information(),
                "access_token": token,
                "token_type": "bearer",
            },
            status_code=status.HTTP_200_OK,
        )
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password incorrect.")


@users_router.post("/auth/register")
async def user_register(user: EnUser = Depends(), db: Session = Depends(get_db_session)):
    # Test against same username
    statement = select(EnUserDB).where(EnUserDB.username == user.username)
    results = db.exec(statement).first()

    if results is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")

    # Test against same mail
    statement = select(EnUserDB).where(EnUserDB.mail == user.mail)
    results = db.exec(statement).first()

    if results is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mail already in use.")

    db_user = EnUserDB(**user.model_dump())
    db_user.username = user.username.lower()
    db_user.password = pbkdf2_sha256.hash(user.password)
    db_user.date_joined = datetime.now()

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    if db_user.id is not None:
        token = jwt.encode(user.get_token_information(), token_secret, algorithm="HS256")

        return JSONResponse(
            content={
                "message": "User created.",
                "user_data": user.get_token_information(),
                "access_token": token,
                "token_type": "bearer",
            },
            status_code=status.HTTP_200_OK
        )
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User registration failed.")


@users_router.get("/read", response_model=EnUser)
async def user_read(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db_session)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    else:
        token_data = decode_token(token)

    user = db.get(EnUserDB, token_data["id"])

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    else:
        return user


@users_router.patch("/update", response_model=EnUser)
async def update_user(token: Annotated[str, Depends(oauth2_scheme)], user: EnUserUpdate, db: Session = Depends(get_db_session)):
    token_data = decode_token(token)

    user_db = db.get(EnUserDB, token_data["id"]) # TODO: NICE!

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    for field, value in user.model_dict().items():
        print(field,":", value)
        setattr(user_db, field, value)

    db.commit()
    db.refresh(user_db)

    return user_db


@users_router.delete("/delete", response_model=EnUser)
async def delete_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db_session)):
    token_data = decode_token(token)

    if not "id" in token_data:
        statement = select(EnUserDB).where(EnUserDB.username == token_data["username"])
        user = db.exec(statement).first()
    else:
        user = db.get(EnUser, token_data["id"])

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    db.delete(user)
    db.commit()

    return JSONResponse(
        content={
            "message": "User was successfully deleted.",
            "user_data": user.get_token_information(),
            "token": token,
            "token_type": "bearer",
        },
        status_code=status.HTTP_200_OK
    )
