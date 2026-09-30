# Lumincode

Lumincode is a multilingual programming and computer science learning site. The first interactive learning path is Python. The interface and lesson text currently support Armenian, French, Spanish, English, and Russian.

## Technology choices

- FastAPI serves the pages and handles accounts, access rules, quizzes, and billing webhooks.
- Jinja templates, CSS, and browser JavaScript provide the interactive interface. Node.js and Docker are not required to run the current version.
- SQLAlchemy connects the Python app to a SQL database. SQLite is used locally; PostgreSQL can be selected for a hosted launch.
- Passwords are stored as salted PBKDF2 hashes. Login sessions are random tokens whose hashes are stored in the database.

## Run locally on Windows PowerShell

1. Open PowerShell in the project folder.
2. Create and activate a Python virtual environment:

       python -m venv .venv
       .\.venv\Scripts\Activate.ps1

   If PowerShell blocks activation, use the virtual environment interpreter directly in the commands below.
3. Install the app packages:

       python -m pip install -r requirements.txt
4. Create the local configuration file:

       Copy-Item .env.example .env

5. Create the SQL tables:

       python -m alembic upgrade head

   The default database is the local file lumincode.db. It is created in the project folder.
6. Start the site:

       python -m uvicorn app.main:app --reload

7. Open http://127.0.0.1:8000 in a browser. The interactive API reference is at http://127.0.0.1:8000/api/docs.

The local configuration uses SQLite, a SQL database stored in one file. You do not need to install or start a database server. Account records, trial expiration, quiz attempts, and progress are stored in that file.

## Connect PostgreSQL later

1. Create a PostgreSQL database with the hosting provider you choose.
2. Copy the provider's database connection URL into the DATABASE_URL value in .env. The SQLAlchemy driver form is:

       postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require

3. Keep the connection URL private. Do not paste it into chat, commit it, or put it in frontend code. If the password contains URL-reserved characters, URL-encode those characters.
4. Install packages if you have not already, then run:

       python -m alembic upgrade head

5. Start the app with the same Uvicorn command. The database URL is read from .env when the server starts.

SQLite is convenient for learning and local work. Use hosted PostgreSQL for a public launch with real user accounts and payments. Choose a host later; its database URL and SSL settings may differ.

## Trial and course pricing

Every new account receives a 20-minute trial from registration. Server routes check access before returning course content. After the trial, each complete course is planned at $25 USD as a one-time payment. The finished Python course is the only course currently available to buy; the other cards show the roadmap and are not on sale yet. Purchases are stored per user and per course, so buying one path does not silently unlock every other path.

Stripe Checkout and webhook support is present, but payment is disabled until the site owner creates a Stripe account, creates a one-time $25 USD Python price, and configures these private values in .env:

- STRIPE_SECRET_KEY
- STRIPE_PRICE_PYTHON
- STRIPE_WEBHOOK_SECRET

In Stripe's dashboard, create a one-time USD 25 price for the complete Python course and copy its price ID to `STRIPE_PRICE_PYTHON`. Point the webhook to `https://YOUR-SITE/billing/webhook` and enable `checkout.session.completed`. Use Stripe test keys first. The deployed HTTPS address is needed for a public webhook. Never commit `.env`.

To grant founder access to an account, set that user's `is_owner` field to true in the SQL database. Owner access bypasses the trial and course purchase checks for courses that have actually been published. The site's roadmap cards do not create unfinished course pages.

## Current stage

- Working: home page, five interface languages, account registration/sign-in, database-backed sessions, trial access, Python lessons, two-part checkpoints, build missions, quiz scoring, points, levels, and progress.
- The full roadmap lists Computer Science, Python, JavaScript, HTML, CSS, SQL, C++, C#, Java, Rust, frontend, backend, software engineering, testing, automation, AI, data engineering, cloud/DevOps, Git, and system design. Python is the first complete course; the other cards clearly show that they are upcoming.
- Each Python lesson has a public YouTube embed. See [the curated video sources and reuse notes](docs/video-sources.md). Review third-party video licensing before the paid public launch.
- Email confirmation and password reset need a sender address and an email provider, which the owner has not chosen yet.
- Contact details are intentionally placeholders until the founder supplies an email.
- Stripe cannot charge or unlock a course until the owner configures the Stripe account, the $25 one-time price, and secrets.

## Run checks

    python -m pytest -q
