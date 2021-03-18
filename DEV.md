# Developer HOWTO

## Start locally

First - build the static files (UI):

    $ npm install && npm run build

Then cd do the ``trade_portal/devops/localdocker`` folder and create local.env file (may be empty; for each country you want to start - au sg cn etc):

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

Please check ``trade_portal/devops/localdocker/common.env`` and other env files to understand how it's linked to external APIs. There is some documentation inside.


## Tests

Inside the Django docker container:

  $ py.test
  $ flake8
  $ bandit -r trade_portal

Coverage is available in ``htmlcov`` directory and is updated each test run.


### Translations

We use https://django-amazon-translate.readthedocs.io/en/latest/installation.html library
to ask AWS Translate to make the translations for us. It saves time, but the translations
can look dumb in some places. The most irritating ones are supposed to be fixed manually.

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

### Models graph

Login to the Django container and

    ./manage.py graph_models documents users  > documents_users.dot
    ./manage.py graph_models documents  > documents.dot
    ./manage.py graph_models -a > full.dot
