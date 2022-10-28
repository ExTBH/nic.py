from enum import Enum
import json
import os
import shutil
import sys
import re
import subprocess
import cmd
#import colorama
from typing import List, Union
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
    FILTER_SSH_PROMPT = 'Select a MobileSubstrate Bundle filter (0-%s) ' \
        f'or enter one [{SPRINGBOARD_PACKAGE}]: '
    INVALID_BUNDLE = 'Invaid filter(%s), only Letters, Number and [+.-] allowed'
    PROCESSES_PROMPT = 'List of applications to terminate upon installation '\
        f'(space-separated, \'-\' for none) [{SPRINGBOARD_PROCESS}]: '

class Regex:
    filter_project_name = '[^a-zA-Z0-9+.-]'
    bundle = '^([a-zA-Z0-9\\+\\-]+\\.)+[a-zA-Z0-9\\+\\-]+$'



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
    def _bundles_over_ssh() -> str:
        if os.environ.get('THEOS_DEVICE_IP'):
            print("Attempting to get Bundle ID's over SSH..")
            user = 'root'
            host = os.environ['THEOS_DEVICE_IP']
            port = '22'
            if os.environ.get('THEOS_DEVICE_USER'):
                user = os.environ['THEOS_DEVICE_USER']
            if os.environ.get('THEOS_DEVICE_PORT'):
                port = os.environ['THEOS_DEVICE_PORT']
            
            session = subprocess.run(['ssh', f'{user}@{host}','-p',port, 'uicache', '-l'], capture_output=True, text=True)
            if session.returncode != 0:
                print(session.stderr)
                print('Going back to manual mode')
                return ''
            
            entries = session.stdout.splitlines()
            raw_bundles = []
            for entry in entries:
                bundle, path = entry.split(' : ')
                raw_bundles.append(bundle)
            
            raw_bundles = sorted(raw_bundles)
            indexed_bundles, bundles_path = [], []# paths could be used later to fill the kill rule
            for index, bundle in enumerate(raw_bundles):
                indexed_bundles.append(f'[{index}] {bundle}')
            
            cmd.Cmd().columnize(indexed_bundles,
                displaywidth=shutil.get_terminal_size().columns)
            
            failed_attempts = 0
            while failed_attempts < 2:
                choice = input(Consts.FILTER_SSH_PROMPT % (len(raw_bundles) -1))
                if not choice:
                    return Consts.SPRINGBOARD_PACKAGE
                try:
                    return raw_bundles[int(choice)]
                except IndexError:
                    print(f'({choice}) is out of range, maximum is ({len(raw_bundles)-1})')
                    failed_attempts +=1
                except ValueError:
                    if re.match(Regex.bundle, choice):
                        return choice
                    else:
                        print(Consts.INVALID_BUNDLE % choice)
                        failed_attempts += 1
            sys.exit('Failed attempts exceeded, exiting...')

        return ''

    @staticmethod
    def _bundle_filter() -> str:
        ssh_filter = NIC._bundles_over_ssh()
        if ssh_filter:
            return ssh_filter
        failed_attempts = 0
        while failed_attempts < 2:
            choice = input(Consts.FILTER_PROMPT)
            if re.match(Regex.bundle, choice):
                return choice
            elif not choice:
                return Consts.SPRINGBOARD_PACKAGE
            else:
                print(Consts.INVALID_BUNDLE % choice)
                failed_attempts += 1
        sys.exit('Failed attempts exceeded, exiting...')

    @staticmethod
    def _kill_rule() -> str:
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
            subprocess.Popen('$THEOS/bin/nic.pl', shell=True).communicate()
            sys.exit(0)


        for index, path in enumerate(templates):
            with open(f'{path}/template.json', 'r') as f:
                config = json.load(f)
            print(f'[{index}] {config.get("name")}')

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
        if re.match(Regex.bundle, package_name) == None:
            sys.exit(Consts.INVALID_BUNDLE % package_name)

        author = input(f'Author/Maintainer [{os.getlogin().title()}]: ')
        if author == '':
            author = os.getlogin().title()
        
        filter = self._bundle_filter()
        kill_rule = self._kill_rule()

        cookiecutter(templates[selected_template], extra_context={
            "PACKAGENAME": package_name,
            "PROJECTNAME": clean_project_name,
            "FULLPROJECTNAME": project_name,
            "USER": author,
            "FILTER": filter,
            "KILL_RULE": kill_rule
        }, no_input=False)



try:
    nic = NIC()
except KeyboardInterrupt:
    sys.exit('\n')

