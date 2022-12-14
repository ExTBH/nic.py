from concurrent.futures import thread
from dataclasses import dataclass
from enum import Enum
import json, os, subprocess, re, shutil
from pathlib import Path
from typing import Dict, List, Optional, Type
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.completion import Completer, Completion
from tempfile import TemporaryDirectory
from cookiecutter.main import cookiecutter
from colorama import Fore
from threading import Thread

class NoTemplates(Exception):
    pass

class Regex:
    filter_project_name = '[^a-zA-Z0-9+.-]'
    bundle = '^([a-zA-Z0-9\\+\\-]+\\.)+[a-zA-Z0-9\\+\\-]+$'


class PromptsTypes(Enum):
    BOOL = "BOOL"
    INTEGER = "INTEGER"
    STRING = "STRING"
    BUNDLE_ID = "BUNDLE_ID"
    BUNDLE_FILTER = "BUNDLE_FILTER"

@dataclass
class TemplatePrompt:
    type: PromptsTypes
    jinja_tag: str
    description: Optional[str]
    required: bool
    default: Optional[str]
    validate: Optional[Type[Validator]] = None # subclasses of Validator
    completer: Optional[Completer] = None

    def __post_init__(self) -> None:
        if self.type == PromptsTypes.BUNDLE_ID:
            self.validate = BundleValidator
            bundles_thread = BundlesFetcher()
            bundles_thread.start()
            self.completer = BundleCompleter(bundles_thread.bundles)
            if not self.description:
                self.description = 'Bundle ID for your Tweak'

        elif self.type == PromptsTypes.BUNDLE_FILTER:
            self.validate = BundleValidator
            if not self.description:
                self.description = 'MobileSubstrate Filter to hook against'

        elif self.jinja_tag == 'KILL_PROCESS':
            if not self.description:
                self.description = 'Applications to Terminate upon installation(space-separated)'
        
        if self.required and not self.validate:
            self.validate = BaseValidator
        if self.jinja_tag == 'AUTHOR' and not self.default:
            self.default = os.getlogin().title()
    @classmethod
    def from_dict(cls, data: Dict) -> "TemplatePrompt":
        
        return cls(
            type=PromptsTypes[data['type']],
            jinja_tag=data['jinja_tag'],
            description=data['description'],
            required=data['required'],
            default=data['default'],
        )

    def to_dict(self) -> Dict:
        cc_dict = {
            'type': self.cc_type(),
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

    def cc_type(self) -> str:
        if self.type in (PromptsTypes.STRING, PromptsTypes.BUNDLE_FILTER, PromptsTypes.BUNDLE_ID):
            return 'input'
        return 'input'
@dataclass
class Template:
    path: Path
    template_name: str
    author: str
    source: str
    prompts: List[TemplatePrompt]

    @classmethod
    def from_path(cls, path: Path) -> "Template":
        data = json.loads(path.read_bytes())
        return cls(
            path=path,
            template_name=data["template_name"],
            author=data["author"],
            source=data["source"],
            prompts=[TemplatePrompt.from_dict(d) for d in data["prompts"]],
        )

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
    def __init__(self, bundles: List[str]) -> None:
        super().__init__()
        self.bundles = bundles
    def get_completions(self, document, complete_event):
        for bundle in self.bundles:
            if bundle.lower().startswith(document.text.lower()):
                yield Completion(bundle, start_position=-len(document.text))


class BundlesFetcher(Thread):
    def __init__(self) -> None:
        super().__init__()
        self.bundles: List[str] = []
    
    def run(self) -> None:
        if os.environ.get('THEOS_DEVICE_IP'):
            host = os.environ['THEOS_DEVICE_IP']
            user = os.environ['THEOS_DEVICE_USER'] if os.environ.get('THEOS_DEVICE_USER') else 'root'
            port = os.environ['THEOS_DEVICE_PORT'] if os.environ.get('THEOS_DEVICE_PORT') else '22'

            session = subprocess.run(['ssh', f'{user}@{host}', '-p', port, 'uicache', '-l'], capture_output=True, text=True)
            if session.returncode != 0:
                print(f'{Fore.YELLOW}{session.stderr}{Fore.RESET}')
                # stop the thread?
            else:
                entries = session.stdout.splitlines()
                for entry in entries:
                    bundle = entry.split(' : ')[0]
                    self.bundles.append(bundle)

def load_templates(templates_dir: Path) -> Dict[str, Template]:
    templates_folders = list(templates_dir.glob('*.nic3'))
    if len(templates_folders) < 1:
        raise NoTemplates(f"Niccy can't find templates in [{templates_dir}]")

    templates = {}
    for template_dir in templates_folders:
        try:
            template = Template.from_path(template_dir / 'template.json')

        except OSError:
            pass

        else:
            templates[template.template_name] = template

    return templates






def build_cc_project(answers: Dict, template_path: Path, clean_name = False) -> None:
    with TemporaryDirectory() as temp_dir:
        if clean_name:
            answers['CLEAN_PROJECT_NAME'] = re.sub(Regex.filter_project_name, '', answers['FULL_PROJECT_NAME'])
        dest_dir = Path(temp_dir) / 'dest'
        shutil.copytree(template_path.parent, dest_dir)

        config_path = Path(dest_dir) / 'cookiecutter.json'
        config_path.write_text(json.dumps(answers))
        cookiecutter(dest_dir.as_posix(), no_input=True)


def theos_env() -> Path:
    if os.environ.get('THEOS'):
        return Path(os.environ['THEOS'])
    raise EnvironmentError
