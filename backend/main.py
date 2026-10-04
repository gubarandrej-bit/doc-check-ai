"""Точка входа FastAPI-приложения."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from config import FRONTEND_URL, UPLOAD_DIR
from models import init_db
from routers import auth, users, projects, checks, ntd, ai_models, reports

app = FastAPI(title="DocCheck — проверка технической документации", version="1.0.0")

# Адреса перечислены явно: подстановка "*" вместе с allow_credentials=True
# несовместима — браузер всё равно блокирует запросы с заголовком Authorization.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Общий префикс /api обязателен: фронтенд обращается к /api/... (api.js),
# и в рабочем режиме nginx проксирует эти запросы сюда (frontend/nginx.conf).
API = "/api"
app.include_router(auth.router, prefix=API)
app.include_router(users.router, prefix=API)
app.include_router(projects.router, prefix=API)
app.include_router(checks.router, prefix=API)
app.include_router(ntd.router, prefix=API)
app.include_router(ai_models.router, prefix=API)
app.include_router(reports.router, prefix=API)

try:
    app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")
except Exception:
    pass


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "mode": config.MODE}


@app.get("/")
def root():
    return {"service": "DocCheck", "docs": "/docs", "version": "1.0.0"}