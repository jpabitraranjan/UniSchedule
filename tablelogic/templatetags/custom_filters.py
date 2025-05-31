from django import template


register = template.Library()



@register.filter
def section_and_optional_batch(assignment):
    # Fetch section and batch attributes
    section = getattr(assignment, 'section', None)
    batch = getattr(assignment, 'batch', None)

    # Return formatted string based on whether section or batch is available
    if section and batch:
        return f"{section.name} - {batch.name}"
    elif section:
        return f"{section.name}"
    elif batch:
        return f"Batch {batch.name}"
    else:
        return "N/A"

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
