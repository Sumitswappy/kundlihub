import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

try:
	# Local dev convenience: load DATABASE_URL from backend/.env when present.
	# (The backend venv already includes python-dotenv in this repo.)
	from dotenv import load_dotenv

	backend_env_path = os.path.abspath(
		os.path.join(os.path.dirname(__file__), os.pardir, ".env")
	)
	load_dotenv(backend_env_path, override=True)
except Exception:
	# If python-dotenv isn't installed, we fall back to environment variables only.
	pass


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
	raise RuntimeError(
		"DATABASE_URL is not set. Set it as an environment variable or add it to backend/.env"
	)


connect_args: dict = {}
url_lower = DATABASE_URL.lower()

# Default engine kwargs for more reliable DB connections (especially on hosted Postgres).
engine_kwargs: dict = {}

# Neon often requires SSL. If sslmode is already present in the URL query params,
# do not override it.
if url_lower.startswith("postgresql") and "sslmode=" not in url_lower:
	connect_args["sslmode"] = "require"

	# Network/connectivity hardening. These options reduce failures due to
	# idle SSL connections being dropped by the server/load balancer.
	connect_args.setdefault("connect_timeout", 10)
	connect_args.setdefault("keepalives", 1)
	connect_args.setdefault("keepalives_idle", 30)
	connect_args.setdefault("keepalives_interval", 10)
	connect_args.setdefault("keepalives_count", 5)

	engine_kwargs.setdefault("pool_pre_ping", True)
	engine_kwargs.setdefault("pool_recycle", 300)
	engine_kwargs.setdefault("pool_timeout", 30)

	# If you're using a pooler/pgbouncer URL (common on Neon), disable
	# SQLAlchemy's pooling to avoid holding onto server-closed connections.
	# (The pooler already manages connections.)
	if "pooler" in url_lower or "pgbouncer" in url_lower:
		engine_kwargs.setdefault("poolclass", NullPool)

# SQLite needs this flag when used with FastAPI's default threadpool.
if url_lower.startswith("sqlite"):
	connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()