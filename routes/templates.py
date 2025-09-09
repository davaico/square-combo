from fastapi import APIRouter, Request
from starlette.templating import Jinja2Templates
from services.setup_service import SetupService
from database import database

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def default(request: Request):
    setup_service = SetupService(database.get_db())
    square_auth_url = setup_service.get_square_authentication_url()
    return templates.TemplateResponse("index.html", {"request": request, "square_auth_url": square_auth_url})