import os

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False))
Base = declarative_base()
Base.query = db_session.query_property()  # type: ignore[attr-defined]


def init_app(app: Flask):
    database_url = app.config['DATABASE_URL']
    echo = bool(app.config.get('DATABASE_ECHO'))
    engine = create_engine(database_url, convert_unicode=True, echo=echo)
    db_session.configure(bind=engine)
    app.teardown_appcontext(lambda e: db_session.remove())
    return app


def init_db(app: Flask):
    from . import models

    database_url = app.config['DATABASE_URL']
    engine = create_engine(database_url, convert_unicode=True)
    Base.metadata.create_all(bind=engine)
