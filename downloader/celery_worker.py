from downloader import create_app
from downloader.tasks import celery

app = create_app()
