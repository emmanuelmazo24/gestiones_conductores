from django import template

register = template.Library()

@register.filter
def dictget(dictionary, key):
    """Returns the value for a given key from a dictionary."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
