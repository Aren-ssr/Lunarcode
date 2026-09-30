"""Lumincode web app: multilingual lessons, accounts, trial access, and progress."""

import os
import re
import secrets
import time
from pathlib import Path
from urllib.parse import quote

import stripe
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import grouped_course_catalog
from app.content import LANGUAGES, LESSONS, UI, lesson_by_slug, lesson_summaries
from app.database import Base, engine, get_db
from app.models import CoursePurchase, LessonProgress, LoginSession, QuizAttempt, User
from app.security import (
    SESSION_SECONDS,
    TRIAL_SECONDS,
    hash_password,
    new_session_token,
    token_digest,
    trial_is_active,
    verify_password,
)

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
SESSION_COOKIE = "lumincode_session"
CSRF_COOKIE = "lumincode_csrf"
SUPPORTED_LANGUAGES = set(LANGUAGES)
app = FastAPI(title="Lumincode", docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")


@app.middleware("http")
async def request_defaults(request: Request, call_next):
    """Set the selected locale, double-submit CSRF token, and safe headers."""
    candidate = request.query_params.get("lang") or request.cookies.get("lumincode_locale")
    if candidate not in SUPPORTED_LANGUAGES:
        accept = request.headers.get("accept-language", "")
        candidate = next(
            (part.split("-")[0].lower() for part in accept.split(",") if part.split("-")[0].lower() in SUPPORTED_LANGUAGES),
            "en",
        )
    request.state.locale = candidate
    csrf = request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(24)
    request.state.csrf_token = csrf
    response = await call_next(request)
    secure = request.url.scheme == "https"
    if not request.cookies.get(CSRF_COOKIE):
        response.set_cookie(CSRF_COOKIE, csrf, max_age=60 * 60 * 24, secure=secure, httponly=False, samesite="lax")
    if request.query_params.get("lang") in SUPPORTED_LANGUAGES:
        response.set_cookie("lumincode_locale", candidate, max_age=60 * 60 * 24 * 365, secure=secure, httponly=False, samesite="lax")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-src 'self' https://www.youtube-nocookie.com; frame-ancestors 'none'; base-uri 'self'")
    return response


def get_locale(request: Request) -> str:
    return getattr(request.state, "locale", "en")


def get_user(request: Request, db: Session) -> User | None:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        return None
    login = db.scalar(select(LoginSession).where(LoginSession.token_hash == token_digest(raw_token)))
    if not login or login.expires_at <= int(time.time()):
        return None
    return db.get(User, login.user_id)


def validate_csrf(request: Request, submitted: str) -> bool:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    return bool(cookie and submitted and secrets.compare_digest(cookie, submitted))


def has_access(user: User, now: int | None = None) -> bool:
    return user.is_owner or user.subscription_status in {"active", "trialing"} or trial_is_active(user.trial_expires_at, now)


def has_course_access(user: User, course_slug: str, db: Session, now: int | None = None) -> bool:
    """Allow trial, founder, legacy subscription, or a purchase of this course."""
    if has_access(user, now):
        return True
    return db.scalar(
        select(CoursePurchase.id).where(
            CoursePurchase.user_id == user.id,
            CoursePurchase.course_slug == course_slug,
        )
    ) is not None


def render(request: Request, page: str, **extra):
    locale = get_locale(request)
    user = extra.pop("user", None)
    status_code = extra.pop("status_code", 200)
    context = {
        "request": request,
        "locale": locale,
        "languages": LANGUAGES,
        "t": UI[locale],
        "current_user": user,
        "csrf_token": request.state.csrf_token,
    }
    context.update(extra)
    return templates.TemplateResponse(request=request, name=page, context=context, status_code=status_code)


def create_login(user: User, db: Session, response: RedirectResponse):
    raw_token = new_session_token()
    now = int(time.time())
    db.add(LoginSession(user_id=user.id, token_hash=token_digest(raw_token), expires_at=now + SESSION_SECONDS))
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=os.getenv("APP_ENV", "development") == "production",
        samesite="lax",
        path="/",
    )


def auth_redirect(destination: str) -> RedirectResponse:
    return RedirectResponse(f"/login?next={quote(destination, safe='/')}", status_code=303)


def progress_for(user: User, db: Session) -> tuple[set[str], int]:
    rows = db.scalars(select(LessonProgress).where(LessonProgress.user_id == user.id)).all()
    return {row.lesson_slug for row in rows}, sum(row.points for row in rows)


def safe_next_path(value: str) -> str:
    if value.startswith("/") and not value.startswith("//"):
        return value
    return "/dashboard"


def account_display_name(user: User) -> str:
    if user.display_name:
        return user.display_name
    local_part = user.email.split("@", 1)[0]
    match = re.match(r"[A-Za-zԱ-Ֆա-ֆ]+", local_part)
    return (match.group(0) if match else local_part).capitalize()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    return render(request, "home.html", user=user, course_groups=grouped_course_catalog(get_locale(request)))


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    if get_user(request, db):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "auth.html", mode="register", error=None, email="", next_path="/dashboard")


@app.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    email: str = Form(),
    password: str = Form(),
    display_name: str = Form(default=""),
    locale: str = Form(default="en"),
    csrf_token: str = Form(),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        return render(request, "auth.html", mode="register", error="csrf", email=email, next_path="/dashboard")
    normalized_email = email.strip().lower()
    if len(normalized_email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized_email):
        return render(request, "auth.html", mode="register", error="email", email=email, next_path="/dashboard")
    if len(password) < 8 or len(password) > 128:
        return render(request, "auth.html", mode="register", error="password", email=email, next_path="/dashboard")
    if db.scalar(select(User.id).where(User.email == normalized_email)):
        return render(request, "auth.html", mode="register", error="exists", email=email, next_path="/dashboard")
    if locale not in SUPPORTED_LANGUAGES:
        locale = get_locale(request)
    now = int(time.time())
    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        locale=locale,
        display_name=display_name.strip()[:80] or None,
        created_at=now,
        trial_expires_at=now + TRIAL_SECONDS,
        subscription_status="inactive",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie("lumincode_locale", locale, max_age=60 * 60 * 24 * 365, samesite="lax", path="/")
    create_login(user, db, response)
    return response


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/dashboard", db: Session = Depends(get_db)):
    if get_user(request, db):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "auth.html", mode="login", error=None, email="", next_path=safe_next_path(next))


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    email: str = Form(),
    password: str = Form(),
    next: str = Form(default="/dashboard"),
    csrf_token: str = Form(),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        return render(request, "auth.html", mode="login", error="csrf", email=email, next_path=safe_next_path(next))
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if not user or not verify_password(password, user.password_hash):
        return render(request, "auth.html", mode="login", error="login", email=email, next_path=safe_next_path(next))
    response = RedirectResponse(safe_next_path(next), status_code=303)
    create_login(user, db, response)
    return response


@app.post("/logout")
def logout(request: Request, csrf_token: str = Form(), db: Session = Depends(get_db)):
    if not validate_csrf(request, csrf_token):
        raise HTTPException(status_code=400, detail="Invalid form token")
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        login = db.scalar(select(LoginSession).where(LoginSession.token_hash == token_digest(token)))
        if login:
            db.delete(login)
            db.commit()
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.post("/locale")
def change_locale(
    request: Request,
    locale: str = Form(),
    next_path: str = Form(default="/"),
    csrf_token: str = Form(),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token) or locale not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Invalid locale form")
    user = get_user(request, db)
    if user:
        user.locale = locale
        db.commit()
    response = RedirectResponse(safe_next_path(next_path), status_code=303)
    response.set_cookie("lumincode_locale", locale, max_age=60 * 60 * 24 * 365, secure=request.url.scheme == "https", samesite="lax", path="/")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        return auth_redirect("/dashboard")
    done, points = progress_for(user, db)
    remaining = max(0, user.trial_expires_at - int(time.time()))
    return render(
        request,
        "dashboard.html",
        user=user,
        done=done,
        points=points,
        level=points // 200 + 1,
        remaining=remaining,
        lessons=lesson_summaries(get_locale(request)),
        has_access=has_access(user),
        display_name=account_display_name(user),
        course_groups=grouped_course_catalog(get_locale(request)),
    )


@app.get("/courses/python", response_class=HTMLResponse)
def python_course(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        return auth_redirect("/courses/python")
    if not has_course_access(user, "python", db):
        return RedirectResponse("/subscribe", status_code=303)
    done, points = progress_for(user, db)
    return render(
        request,
        "course.html",
        user=user,
        done=done,
        points=points,
        lessons=lesson_summaries(get_locale(request)),
    )


@app.get("/courses/python/{slug}", response_class=HTMLResponse)
def python_lesson(slug: str, request: Request, result: str | None = None, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        return auth_redirect(f"/courses/python/{slug}")
    if not has_course_access(user, "python", db):
        return RedirectResponse("/subscribe", status_code=303)
    lesson = lesson_by_slug(slug, get_locale(request))
    if not lesson:
        return render(request, "not_found.html", user=user, status_code=404)
    done, points = progress_for(user, db)
    return render(
        request,
        "lesson.html",
        user=user,
        lesson=lesson,
        done=done,
        points=points,
        result=result if result in {"correct", "incorrect"} else None,
        lessons=lesson_summaries(get_locale(request)),
    )


@app.post("/courses/python/{slug}/quiz")
def submit_quiz(
    slug: str,
    request: Request,
    answer: int = Form(),
    trace_answer: int = Form(),
    csrf_token: str = Form(),
    db: Session = Depends(get_db),
):
    user = get_user(request, db)
    if not user:
        return auth_redirect(f"/courses/python/{slug}")
    if not has_course_access(user, "python", db):
        return RedirectResponse("/subscribe", status_code=303)
    lesson = lesson_by_slug(slug, get_locale(request))
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if not validate_csrf(request, csrf_token):
        raise HTTPException(status_code=400, detail="Invalid form token")
    checks = lesson["quiz"]["checks"]
    answers = [answer, trace_answer]
    correct = len(answers) == len(checks) and all(
        0 <= answer < len(check["options"]) and answer == check["answer"]
        for answer, check in zip(answers, checks)
    )
    now = int(time.time())
    db.add(QuizAttempt(user_id=user.id, lesson_slug=slug, is_correct=correct, attempted_at=now))
    existing = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_slug == slug,
        )
    )
    if correct and not existing:
        db.add(LessonProgress(user_id=user.id, lesson_slug=slug, completed_at=now, points=lesson["points"]))
    db.commit()
    status = "correct" if correct else "incorrect"
    return RedirectResponse(f"/courses/python/{slug}?result={status}#quiz", status_code=303)


@app.get("/subscribe", response_class=HTMLResponse)
def subscribe_page(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        return auth_redirect("/subscribe")
    return render(
        request,
        "subscribe.html",
        user=user,
        stripe_ready=bool(os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_PRICE_PYTHON") and os.getenv("STRIPE_WEBHOOK_SECRET")),
        course_title=UI[get_locale(request)]["python_title"],
    )


@app.post("/courses/{course_slug}/checkout")
def checkout(course_slug: str, request: Request, csrf_token: str = Form(), db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        return auth_redirect(f"/courses/{course_slug}/checkout")
    if not validate_csrf(request, csrf_token):
        raise HTTPException(status_code=400, detail="Invalid form token")
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if course_slug != "python":
        raise HTTPException(status_code=404, detail="Course is not available yet")
    if has_course_access(user, course_slug, db):
        return RedirectResponse("/courses/python", status_code=303)
    price_id = os.getenv("STRIPE_PRICE_PYTHON")
    if not stripe_key or not price_id:
        return render(request, "subscribe.html", user=user, stripe_ready=False, error="billing", course_title=UI[get_locale(request)]["python_title"])
    stripe.api_key = stripe_key
    base_url = os.getenv("APP_BASE_URL", str(request.base_url).rstrip("/"))
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": price_id, "quantity": 1}],
            client_reference_id=str(user.id),
            customer_email=user.email,
            metadata={"course_slug": course_slug},
            success_url=f"{base_url}/courses/python?payment=success",
            cancel_url=f"{base_url}/subscribe?payment=cancelled",
        )
    except Exception:
        return render(request, "subscribe.html", user=user, stripe_ready=True, error="billing")
    return RedirectResponse(checkout_session.url, status_code=303)


@app.post("/billing/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Billing webhook is not configured")
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
    except Exception as error:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook") from error

    event_type = event["type"]
    data = event["data"]["object"]
    if event_type == "checkout.session.completed" and data.get("mode") == "payment":
        user_id = data.get("client_reference_id")
        course_slug = (data.get("metadata") or {}).get("course_slug")
        session_id = data.get("id")
        user = db.get(User, int(user_id)) if user_id and str(user_id).isdigit() else None
        if user and course_slug == "python" and session_id and not db.scalar(
            select(CoursePurchase.id).where(CoursePurchase.user_id == user.id, CoursePurchase.course_slug == course_slug)
        ):
            db.add(CoursePurchase(user_id=user.id, course_slug=course_slug, stripe_session_id=session_id, purchased_at=int(time.time())))
            db.commit()
    elif event_type == "checkout.session.completed" and data.get("mode") == "subscription":
        user_id = data.get("client_reference_id")
        user = db.get(User, int(user_id)) if user_id and str(user_id).isdigit() else None
        if user:
            user.stripe_customer_id = data.get("customer")
            user.stripe_subscription_id = data.get("subscription")
            user.subscription_status = "active"
            db.commit()
    elif event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        user = db.scalar(select(User).where(User.stripe_customer_id == data.get("customer")))
        if user:
            user.stripe_subscription_id = data.get("id")
            user.subscription_status = data.get("status", "inactive") if event_type.endswith("updated") else "inactive"
            db.commit()
    return JSONResponse({"received": True})


@app.get("/health")
def health():
    return {"status": "ok", "app": "Lumincode"}


@app.exception_handler(404)
async def not_found_handler(request: Request, _error):
    return render(request, "not_found.html", user=None, status_code=404)
