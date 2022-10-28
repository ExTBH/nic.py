import os
from PyInquirer.prompt import prompt
import NicInternal

theos = NicInternal.theos_env()

templates, templates_paths = NicInternal.load_templates(theos + '/vendor/templates')



template_selection = {
    'type': 'list',
    'name': 'template',
    'message': 'Select a Template:',
    'choices': templates
}


template = prompt(template_selection)

bundles = []
if os.environ.get("THEOS_DEVICE_IP"):
    bundles = NicInternal.bundles_over_ssh('192.168.100.3')

path_for_selection = templates_paths[templates.index(template['template'])]

prompts = NicInternal.prompts_for_template(path_for_selection, bundles)
answers = prompt(prompts)

cc_config = NicInternal.build_cc_project(answers, path_for_selection)

