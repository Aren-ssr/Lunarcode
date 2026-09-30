from app.content import LANGUAGES, LESSONS, lesson_by_slug
from app.catalog import course_catalog
from app.security import TRIAL_SECONDS, hash_password, trial_is_active, verify_password


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("orbital-learning-42")
    second = hash_password("orbital-learning-42")
    assert first != second
    assert verify_password("orbital-learning-42", first)
    assert not verify_password("wrong-password", first)


def test_trial_expires_at_exact_boundary():
    assert TRIAL_SECONDS == 20 * 60
    assert trial_is_active(1_200, now=1_199)
    assert not trial_is_active(1_200, now=1_200)


def test_python_lessons_have_all_five_locales_and_quizzes():
    assert set(LANGUAGES) == {"hy", "fr", "es", "en", "ru"}
    assert len(LESSONS) == 10
    for locale in LANGUAGES:
        for lesson in LESSONS:
            localized = lesson_by_slug(lesson["slug"], locale)
            assert localized
            assert localized["title"]
            assert localized["theory"]
            assert localized["code"]
            assert localized["video"]["id"]
            assert len(localized["quiz"]["options"]) == 3
            assert 0 <= localized["quiz"]["answer"] < 3
            assert len(localized["quiz"]["checks"]) == 2
            assert all(len(check["options"]) == 3 and 0 <= check["answer"] < 3 for check in localized["quiz"]["checks"])
            assert localized["challenge"]
            assert localized["challenge_code"]
    for locale in LANGUAGES:
        first = lesson_by_slug("first-program", locale)
        assert len(first["guided_steps"]) == 5
        assert all(step["explanation"] for step in first["guided_steps"])


def test_every_learning_path_has_a_separate_one_time_course_price():
    for locale in LANGUAGES:
        courses = course_catalog(locale)
        names = {course["title"] for course in courses}
        assert len(courses) == 20
        assert {"Python", "HTML", "Rust"}.issubset(names)
        assert all(course["price"] == LANGUAGES.get("en", "") or course["price"] for course in courses)
        assert len([course for course in courses if course["available"]]) == 1
