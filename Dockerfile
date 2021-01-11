FROM python:3.9.1-alpine3.12 AS build
RUN apk update &&\
    apk add gcc postgresql-dev python3-dev musl-dev
WORKDIR /install
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.9.1-alpine3.12
RUN addgroup -S app && adduser -S app -G app
WORKDIR /app
COPY --from=build /install /usr/local
COPY ./downloader ./downloader
COPY ./entrypoint.sh .
RUN apk --no-cache add postgresql-libs && \
    chown -R app:app . && \
    chmod +x ./entrypoint.sh

USER app
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "--workers=2", "--threads=4", "--worker-class=gthread", "-b 0.0.0.0:8000", "downloader:create_app()"]
