TARGET := iphone:clang:latest:7.0
{% if cookiecutter.KILL_PROCESS %}
INSTALL_TARGET_PROCESSES = {{ cookiecutter.KILL_PROCESS }}
{% endif %}

include $(THEOS)/makefiles/common.mk

TWEAK_NAME = {{cookiecutter.CLEAN_PROJECT_NAME}}

{{cookiecutter.CLEAN_PROJECT_NAME}}_FILES = Tweak.x
{{cookiecutter.CLEAN_PROJECT_NAME}}_CFLAGS = -fobjc-arc

include $(THEOS_MAKE_PATH)/tweak.mk
