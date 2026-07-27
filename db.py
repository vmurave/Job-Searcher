"""SQLite storage for discovered job postings."""
from __future__ import annotations

import datetime as _dt
import os

from sqlalchemy import Column, Date, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# DB location is configurable so hosts (e.g. Render) can point it at a
# persistent disk via DATABASE_URL. Defaults to a local file for dev.
DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///jobs.db")
_connect_args = {"check_same_thread": False} if DB_PATH.startswith("sqlite") else {}
engine = create_engine(DB_PATH, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True, index=True)
    platform = Column(String, nullable=False, index=True)
    date_found = Column(Date, nullable=False, default=_dt.date.today, index=True)
    created_at = Column(DateTime, nullable=False, default=_dt.datetime.utcnow)


class RunLog(Base):
    __tablename__ = "run_log"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, nullable=False, default=_dt.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    new_jobs = Column(Integer, nullable=False, default=0)
    errors = Column(String, nullable=True)


Base.metadata.create_all(bind=engine)
