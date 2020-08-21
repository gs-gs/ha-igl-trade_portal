FROM python:3.7-slim-buster

ENV PYTHONUNBUFFERED 1

RUN apt-get update \
  # dependencies for building Python packages
  && apt-get install -y build-essential git \
  # psycopg2 dependencies
  && apt-get install -y libpq-dev \
  # Translations dependencies
  && apt-get install -y gettext \
  # Pdf/Image deps
  && apt-get install -y libmagickwand-dev ghostscript libgl-dev \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip install -r /requirements/local.txt

COPY ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/local/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

COPY ./compose/local/django/celery/worker/start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker

COPY ./compose/local/django/celery/beat/start /start-celerybeat
RUN sed -i 's/\r$//g' /start-celerybeat
RUN chmod +x /start-celerybeat

COPY ./compose/local/django/celery/flower/start /start-flower
RUN sed -i 's/\r$//g' /start-flower
RUN chmod +x /start-flower

# enable PDF conversion in wand/imagemagick
RUN python -c "result = open('/etc/ImageMagick-6/policy.xml').read().replace('rights="\""none"\"" pattern="\""PDF"\""', 'rights="\""read | write"\"" pattern="\""PDF"\""'); open('/etc/ImageMagick-6/policy.xml', 'w').write(result)"

COPY . /app

WORKDIR /app

RUN DATABASE_URL="postgres://" python /app/manage.py collectstatic --noinput  > /dev/null
RUN DATABASE_URL="postgres://" python /app/manage.py compilemessages > /dev/null

ENTRYPOINT ["/entrypoint"]
