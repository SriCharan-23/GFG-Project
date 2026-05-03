"""
FastAPI main application for the Book E-Commerce store.
Serves HTML pages via Jinja2 and provides JSON API endpoints.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db, engine, Base
from models import Book
from seed_data import seed_database

# ── Logging setup ──
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bookstore")

# ── Base directory (FIX for Cloud Run) ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Lifespan: seed database on startup ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed data on startup."""
    Base.metadata.create_all(bind=engine)

    # Prevent duplicate seeding
    try:
        db = next(get_db())
        if not db.query(Book).first():
            seed_database()
    except Exception as e:
        logger.error(f"Seeding error: {e}")

    logger.info("[READY] Book E-Commerce server is ready!")
    yield


# ── FastAPI App ──
app = FastAPI(
    title="PageTurn Books — E-Commerce",
    description="A modern online bookstore",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Static files & templates (FIXED PATHS) ──
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static"
)

templates = Jinja2Templates(
    directory=os.path.join(BASE_DIR, "templates")
)


# ═══════════════════════════════════════════════════
# HTML PAGE ROUTES
# ═══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page_title": "Shop Our Collection",
    })


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {
        "request": request,
        "page_title": "About Us",
    })


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "page_title": "Contact Us",
    })


# ═══════════════════════════════════════════════════
# JSON API ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/api/books")
async def get_books(
    category: str = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
):
    query = db.query(Book)
    if category:
        query = query.filter(Book.category == category)
    books = query.order_by(Book.title).all()
    return JSONResponse(content=[book.to_dict() for book in books])


@app.post("/api/contact")
async def submit_contact(request: Request):
    try:
        form_data = await request.json()
        name = form_data.get("name", "Unknown")
        email = form_data.get("email", "Unknown")
        subject = form_data.get("subject", "No Subject")
        message = form_data.get("message", "")

        logger.info(
            "[MAIL] New contact submission:\n"
            f"   Name:    {name}\n"
            f"   Email:   {email}\n"
            f"   Subject: {subject}\n"
            f"   Message: {message[:200]}"
        )

        return JSONResponse(
            content={
                "status": "success",
                "message": "Thank you for reaching out! We'll get back to you within 24 hours.",
            }
        )
    except Exception as e:
        logger.error(f"Contact form error: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Something went wrong. Please try again."},
        )


# ═══════════════════════════════════════════════════
# HEALTH CHECK (NEW - useful for Cloud Run)
# ═══════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok"}


# ═══════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
