from enum import Enum
# from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
@app.get("/home", response_class=HTMLResponse)
async def home():
    return templates.TemplateResponse("index.html", {"request":{}})

@app.get("/login", response_class=HTMLResponse)
async def login():
    return templates.TemplateResponse("login.html", {"request": {}})