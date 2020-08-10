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

To create a superuser:

    $ (the project variables) docker-compose run -rm django bash
    $ ./manage.py createsuperuser

After it's done please get back to README.md to configure organisation manually (so you can create documents). Site note: navigate to .../admin/constance/config/ and set the OA_WRAP_API_URL to the correct one (for example https://openattestation.c1.devnet.trustbridge.io/ - we only use document/wrap and unwrap endpoints which are public).


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
