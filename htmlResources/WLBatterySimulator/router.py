from fastapi import FastAPI, Request, Form, APIRouter
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional

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
            "storage_margin": 10000,
            "use_margin_under_5": True
        },
    )

@router.get("/calculate")
def calculate_get(request: Request):
    return RedirectResponse("https://discordbot-riseicalculator.herokuapp.com/WLBatterySimulator/")

@router.post("/calculate", response_class=HTMLResponse)
def calculate(request: Request, required_power: int = Form(...), storage_margin: int = Form(...), use_margin_under_5:Optional[bool] =Form(False)):
    try:
        result = optimize(required_power, storage_margin, use_margin_under_5)
        error = None
    except Exception as e:
        result = None
        error = str(e)
        errResponse = templates.TemplateResponse("error.html",{
            "request": request,
            "error": error
        })
        return HTMLResponse(f"""
            <div id="error" class="error" hx-swap-oob="outerHTML">
                {errResponse.body.decode("utf-8")}
            </div>
        """)
    

    resultResponse = templates.TemplateResponse("result.html",{
        "request": request,
        "result": result
    })
    chartResponse = templates.TemplateResponse("chart.html",{
        "request": request,
        "result": result
    })

    return HTMLResponse(content=f"""
      <div id="error" class="error" hx-swap-oob="outerHTML" hidden="true">
      </div>
      <div id="result" class="result" hx-swap-oob="outerHTML">
        {resultResponse.body.decode("utf-8")}
      </div>
      <section id="tvChart" class="card full" hx-swap-oob="outerHTML">
        {chartResponse.body.decode("utf-8")}
      </section>
    """)