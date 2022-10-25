import json
import os
import sys
import re
#import colorama
from typing import List
from cookiecutter.main import cookiecutter
from glob import glob


class Consts:
    NIC = 'NIC 3.0 - New Instance Creator'
    NO_THEOS_ENV = 'THEOS enviroment variable is not set, '\
        'https://theos.dev/docs/installation.'
    FORBIDDEN_PATH = 'Cowardly refusing to make a prject in $THEOS(%s)'
    NO_TEMPLATES = 'Nicolas The Third didn\'t find new style templates, '\
        'going to use Nicolas the Second'
    NO_PROJECT_NAME = "I can't live without a project name! Aieeee!"
    TEMPLATE_PROMPT = 'Choose a Template (required): '
    TEMPLATE_PROMPT_ONLY_NUMBERS = 'Cmon dude only Numbers..'
    PROJECT_NAME_PROMPT = 'Project Name (required): '
    PACKAGE_NAME_PROMPT = 'Package Name [com.yourcompany.%s]: '
    SPRINGBOARD_PACKAGE = 'com.apple.springboard'
    SPRINGBOARD_PROCESS = 'SpringBoard'
    FILTER_PROMPT = f'MobileSubstrate Bundle filter [{SPRINGBOARD_PACKAGE}]: '
    INVALID_BUNDLE = 'Invaid filter(%s), only Letters, Number and [+.-] allowed'
    PROCESSES_PROMPT = f'List of applications to terminate upon installation '\
        '(space-separated, \'-\' for none) [{SPRINGBOARD_PROCESS}]: '

class Regex:
    filter_project_name = '[^a-zA-Z0-9+.-]'
    package_name = '^([a-zA-Z0-9\\+\\-]+\\.)+[a-zA-Z0-9\\+\\-]+$'


class NIC:
    __cwd = os.getcwd()
    __theos_dir = os.environ.get('THEOS')
    __templates_dir = f"{__theos_dir}/vendor/templates/v3"

    def __init__(self) -> None:
        if self.__theos_dir == None:
            sys.exit(Consts.NO_THEOS_ENV)

        if self.__theos_dir in self.__cwd:
            sys.exit(Consts.FORBIDDEN_PATH % self.__theos_dir)

        print(Consts.NIC + '\n' + '-' * len(Consts.NIC))
        self.__load_templates()


    @staticmethod
    def __bundle_filter() -> str:
        filter = input(Consts.FILTER_PROMPT)
        # get installed apps with ssh
        if filter == '':
            return Consts.SPRINGBOARD_PACKAGE
        if re.match(Regex.package_name, filter) == None:
            sys.exit(Consts.INVALID_BUNDLE % filter)
        return filter

    @staticmethod
    def __process_kill() -> str:
        apps = input(Consts.PROCESSES_PROMPT)
        if apps == '-':
            return ''
        elif apps == '':
            return Consts.SPRINGBOARD_PROCESS
        if len(apps.split(' ')) > 1:
            return 'INSTALL_TARGET_PROCESSES = ' + apps
        else:
            return 'INSTALL_TARGET_PROCESS = ' + apps

    def __load_templates(self) -> None:

        templates = glob(f"{self.__templates_dir}/*.nic")

        if len(templates) < 1:
            print(Consts.NO_TEMPLATES)
            print('-' * len(Consts.NIC))
            os.system('$THEOS/bin/nic.pl')
            sys.exit(0)


        for template in enumerate(templates):
            with open(f'{template[1]}/template.json', 'r') as f:
                config = json.load(f)
            print(f'[{template[0]}] {config.get("name")}')

        try:
            selected_template = int(input(Consts.TEMPLATE_PROMPT))
        except ValueError:
            sys.exit(Consts.TEMPLATE_PROMPT_ONLY_NUMBERS)

        # Gather project info
        project_name = input(Consts.PROJECT_NAME_PROMPT)
        if project_name == '':
            sys.exit(Consts.NO_PROJECT_NAME)

        clean_project_name = re.sub(Regex.filter_project_name, '', project_name)

        package_name = input(Consts.PACKAGE_NAME_PROMPT % clean_project_name)
        if package_name == '':
            package_name = f'com.yourcompany.{clean_project_name}'
        if re.match(Regex.package_name, package_name) == None:
            sys.exit(Consts.INVALID_BUNDLE % package_name)

        author = input(f'Author/Maintainer [{os.getlogin().title()}]: ')
        if author == '':
            author = os.getlogin().title()
        
        filter = self.__bundle_filter()
        kill_rule = self.__process_kill()

        cookiecutter(templates[selected_template], extra_context={
            "PACKAGENAME": package_name,
            "PROJECTNAME": clean_project_name,
            "FULLPROJECTNAME": project_name,
            "USER": author,
            "FILTER": filter,
            "KILL_RULE": kill_rule
        }, no_input=True)



try:
    nic = NIC()
except KeyboardInterrupt:
    sys.exit('\n')