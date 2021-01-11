from uuid import uuid4

from downloader.db import Base
from sqlalchemy import Column, DateTime, Index, Interval, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func


class File(Base):
    __tablename__ = 'file'
    id = Column(UUID(as_uuid=True), primary_key=True)
    url = Column(String, nullable=False)
    name = Column(String(256))
    added_at = Column(DateTime, default=func.now(), server_default=func.now())
    download_time = Column(Interval)
    size = Column(String)

    __table_args__ = (Index('added_at__download_time__id__idx', added_at, id,
                            download_time),)

    def __init__(self, url):
        self.url = url
        self.id = uuid4()

    @property
    def on_disk_filename(self):
        return self.id.hex

    @classmethod
    def get_page(cls, last_id=None, per_page=20):
        # NB: Сортировка по-умолчанию: по-возрастанию дата, по-возрастанию
        # время скачивания, NULL значения (время скачивания) последними.
        # Предполагаю что строк в бд будет много, потому пагинация не по
        # оффсету, а по id.
        # pylint: disable=no-member
        query = File.query.order_by(File.added_at, File.download_time, File.id)
        if last_id:
            # pylint: disable=no-member
            # yapf: disable
            stmt = File.query.with_entities(File.id,
                                            File.added_at,
                                            File.download_time) \
                    .filter_by(id=last_id) \
                    .subquery('last_seen')
            # yapf: enable
            last_seen = aliased(File, stmt)
            # NB: Фильтр работает только с сортировкой по-умолчанию.
            _added_later = File.added_at > last_seen.added_at
            _added_same_date = File.added_at == last_seen.added_at
            _loaded_slower = File.download_time > last_seen.download_time
            _loaded_same_time = File.download_time == last_seen.download_time
            _same_date_slower = _added_same_date & _loaded_slower
            # yapf: disable
            _same_date_same_time_next_ids = (
                _added_same_date &
                (_loaded_same_time | File.download_time.is_(None)) &
                (File.id > last_seen.id))
            # yapf: enable
            # yapf: disable
            query = query.filter(
                _added_later |
                _same_date_slower |
                _same_date_same_time_next_ids)
            # yapf: enable

        return query.limit(per_page).all()
