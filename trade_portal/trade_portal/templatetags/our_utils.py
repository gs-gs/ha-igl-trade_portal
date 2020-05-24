import json

from django import template

register = template.Library()


@register.filter
def json_render(obj):
    def escape_script_tags(unsafe_str):
        # seriously: http://stackoverflow.com/a/1068548/8207
        return unsafe_str.replace('</script>', '<" + "/script>')

    return escape_script_tags(json.dumps(obj, indent=2))
