# Developer HOWTO

## Start locally

First - build the static files (UI):

    $ npm install && npm run build

First, cd do the ``trade_portal/devops/localdocker`` folder and create local.env file (may be empty; for each country you want to start - au sg cn etc):

    $ touch demo-au-local.env
    $ touch demo-sg-local.env


To start it without intergov connection (just the UI, for doing markup):

    $ COMPOSE_PROJECT_NAME=trau docker-compose up

With the intergov node has already been started as docker-compose file (for each setup you update au to cn or sg):

    $ COMPOSE_PROJECT_NAME=trau docker-compose -f docker-compose.yml -f demo-au.yml up
    $ COMPOSE_PROJECT_NAME=trsg docker-compose -f docker-compose.yml -f demo-sg.yml up

Or you could still use the first variant, providing intergov endpoints as env variables
in the local.env file.

Please note that docker-compose project name must not be AU or CN or SG because 2-letter codes are already used by the intergov node; so we prefix them with CH letters.

Please note that by default the app is started for AU jurisdiction, you may change it using env variables.

To create a superuser:

    $ (the project variables) docker-compose run -rm django bash
    $ ./manage.py createsuperuser


## Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report (inside the Django docker container):

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html


## Running tests

  $ py.test (from the inside of the django container)

The helper pytest.sh will run unittests, mypy check and flake8 check.
