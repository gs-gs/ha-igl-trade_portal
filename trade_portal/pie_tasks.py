import shutil
from pathlib import Path

from pie_docker import *
from pie_docker_compose import *


ROOT_DIR = Path('.').absolute()
DOCKER_COMPOSE = DockerCompose(ROOT_DIR/'docker-compose.yml')


@task
def create_igl_local_network():
    Docker().network('igl-local-network').create()



@task
def build(no_cache=True):
    """
    Builds all images.
    Build the django image first, then the others without the --no-cache option to speed the build up
    """
    options = []
    options_django = options.copy()
    if no_cache:
        options_django.append('--no-cache')
    DOCKER_COMPOSE.build(service='django', options=options_django)
    DOCKER_COMPOSE.build(options=options)


@task
def start(background=False):
    DOCKER_COMPOSE.cmd('up', options=['-d' if background else '', 'django'])
# COMPOSE_PROJECT_NAME=trau docker-compose -f docker-compose.yml -f demo-au.yml up


@task
def stop():
    DOCKER_COMPOSE.cmd('down')


@task
def restart(background=False):
    stop()
    start(background)


@task
def manage(command):
    """
    Usage:
    python3 pie.py manage --command="collectstatic --no-input"
    """
    DOCKER_COMPOSE.service('django').cmd('run', options=['--rm'], container_cmd=f'python manage.py {command}')
