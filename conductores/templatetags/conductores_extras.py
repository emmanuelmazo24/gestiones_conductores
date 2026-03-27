from django import template

register = template.Library()

@register.filter
def dictget(dictionary, key):
    """Returns the value for a given key from a dictionary."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def split(value, key):
    """Returns the string split by the key."""
    if isinstance(value, str):
        return value.split(key)
    return value
