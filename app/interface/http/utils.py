from jwt import encode
from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.application.ports.presenters import Presenter, State
from app.config.config import settings

def create_access_token(data: dict, expires_delta: timedelta|None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=settings.JWT_TOKEN_EXPIRY_TIME))
    to_encode.update({"exp": expire})
    return encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def raise_for_presenter_400_state(p: Presenter):
    if not isinstance(p.response, str):
          raise ValueError("Wrong type for presenter response. str expected.") 
    match p.state:
        case State.UNAUTHORIZED:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=p.response, headers={"WWW-Authenticate": "Bearer"})
        case State.FORBIDDEN:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=p.response)
        case State.CONFLICT:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=p.response)
        case State.ERROR:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=p.response)