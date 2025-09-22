from typing import NoReturn

from fastapi import HTTPException, status

from app.application.ports.presenters import Presenter, State


def raise_for_presenter_400_state(p: Presenter) -> NoReturn:
    if not isinstance(p.response, str):
        raise ValueError("Wrong type for presenter response. str expected.")
    match p.state:
        case State.UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=p.response,
                headers={"WWW-Authenticate": "Bearer"},
            )
        case State.FORBIDDEN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=p.response
            )
        case State.CONFLICT:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=p.response)
        case State.ERROR:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=p.response
            )

    raise ValueError("Wrong presenter state")
