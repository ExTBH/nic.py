from enum import Enum
import json, os, subprocess, re, shutil
from pathlib import Path
from typing import Dict, List, Tuple
from glob import glob
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.completion import Completer, Completion
from tempfile import TemporaryDirectory
from cookiecutter.main import cookiecutter

class NoTemplates(Exception):
    pass

class NoTheosEnv(Exception):
    pass

class Regex:
    filter_project_name = '[^a-zA-Z0-9+.-]'
    bundle = '^([a-zA-Z0-9\\+\\-]+\\.)+[a-zA-Z0-9\\+\\-]+$'


class PromptsTypes(Enum):
    FULL_PROJECT_NAME = 'FULL_PROJECT_NAME'
    CLEAN_PROJECT_NAME = 'CLEAN_PROJECT_NAME'
    BUNDLE_ID = 'BUNDLE_ID'
    BUNDLE_FILTER = 'BUNDLE_FILTER'
    KILL_PROCESS = 'KILL_PROCESS'
    AUTHOR = 'AUTHOR'


class BundleValidator(Validator):
    def validate(self, document) -> None:
        ok = re.match(Regex.bundle, document.text)
        if not ok:
            raise ValidationError(
                message='Invalid Bundle ID',
                cursor_position=len(document.text)
            )

class BundleCompleter(Completer):
    def __init__(self, bundles: List = []) -> None:
        super().__init__()
        self.bundles = bundles
    def get_completions(self, document, complete_event):
        for bundle in self.bundles:
            if bundle.lower().startswith(document.text.lower()):
                yield Completion(bundle, start_position=-len(document.text))


def load_templates(templates_dir: Path) -> Tuple[List[str], List[str]]:
    templates_folders = glob((templates_dir / '*.nic3').as_posix(), recursive=False)
    if len(templates_folders) < 1:
        raise NoTemplates(f"Niccy can't find templates in [{templates_dir}]")
    
    templates_names = []
    for index, template in enumerate(templates_folders):
        template_name = get_template_name(Path(template))
        if template_name:
            templates_names.append(template_name)
        else:
            templates_folders.pop(index) #broken template?
    return (templates_names, templates_folders)

def get_template_name(path: Path) -> str:
    try:
        with open(path / 'template.json', 'r') as f:
            conf = json.load(f)
            return conf.get('template_name')
    except OSError:
        return ''



def set_prompt_keys_for_type(keys: Dict, prompt: Dict, bundles: List = []) -> Dict:
    if prompt['type'] == PromptsTypes.FULL_PROJECT_NAME.value:
        keys['type'] = 'input'
        if not prompt.get('description'):
            keys['message'] = 'Enter a Project Name:'

    elif prompt['type'] == PromptsTypes.BUNDLE_ID.value:
        keys['validate'] = BundleValidator
        if not prompt.get('description'):
            keys['message'] = 'Enter a Bundle ID:'
        keys['default'] = lambda answers: f"com.yourcompany.{re.sub(Regex.filter_project_name, '', answers['FULL_PROJECT_NAME'])}"
    
    elif prompt['type'] == PromptsTypes.BUNDLE_FILTER.value:
        keys['validate'] = BundleValidator
        keys['completer'] = BundleCompleter(bundles)
        if not prompt.get('description'):
            keys['message'] = 'Enter a MobileSubstrate Filter:'

    elif prompt['type'] == PromptsTypes.KILL_PROCESS.value:
        if not prompt.get('description'):
            keys['message'] = 'Enter Applications to terminate (space-separated, empty for none):'

    elif prompt['type'] == PromptsTypes.AUTHOR.value:
        if not prompt.get('description'):
            keys['message'] = 'Enter Auther/Maintainer Name:'
        if not prompt.get('default'):
            keys['default'] = os.getlogin().title()
    
    elif prompt['type'] == 'list':
        keys['type'] = 'list'
        keys['choices'] = prompt['choices']
    return keys


def prompts_for_template(path: Path, bundles: List = []) -> List:
    try:
        with open(path / 'template.json', 'r') as f:
            conf = json.load(f)
            prompts = []
            for prompt in conf['prompts']:
                keys = {}

                keys['name'] = prompt['jinja_tag']

                if prompt.get('description'):
                    keys['message'] = prompt['description']

                if prompt.get('default'):
                    keys['default'] = prompt['default']
                
                if prompt.get('required'):
                    keys['validate'] = lambda val: val.strip() != '' or 'Required field'  
                
                keys = set_prompt_keys_for_type(keys, prompt, bundles)

                if not keys.get('type'):
                    keys['type'] = 'input'
                prompts.append(keys)

            return prompts
    except OSError:
        return []

def bundles_over_ssh(host = os.environ['THEOS_DEVICE_IP'], user = 'root', port = '22') -> List[str]:
    if os.environ.get('THEOS_DEVICE_USER'):
        user = os.environ['THEOS_DEVICE_USER']
    if os.environ.get('THEOS_DEVICE_PORT'):
        port = os.environ['THEOS_DEVICE_PORT']

    session = subprocess.run(['ssh', f'{user}@{host}', '-p', port, 'uicache', '-l'], capture_output=True, text=True)
    if session.returncode != 0:
        print(session.stderr)
        return []
    entries = session.stdout.splitlines()
    raw_bundles = []
    for entry in entries:
        bundle, path = entry.split(' : ')
        raw_bundles.append(bundle)

    return raw_bundles

def build_cc_project(answers: Dict, template_path: Path) -> None:
    with TemporaryDirectory() as temp_dir:
        answers['CLEAN_PROJECT_NAME'] = re.sub(Regex.filter_project_name, '', answers['FULL_PROJECT_NAME'])
        dest_dir = Path(temp_dir) / 'dest'
        shutil.copytree(template_path, dest_dir)

        config_path = Path(dest_dir) / 'cookiecutter.json'
        config_path.write_text(json.dumps(answers))
        cookiecutter(dest_dir.as_posix(), no_input=True)

def theos_env() -> Path:
    if os.environ.get('THEOS'):
        return Path(os.environ['THEOS'])
    raise NoTheosEnv