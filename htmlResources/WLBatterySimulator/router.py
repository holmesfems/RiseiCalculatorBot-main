from fastapi import FastAPI, Request, Form, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .optimizer import optimize
BASE_DIR = Path(__file__).resolve().parent

router = APIRouter(prefix="/WLBatterySimulator", tags=["WLBatterySimulator"])

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    # 初期表示（未計算）
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": None,
            "error": None,
            "storage_margin": 10000
        },
    )


@router.post("/calculate", response_class=HTMLResponse)
def calculate(request: Request, required_power: int = Form(...), storage_margin: int = Form(...)):
    try:
        result = optimize(required_power, storage_margin)
        error = None
    except Exception as e:
        result = None
        error = str(e)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": result,
            "error": error,
            "required_power": required_power,
            "storage_margin": storage_margin
        },
    )