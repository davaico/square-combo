from enum import Enum

from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from adapters.combo.client import ComboClient
from adapters.square.client import SquareClient
from database.database import get_db
from services.client_service import ClientService
from services.setup_service import SetupService

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class SetupStatusEnum(str, Enum):
    SQUARE_AUTH_ERROR = "SQUARE_AUTH_ERROR"
    MISSING_COMBO_API_KEY = "MISSING_COMBO_API_KEY"
    COMBO_API_KEY_INVALID = "COMBO_API_KEY_INVALID"
    SETUP_COMPLETED = "SETUP_COMPLETED"

def get_setup_service(db: Session = Depends(get_db)):
    return SetupService(db)

def get_client_service(db: Session = Depends(get_db)):
    return ClientService(db)

def get_setup_status_script(status: SetupStatusEnum, client_id: int = None) -> str:
    match status:
        case SetupStatusEnum.SQUARE_AUTH_ERROR:
            return f"""
                <script>
                    window.opener.postMessage({{type: "SQUARE_AUTH_ERROR"}}, "*");
                    window.close();
                </script>
                """
        case SetupStatusEnum.MISSING_COMBO_API_KEY:
            return f"""
                <script>
                    window.opener.postMessage({{type: "MISSING_COMBO_API_KEY", client_id: "{client_id}"}}, "*");
                    window.close();
                </script>
                """
        case SetupStatusEnum.COMBO_API_KEY_INVALID:
            return f"""
                <script>
                    window.opener.postMessage({{type: "COMBO_API_KEY_INVALID", client_id: "{client_id}"}}, "*");
                    window.close();
                </script>
                """
        case SetupStatusEnum.SETUP_COMPLETED:
            return f"""
                <script>
                    window.opener.postMessage({{type: "SETUP_COMPLETED"}}, "*");
                    window.close();
                </script>
                """
        case _: return ""


@router.get("/")
async def default(request: Request):
    setup_service = SetupService(db=get_db())
    square_auth_url = setup_service.get_square_authentication_url()
    return templates.TemplateResponse("template.html", {"request": request, "square_auth_url": square_auth_url})


@router.get("/square-auth/callback")
async def square_auth_callback(request: Request,
                               setup_service: SetupService = Depends(get_setup_service),
                               client_service: ClientService = Depends(get_client_service)):
    obtain_token = await setup_service.obtain_square_access_token(request.query_params.get("code"))
    if not obtain_token:
        return HTMLResponse(content=get_setup_status_script(SetupStatusEnum.SQUARE_AUTH_ERROR))

    # if client does not exist in db, create new
    client = client_service.get_client_by_merchant_id(obtain_token.get("merchant_id"))
    if not client:
        # call square api to get merchant details
        square_client: SquareClient = SquareClient(access_token=obtain_token.get("access_token"))
        merchant_data = await square_client.get_merchant_by_id(obtain_token.get("merchant_id"))
        new_client = {
            "name": merchant_data["business_name"],
            "square_access_token": obtain_token.get("access_token"),
            "square_merchant_id": obtain_token.get("merchant_id"),
            "square_refresh_token": obtain_token.get("refresh_token"),
            "square_access_token_expiry_date": obtain_token.get("expires_at"),
        }
        response = client_service.create_client(new_client)
        return HTMLResponse(content=get_setup_status_script(SetupStatusEnum.MISSING_COMBO_API_KEY, response.id))

    if not client.combo_api_key:
        return HTMLResponse(content=get_setup_status_script(SetupStatusEnum.MISSING_COMBO_API_KEY, client.id))

    return HTMLResponse(content=get_setup_status_script(SetupStatusEnum.SETUP_COMPLETED))


@router.post("/")
async def submit_combo_api_key_request(request: Request,
                                       client_id: int = Form(...),
                                       api_key: str = Form(...),
                                       client_service: ClientService = Depends(get_client_service)):
    combo_client: ComboClient = ComboClient(
        api_key=api_key,
    )
    try:
        locations = await combo_client.get_locations()
    except Exception as e:
        return HTMLResponse(content=get_setup_status_script(SetupStatusEnum.COMBO_API_KEY_INVALID, client_id))

    update_fields = {
        "combo_api_key": api_key,
    }
    client_service.update_client(client_id, update_fields)
    return HTMLResponse(content=get_setup_status_script(SetupStatusEnum.SETUP_COMPLETED))


