# Poker

A self-hosted FastAPI backend for tracking poker sessions. Manage tables, record buy-ins and cash-outs, calculate end-of-game settlements, and track a global leaderboard across all sessions.

---

## Features

- JWT authentication with email verification and password reset
- Create and manage game tables
- Track player buy-ins and cash-outs per session
- Automatic settlement calculation — minimal transactions to settle all debts
- Global leaderboard and per-user play history

---

## Requirements

- Python 3.13+
- An async-compatible database (PostgreSQL recommended for production; SQLite supported for development)

---

## Installation

```bash
git clone https://github.com/your-username/poker.git
cd poker

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Core dependencies
pip install -e .

# SQLite support (development only)
pip install -e ".[sqlite]"
```

---

## Configuration

Copy the example below into a `.env` file in the project root and fill in your values:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./poker.db
# For PostgreSQL: postgresql+asyncpg://user:password@localhost/poker

# JWT
JWT_SECRET=change-me
JWT_LIFETIME_HOURS=3

# Password reset
RESET_PASSWORD_SECRET=change-me
RESET_PASSWORD_TOKEN_LIFETIME_HOURS=1

# Email verification
VERIFICATION_SECRET=change-me
VERIFICATION_TOKEN_LIFETIME_HOURS=24
```

| Variable | Description |
|---|---|
| `DATABASE_URL` | Async SQLAlchemy connection string |
| `JWT_SECRET` | Secret used to sign JWT tokens |
| `JWT_LIFETIME_HOURS` | How long a login token stays valid |
| `RESET_PASSWORD_SECRET` | Secret for password reset tokens |
| `RESET_PASSWORD_TOKEN_LIFETIME_HOURS` | Password reset token expiry |
| `VERIFICATION_SECRET` | Secret for email verification tokens |
| `VERIFICATION_TOKEN_LIFETIME_HOURS` | Verification token expiry |

> **Note:** `on_after_forgot_password` and `on_after_request_verify` in `routers/auth.py` currently print tokens to stdout. Wire these up to an email provider before deploying publicly.

---

## Running

```bash
uvicorn app.main:app --reload
```

Interactive API docs are available at `http://localhost:8000/docs`.

---

## Project Structure

```
poker/
├── app/
│   ├── main.py          # App entrypoint, lifespan handler, global error handler
│   ├── models.py        # SQLAlchemy models: User, Player, GameTable
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── db.py            # Async engine, session factory, table initialisation
│   └── routers/
│       ├── auth.py      # Registration, login, password reset, verification
│       ├── users.py     # User listing and play history
│       ├── tables.py    # Table lifecycle and settlement calculation
│       └── players.py   # Player join, buy-in, cash-out, leave
├── pyproject.toml
└── .env                 # Not committed — see Configuration above
```

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first to discuss what you'd like to change.

---

## License

[MIT](LICENSE)