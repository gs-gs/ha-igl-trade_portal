"""
Python3.6+ only
"""
__VERSION__='0.0.2'


from pie import *


class DockerCompose:
    def __init__(self,docker_compose_filename,project_name=None):
        self.docker_compose_filename=docker_compose_filename
        self.project_name=project_name

    def cmd(self,compose_cmd,compose_options=[],options=[]):
        c_ops = [f'-f {self.docker_compose_filename}']
        if self.project_name:
            c_ops.append(f'-p {self.project_name}')
        c_ops.extend(compose_options)
        compose_options_str=' '.join(c_ops)
        options_str=' '.join(options)
        c=f'docker-compose {compose_options_str} {compose_cmd} {options_str}'
        # --no-ansi
        print(c)
        return cmd(c)


    def build(self,service=None,compose_options=[],options=[]):
        compose_options=list(compose_options)
        options=list(options)
        if isinstance(service,str):
            options.append(service)
        elif isinstance(service,(list,tuple)):
            options.extend(service)
        return self.cmd('build',compose_options=compose_options,options=options)


    def service(self,service_name):
        return DockerComposeService(self,service_name)


    @classmethod
    def set_ignore_orphans_env_variable(cls,value):
        """If you use multiple docker compose files in the same project, docker compose thinks that some services have been orphaned, but really it's just that docker compose doesn't know about the other docker compose files"""
        env.set('COMPOSE_IGNORE_ORPHANS','True' if value else 'False')



class DockerComposeService:
    def __init__(self,compose_obj,service_name):
        self.compose_obj=compose_obj
        self.service_name=service_name


    def cmd(self,compose_cmd,compose_options=[],options=[],container_cmd=''):
        options=list(options)
        options.extend([self.service_name,container_cmd])
        return self.compose_obj.cmd(compose_cmd,compose_options=compose_options,options=options)


    def build(self,compose_options=[],options=[]):
        return self.compose_obj.build(self.service_name,compose_options=compose_options,options=options)
