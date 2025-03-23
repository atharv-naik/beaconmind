from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

@register.filter(name='getattr')
def getattr_filter(obj, attr_name):
    """Fetches an attribute of an object dynamically."""
    return getattr(obj, attr_name, None)
