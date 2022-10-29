import os
from pathlib import Path
from PyInquirer.prompt import prompt
from dataclasses import dataclass, asdict
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


bundles = []
# if os.environ.get("THEOS_DEVICE_IP"):
#     bundles = NicInternal.bundles_over_ssh('192.168.100.3')


prompts = NicInternal.prompts_for_template2(templates[template['name']], bundles)

answers = prompt(prompts)

path: Path = templates[template['name']]['path']
cc_config = NicInternal.build_cc_project(answers, path)

print(answers)