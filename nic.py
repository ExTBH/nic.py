from pathlib import Path
from PyInquirer.prompt import prompt
import NicInternal

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
answers = prompt([t.to_dict() for t in prompts])

path = templates[template['name']].path
cc_config = NicInternal.build_cc_project(answers, path)
