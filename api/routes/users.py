# api/routes/users.py
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from api.models.schemas import UsersResponse, UserInfo

router = APIRouter()

DATA_USERS_DIR = Path("data/users")


@router.get("/users", response_model=UsersResponse)
async def list_users() -> UsersResponse:
    if not DATA_USERS_DIR.exists():
        return UsersResponse(users=[])

    users = []
    for user_dir in DATA_USERS_DIR.iterdir():
        if not user_dir.is_dir():
            continue
        photo_count = sum(1 for p in user_dir.iterdir() if p.is_file())
        users.append(UserInfo(user_id=user_dir.name, photo_count=photo_count))

    return UsersResponse(users=users)
