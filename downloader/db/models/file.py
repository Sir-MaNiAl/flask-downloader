from uuid import uuid4

from downloader.db import Base
from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Index, Interval,
                        String)
from sqlalchemy.dialects.postgresql import UUID
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
