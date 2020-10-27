FROM python:3.8-alpine

RUN apk update && apk add bash make g++ gcc curl

WORKDIR /document-store-worker

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./ ./

ENV PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ./docker-entrypoint.sh
