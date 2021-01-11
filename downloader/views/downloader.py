from uuid import uuid4
from datetime import timezone

from flask import Blueprint, abort, make_response, redirect, current_app
from marshmallow import validate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import not_, or_, and_
from werkzeug.exceptions import default_exceptions
from webargs import fields
from webargs.flaskparser import use_args, parser

from downloader import tasks
from downloader.db import db_session
from downloader.db.models import File

bp = Blueprint('downloader', __name__)


@bp.route('/download', methods=['POST'])
@use_args(
    {
        'url_list':
            fields.List(
                fields.Url, required=True, validation=lambda x: len(x) > 0)
    },
    location='json',
)
def files_download(args):
    session = db_session()
    files = [File(url=url) for url in args['url_list']]
    session.bulk_save_objects(files)
    session.commit()

    for f in files:
        tasks.download_file.delay(f.id)

    return {'files': [{'url': f.url, 'id': f.id} for f in files]}


@bp.route('/files', methods=['GET'])
@use_args(
    {
        'per_page':
            fields.Int(missing=20, validation=validate.Range(min=1, max=1000)),
        'show_after_id':
            fields.UUID(missing=None)
    },
    location='json',
)
def files_list(args):
    per_page = args['per_page']
    show_after_id = args['show_after_id']
    # NB: Сортировка по-умолчанию: по-возрастанию дата, по-возрастанию время
    # скачивания, NULL значения (время скачивания) последними.
    # Предполагаю что строк в бд будет много, потому пагинация не по оффсету,
    # а по id.
    # pylint: disable=no-member
    query = File.query.order_by(File.added_at, File.download_time, File.id)
    if show_after_id:
        # pylint: disable=no-member
        # yapf: disable
        stmt = File.query.with_entities(File.id,
                                        File.added_at,
                                        File.download_time) \
                   .filter_by(id=show_after_id) \
                   .subquery('last_seen_file')
        # yapf: enable
        last_seen_file = aliased(File, stmt)
        # NB: Фильтр работает только с сортировкой по-умолчанию.
        _added_later = File.added_at > last_seen_file.added_at
        _added_same_date = File.added_at == last_seen_file.added_at
        _loaded_slower = File.download_time > last_seen_file.download_time
        _same_date_slower = _added_same_date & _loaded_slower
        _loaded_same_time = File.download_time == last_seen_file.download_time
        # yapf: disable
        _same_date_same_downloadtime_next_ids = (
            _added_same_date &
            (_loaded_same_time | File.download_time.is_(None)) &
            (File.id > last_seen_file.id))
        # yapf: enable
        # yapf: disable
        query = query.filter(
            _added_later |
            _same_date_slower |
            _same_date_same_downloadtime_next_ids)
        # yapf: enable

    files = query.limit(per_page).all()
    return {'files': [file_as_json(f) for f in files]}


@bp.route('/file/<uuid:id>', methods=['GET'])
def file_show(id):
    file_ = File.query.get(id)  # pylint: disable=no-member
    return file_as_json(file_) if file_ else {}


@bp.route('/file/<uuid:id>', methods=['POST'])
@use_args(
    {'name': fields.String(required=True)},
    location='json',
)
def file_rename(args, id):
    session = db_session()
    file_ = File.query.get(id)  # pylint: disable=no-member
    if file_ is None:
        return {}
    else:
        file_.name = args['name']
        session.commit()
        return file_as_json(file_)


@bp.route('/file/<uuid:id>', methods=['DELETE'])
def file_delete(id):
    tasks.delete_file.delay(id)
    return {}


@parser.error_handler
def handle_error(error, req, schema, *, error_status_code, error_headers):
    status_code = error_status_code or parser.DEFAULT_VALIDATION_STATUS
    response = make_response(
        {
            'description': default_exceptions[status_code].description,
            'data': error.data,
            'errors': error.messages,
        },
        status_code,
    )
    response.headers = error_headers
    abort(response)


def file_as_json(f: File):
    return {
        'id': f.id,
        'url': f.url,
        'added_at': f.added_at.replace(tzinfo=timezone.utc).isoformat(),
        'name': f.name,
        'download_time': f.download_time and str(f.download_time),
        'size': f.size
    }
