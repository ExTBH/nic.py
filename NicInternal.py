from dataclasses import dataclass
from enum import Enum
import json, os, subprocess, re, shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.completion import Completer, Completion
from tempfile import TemporaryDirectory
from cookiecutter.main import cookiecutter

class NoTemplates(Exception):
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

@dataclass
class TemplatePrompt:
    type: PromptsTypes
    jinja_tag: str
    description: Optional[str]
    required: bool
    default: Optional[str]
    hidden: bool = False
    validate: Optional[Type[Validator]] = None # subclasses of Validator
    completer: Optional[Any] = None

    def __post_init__(self) -> None:
        if self.type == PromptsTypes.BUNDLE_ID.value:
            self.validate = BundleValidator
            self.completer = BundleCompleter(bundles_over_ssh())
            if not self.description:
                self.description = 'Tweak Bundle ID'

        elif self.type == PromptsTypes.BUNDLE_FILTER.value:
            self.validate = BundleValidator
            if not self.description:
                self.description = 'MobileSubstrate Filter'
        
        if self.required and not self.validate:
            self.validate = BaseValidator

    def cc_dict(self) -> Dict:
        cc_dict = {
            'type': 'input',
            'name': self.jinja_tag,
            'message': self.description,
        }
        # Jinja Hates `None` values
        if self.default:
            cc_dict['default'] = self.default
        if self.validate:
            cc_dict['validate'] = self.validate
        if self.completer:
            cc_dict['completer'] = self.completer

        return cc_dict



class BaseValidator(Validator):
    def validate(self, document) -> None:
        # Just to Validate for spaces and such 
        if len(document.text.strip(' ')) < 1:
            raise ValidationError(
                message="Required Field, Can't be Empty",
                cursor_position=len(document.text)
            )

class BundleValidator(BaseValidator):
    def validate(self, document) -> None:
        super().validate(document)
        ok = re.match(Regex.bundle, document.text)
        if not ok:
            raise ValidationError(
                message='Invalid Bundle ID',
                cursor_position=len(document.text)
            )

class BundleCompleter(Completer):
    def __init__(self, bundles: List) -> None:
        super().__init__()
        self.bundles = bundles
    def get_completions(self, document, complete_event):
        for bundle in self.bundles:
            if bundle.lower().startswith(document.text.lower()):
                yield Completion(bundle, start_position=-len(document.text))


def load_templates(templates_dir: Path) -> Dict[str, Dict[str, Any]]:
    templates_folders = list(templates_dir.glob('*.nic3'))
    if len(templates_folders) < 1:
        raise NoTemplates(f"Niccy can't find templates in [{templates_dir}]")

    templates = {}
    for template_dir in templates_folders:
        template = load_template(template_dir)
        if template:
            templates[template['template_name']] = template
            templates[template['template_name']]['path'] = template_dir
    return templates

def load_template(path: Path) -> Optional[Dict]:
    template_path = path / 'template.json'
    try:
        return json.loads(template_path.read_bytes())
    except OSError:
        return None

def prompts_for_template2(template: Dict[str, Any], bundles: List = []) -> List[Dict]:
    prompts: List[Dict] = []
    for prompt in template['prompts']:
        prompt_keys = TemplatePrompt(
            type = prompt['type'],
            jinja_tag = prompt['jinja_tag'],
            description = prompt['description'],
            required = prompt['required'],
            default = prompt['default'],
            )
        prompts.append(prompt_keys.cc_dict())
    return prompts



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


def process_kill_filter(text) -> Optional[list[str]]:
    if not text:
        return None
    splited = text.split(' ')
    print(splited)
    return splited

def theos_env() -> Path:
    if os.environ.get('THEOS'):
        return Path(os.environ['THEOS'])
    raise EnvironmentError