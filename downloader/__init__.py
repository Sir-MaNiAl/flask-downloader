import os

from flask import Flask, logging

ENVVAR_PREFIX = 'FILE_DOWNLOADER_'


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    # Default dev config
    app.config.update(SECRET_KEY='dev',
                      DATABASE_URL='postgresql://test:test@localhost/test',
                      UPLOAD_ROOT_DIR='./upload/',
                      CELERY_BROKER_URL='amqp://test:test@localhost:5672/test',
                      CELERY_RESULT_BACKEND='redis://test:test@localhost:6379')

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
        # Update congig with env variables, if exists.
        for key in ('SECRET_KEY', 'DATABASE_ECHO', 'DATABASE_URL',
                    'UPLOAD_ROOT_DIR', 'CELERY_BROKER_URL',
                    'CELERY_RESULT_BACKEND'):
            envvar = f'{ENVVAR_PREFIX}{key}'
            if value := os.getenv(envvar):
                app.config[key] = value

    else:
        app.config.from_mapping(test_config)

    os.makedirs(app.config['UPLOAD_ROOT_DIR'], exist_ok=True)

    from . import db
    db.init_app(app)
    db.init_db(app)

    from . import tasks
    tasks.make_celery(app)

    register_routes(app)

    return app


def register_routes(app):
    '''Registers all application rotes.'''
    from .views import downloader
    app.register_blueprint(downloader.bp)
