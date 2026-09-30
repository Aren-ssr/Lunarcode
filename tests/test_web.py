import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import LessonProgress, User


def make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    return client, engine, TestingSession


def test_signup_quiz_points_and_locale_switch():
    client, engine, _session = make_client()
    try:
        response = client.get("/register?lang=es")
        assert response.status_code == 200
        csrf = client.cookies["lumincode_csrf"]
        signup = client.post(
            "/register",
            data={
                "email": "Student@example.com",
                "password": "a-strong-password",
                "locale": "es",
                "csrf_token": csrf,
            },
            follow_redirects=False,
        )
        assert signup.status_code == 303
        assert signup.headers["location"] == "/dashboard"
        assert client.cookies.get("lumincode_session")

        dashboard = client.get("/dashboard")
        assert dashboard.status_code == 200
        assert "Tu órbita de aprendizaje" in dashboard.text
        assert "data-countdown=" in dashboard.text

        lesson = client.get("/courses/python/first-program")
        assert lesson.status_code == 200
        assert "Tu primer programa en Python" in lesson.text
        assert "data-lesson-flow" in lesson.text
        assert "print()" in lesson.text
        assert "int(" in lesson.text
        assert "youtube-nocookie.com/embed/JP7ITIXGpHk" in lesson.text
        assert "RETO DE CONSTRUCCIÓN" in lesson.text
        assert 'name="trace_answer"' in lesson.text
        assert 'role="tab"' not in lesson.text
        quiz = client.post(
            "/courses/python/first-program/quiz",
            data={"answer": "1", "trace_answer": "0", "csrf_token": csrf},
            follow_redirects=False,
        )
        assert quiz.status_code == 303
        assert "result=correct" in quiz.headers["location"]

        with engine.connect() as connection:
            progress = connection.execute(select(LessonProgress.lesson_slug, LessonProgress.points)).all()
        assert progress == [("first-program", 100)]
        after = client.get("/dashboard")
        assert "100" in after.text
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_expired_trial_blocks_course_and_routes_to_subscription():
    client, engine, session_factory = make_client()
    try:
        csrf = client.get("/register").cookies.get("lumincode_csrf") or client.cookies["lumincode_csrf"]
        client.post(
            "/register",
            data={"email": "locked@example.com", "password": "a-strong-password", "locale": "en", "csrf_token": csrf},
            follow_redirects=False,
        )
        with session_factory() as db:
            user = db.scalar(select(User).where(User.email == "locked@example.com"))
            user.trial_expires_at = int(time.time()) - 1
            db.commit()
        response = client.get("/courses/python", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/subscribe"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_founder_access_survives_trial_expiration():
    client, engine, session_factory = make_client()
    try:
        csrf = client.get("/register").cookies.get("lumincode_csrf") or client.cookies["lumincode_csrf"]
        client.post(
            "/register",
            data={"email": "arena@example.com", "display_name": "Arena", "password": "a-strong-password", "locale": "en", "csrf_token": csrf},
            follow_redirects=False,
        )
        with session_factory() as db:
            user = db.scalar(select(User).where(User.email == "arena@example.com"))
            user.is_owner = True
            user.trial_expires_at = int(time.time()) - 1
            db.commit()

        dashboard = client.get("/dashboard")
        assert dashboard.status_code == 200
        assert "Welcome back, <span class=\"text-gradient\">Arena</span>" in dashboard.text
        assert "Founder access" in dashboard.text
        assert client.get("/courses/python").status_code == 200
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
