# Developer HOWTO

## Start locally

First - build the static files (UI):

    $ npm install && npm run build

First, cd do the ``trade_portal/devops/localdocker`` folder and create local.env file (may be empty; for each country you want to start - au sg cn etc):

    $ touch local.env
    $ touch demo-au-local.env
    $ touch demo-sg-local.env

To start it without intergov connection (just the UI, for doing markup or working with OA but not IGL):

    $ COMPOSE_PROJECT_NAME=trau docker-compose up

With the intergov node has already been started as docker-compose file (for each setup you update au to cn or sg):

    $ COMPOSE_PROJECT_NAME=trau docker-compose -f docker-compose.yml -f demo-au.yml up
    $ COMPOSE_PROJECT_NAME=trsg docker-compose -f docker-compose.yml -f demo-sg.yml up

To create a superuser:

    $ (the project variables) docker-compose run -rm django bash
    $ ./manage.py createsuperuser

After it's done please get back to README.md to configure organisation manually (so you can create documents).

Constance configuration: navigate to .../admin/constance/config/ and

* set the OA_WRAP_API_URL to the correct one (for example https://openattestation.c1.devnet.trustbridge.io/ - we only use document/wrap and unwrap endpoints which are public). If you need to start this API locally please check `/tradetrust/open-attestation-api/docker-compose.yml` file for details
* set OA_UNPROCESSED_BUCKET_NAME and OA_UNPROCESSED_QUEUE_URL so the service knows where to submit files for the notarisation worker; you are most likely have to set OA_AWS_ACCESS_KEYS variable as well with some api keys issued with access to these bucket/queue.
* update OA_NOTARY_CONTRACT to some correct value (which should be supplied with the bucket/queue from the previous point)


## Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report (inside the Django docker container):

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html


## Running tests

  $ py.test (from the inside of the django container)
  $ flake8
  $ bandit -r trade_portal

The helper pytest.sh will run unittests, mypy check and flake8 check.


### Translations

We use https://django-amazon-translate.readthedocs.io/en/latest/installation.html library
to ask AWS Translate to make the translations for us. It saves times, but the translations
can look dumb in some places. Although it's easy to fix the most irritating ones manually.

To update them:

* pip install django_amazon_translate
* add `django_amazon_translate` line to the base.py, INSTALLED_APPS
* export your AWS credentials with AWS Translate access to env variables
* ./manage.py auto_translate_text
* ./manage.py compilemessages
* restart the web container
* ensure it's working
* remove `django_amazon_translate` from the INSTALLED_APPS

Please note this dependency and code changes is not pushed to the master because
it's rare manual operation anyway.
