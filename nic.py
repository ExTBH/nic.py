from pathlib import Path
from PyInquirer.prompt import prompt
from colorama import Fore
import NicInternal

header = 'NIC 3.0 New Instance Creator'
print(header)
print( '-' * len(header))
print(f'{Fore.GREEN}NIC will attempt to get bundles from your device over SSH, to make it faster use SSH Keys.{Fore.RESET}')
print( '-' * len(header))

theos = NicInternal.theos_env()

templates = NicInternal.load_templates(theos / 'vendor' / 'templates')


template_selection = {
    'type': 'list',
    'name': 'name',
    'message': 'Select a Template:',
    'choices': templates
}

template = prompt(template_selection)

prompts = templates[template['name']].prompts


is_clean_name = False
for p in prompts:
    if p.jinja_tag == 'CLEAN_PROJECT_NAME':
        is_clean_name = True
        prompts.remove(p)
        break


answers = prompt([t.to_dict() for t in prompts])

path = templates[template['name']].path
cc_config = NicInternal.build_cc_project(answers, path, is_clean_name)
