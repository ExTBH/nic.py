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

prompts = NicInternal.prompts_for_template(templates[template['name']])

answers = prompt(prompts)

path = templates[template['name']].path
cc_config = NicInternal.build_cc_project(answers, path)
