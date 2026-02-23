from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_302_FOUND

from app.services.auth import AuthService, User
from app.services.contracts import ContractService


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Finance Chatbot Demo")
app.add_middleware(SessionMiddleware, secret_key="dev-secret-change-me")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
contract_service = ContractService()


def get_session_user(request: Request) -> Optional[User]:
    username = request.session.get("username")
    role = request.session.get("role")
    if username and role:
        return User(username=username, role=role)
    return None


def can_access_contracts(request: Request, token: Optional[str]) -> bool:
    user = get_session_user(request)
    if user is None:
        return AuthService.is_valid_contractor_token(token)
    if user.role in {"analyst", "contractor"}:
        return True
    return False


@app.get("/")
def home() -> RedirectResponse:
    return RedirectResponse(url="/contracts", status_code=HTTP_302_FOUND)


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "user": get_session_user(request),
            "error": None,
        },
    )


@app.post("/login")
def login(
    request: Request,
    role: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
):
    user: Optional[User] = None
    if role == "analyst":
        user = AuthService.authenticate_analyst(username=username, password=password)
    elif role == "contractor":
        user = AuthService.authenticate_contractor(username=username, code=password)

    if user is None:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "user": get_session_user(request),
                "error": "Invalid credentials.",
            },
            status_code=400,
        )

    request.session["username"] = user.username
    request.session["role"] = user.role
    return RedirectResponse(url="/contracts", status_code=HTTP_302_FOUND)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)


@app.get("/contracts")
def contracts_page(request: Request, token: Optional[str] = None):
    user = get_session_user(request)
    if not can_access_contracts(request, token):
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)

    return templates.TemplateResponse(
        "contracts.html",
        {
            "request": request,
            "user": user,
            "contracts": contract_service.list_contracts(),
            "used_token": bool(token),
        },
    )


@app.post("/contracts")
def create_contract(
    request: Request,
    contractor_name: str = Form(...),
    contract_value: str = Form(...),
    notes: str = Form(""),
    token: Optional[str] = Form(None),
):
    if not can_access_contracts(request, token):
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)

    contract_service.add_contract(
        contractor_name=contractor_name,
        contract_value=contract_value,
        notes=notes,
    )

    next_url = "/contracts"
    if token:
        next_url = f"/contracts?token={token}"
    return RedirectResponse(url=next_url, status_code=HTTP_302_FOUND)


@app.get("/assistant")
def assistant_page(request: Request):
    user = get_session_user(request)
    if user is None or user.role != "analyst":
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)

    return templates.TemplateResponse(
        "assistant.html",
        {
            "request": request,
            "user": user,
        },
    )
