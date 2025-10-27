from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from dependencies import get_current_user
from models import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="認証が必要です")
    
    return templates.TemplateResponse(
        "account.html",
        {"request": request, "user": current_user}
    )