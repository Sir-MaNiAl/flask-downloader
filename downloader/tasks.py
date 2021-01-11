import time
from cgi import parse_header
from datetime import timedelta
from os import PathLike
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

from downloader.db import db_session
from downloader.helpers import human_readable_size
from downloader.db.models import File

import requests
from celery import Celery
from celery.utils.log import get_task_logger
from flask import Flask
from sqlalchemy.orm.exc import ObjectDeletedError

celery = Celery()
logger = get_task_logger(__name__)


# pylint - inherit-non-class false positive: NamedTuple (Python 3.9)
# https://github.com/PyCQA/pylint/issues/3876
class HttpHeader(NamedTuple):  # pylint: disable=inherit-non-class
    header: str
    options: dict


def make_celery(app: Flask):
    global celery
    celery.conf.update(main=app.import_name,
                       result_backend=app.config['CELERY_RESULT_BACKEND'],
                       broker_url=app.config['CELERY_BROKER_URL'])
    celery.conf['UPLOAD_ROOT_DIR'] = app.config['UPLOAD_ROOT_DIR']

    class ContextTask(celery.Task):  # type: ignore[name-defined]

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


@celery.task
def download_file(id):
    session = db_session()
    file_ = File.query.get(id)  # pylint: disable=no-member
    # Перестраховка если запись успели удалить после ответа клиенту.
    if file_ is None:
        logger.warning(
            f'File {id=} not found. Probably deleted before upload?')
        return

    start_time = time.monotonic()
    with requests.get(file_.url, stream=True) as response:
        _header, options = parse_header(
            response.headers.get('Content-Disposition', ''))
        file_.name = (options.get('filename*') or options.get('filename') or
                      urlparse(file_.url).path.split('/')[-1])
        file_.size = human_readable_size(int(
            response.headers['Content-Length']))
        session.commit()

        # Ленивая загрузка начинёт новую транзакцию.
        # Перестраховка если запись успели удалить после обновления данных.
        try:
            path = get_upload_path(file_.on_disk_filename)
        except ObjectDeletedError:
            logger.warning(
                f'File {id=} not found. Probably deleted before upload?')
            return

        with path.open('bw') as f:
            for chunk in response.iter_content():
                f.write(chunk)

    file_.download_time = timedelta(seconds=time.monotonic() - start_time)
    file_.downloaded = True
    session.commit()


@celery.task
def delete_file(id):
    session = db_session()
    file_ = File.query.get(id)  # pylint: disable=no-member
    if file_ is None:
        return
    get_upload_path(file_.on_disk_filename).unlink(missing_ok=True)
    session.delete(file_)
    session.commit()


def get_upload_path(filename: PathLike):
    return Path(celery.conf['UPLOAD_ROOT_DIR']) / filename
