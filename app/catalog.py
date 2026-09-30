"""Course catalogue metadata and concise multilingual labels."""

from app.content import LANGUAGES, UI


TRACKS = [
    ("computer-science", "Computer Science", "⌘", "foundations", "cs", "#c7b7ff"),
    ("python", "Python", "Py", "languages", "python", "#a9a0ff"),
    ("javascript", "JavaScript", "JS", "languages", "javascript", "#f4ce67"),
    ("html", "HTML", "<>" , "languages", "html", "#62dc9d"),
    ("css", "CSS", "#", "languages", "css", "#7198ff"),
    ("sql", "SQL", "DB", "languages", "sql", "#42d1d7"),
    ("cpp", "C++", "C++", "languages", "cpp", "#84a9ff"),
    ("csharp", "C#", "C#", "languages", "csharp", "#c6dc71"),
    ("java", "Java", "J", "languages", "java", "#f0a775"),
    ("rust", "Rust", "Rs", "languages", "rust", "#ff756e"),
    ("frontend", "Frontend", "◫", "engineering", "frontend", "#68caff"),
    ("backend", "Backend", "⇄", "engineering", "backend", "#a98bff"),
    ("software-engineering", "Software Engineering", "⚙", "engineering", "software", "#ffb36d"),
    ("testing", "Testing & Quality", "✓", "engineering", "testing", "#75ddbd"),
    ("automation", "Automation", "↻", "engineering", "automation", "#66d9b2"),
    ("ai-ml", "AI & Machine Learning", "✳", "engineering", "ai", "#db8aff"),
    ("data-engineering", "Data Engineering", "▤", "engineering", "data", "#55d5df"),
    ("cloud-devops", "Cloud & DevOps", "☁", "engineering", "cloud", "#78b5ff"),
    ("git-teams", "Git & Teamwork", "⑂", "engineering", "git", "#f39bb8"),
    ("systems-design", "Systems Design", "◎", "engineering", "systems", "#d5b4ff"),
]

GROUP_LABELS = {
    "en": {"foundations": "FOUNDATIONS", "languages": "PROGRAMMING LANGUAGES", "engineering": "BUILD & ENGINEER"},
    "hy": {"foundations": "ՀԻՄՔԵՐ", "languages": "ԾՐԱԳՐԱՎՈՐՄԱՆ ԼԵԶՈՒՆԵՐ", "engineering": "ՍՏԵՂԾՈՒՄ ԵՎ ԻՆԺԵՆԵՐԻԱ"},
    "fr": {"foundations": "FONDAMENTAUX", "languages": "LANGAGES DE PROGRAMMATION", "engineering": "CONSTRUIRE ET CONCEVOIR"},
    "es": {"foundations": "FUNDAMENTOS", "languages": "LENGUAJES DE PROGRAMACIÓN", "engineering": "CONSTRUIR E INGENIERÍA"},
    "ru": {"foundations": "ОСНОВЫ", "languages": "ЯЗЫКИ ПРОГРАММИРОВАНИЯ", "engineering": "РАЗРАБОТКА И ИНЖЕНЕРИЯ"},
}

TITLES = {
    "computer-science": {"hy": "Համակարգչային գիտություն", "fr": "Informatique", "es": "Ciencias de la computación", "ru": "Компьютерные науки"},
    "frontend": {"hy": "Ֆրոնթենդ մշակում", "fr": "Développement frontend", "es": "Desarrollo frontend", "ru": "Фронтенд-разработка"},
    "backend": {"hy": "Բեքենդ մշակում", "fr": "Développement backend", "es": "Desarrollo backend", "ru": "Бэкенд-разработка"},
    "software-engineering": {"hy": "Ծրագրային ինժեներիա", "fr": "Ingénierie logicielle", "es": "Ingeniería de software", "ru": "Программная инженерия"},
    "testing": {"hy": "Թեստավորում և որակ", "fr": "Tests et qualité", "es": "Pruebas y calidad", "ru": "Тестирование и качество"},
    "automation": {"hy": "Ավտոմատացում", "fr": "Automatisation", "es": "Automatización", "ru": "Автоматизация"},
    "ai-ml": {"hy": "AI և մեքենայական ուսուցում", "fr": "IA et apprentissage automatique", "es": "IA y aprendizaje automático", "ru": "ИИ и машинное обучение"},
    "data-engineering": {"hy": "Տվյալների ինժեներիա", "fr": "Ingénierie des données", "es": "Ingeniería de datos", "ru": "Инженерия данных"},
    "cloud-devops": {"hy": "Cloud և DevOps", "fr": "Cloud et DevOps", "es": "Cloud y DevOps", "ru": "Облако и DevOps"},
    "git-teams": {"hy": "Git և թիմային աշխատանք", "fr": "Git et travail en équipe", "es": "Git y trabajo en equipo", "ru": "Git и командная работа"},
    "systems-design": {"hy": "Համակարգերի նախագծում", "fr": "Conception de systèmes", "es": "Diseño de sistemas", "ru": "Проектирование систем"},
}


def course_catalog(locale: str) -> list[dict]:
    """Build the full, consistently priced catalog for the selected locale."""
    labels = UI.get(locale, UI["en"])
    return [
        {
            "slug": slug,
            "title": TITLES.get(slug, {}).get(locale, title),
            "mark": mark,
            "group": group,
            "group_label": GROUP_LABELS.get(locale, GROUP_LABELS["en"])[group],
            "palette": palette,
            "available": slug == "python",
            "price": labels["course_price"],
            "status": labels["course_ready"] if slug == "python" else labels["course_soon"],
            "button": labels["lesson_open"] if slug == "python" else labels["course_soon"],
            "href": "/courses/python" if slug == "python" else "",
            "description": labels["track_cs_copy"] if group == "foundations" else labels["track_language_copy"] if group == "languages" else labels["track_engineering_copy"],
        }
        for slug, title, mark, group, _theme, palette in TRACKS
    ]


def grouped_course_catalog(locale: str) -> list[dict]:
    courses = course_catalog(locale)
    labels = GROUP_LABELS.get(locale, GROUP_LABELS["en"])
    return [
        {"key": key, "title": labels[key], "courses": [course for course in courses if course["group"] == key]}
        for key in ("foundations", "languages", "engineering")
    ]
