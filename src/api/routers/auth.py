from fastapi import APIRouter, Depends

from src.api.deps import CurrentUser, get_current_user
from src.api.models import UserInfo

router = APIRouter()


@router.get("/auth/me", response_model=UserInfo)
def get_me(user: CurrentUser = Depends(get_current_user)):
    return UserInfo(email=user.email, display_name=user.display_name, role=user.role)
