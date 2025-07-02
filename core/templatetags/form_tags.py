from django import template

register = template.Library()

@register.filter(name='get_field')
def get_field(form, field_name):
    return form[field_name]

@register.filter(name='add_classes')
def add_classes(field, classes):
    return field.as_widget(attrs={'class': classes})

@register.simple_tag(name='render_field')
def render_field(form, field_name, classes=''):
    field = form[field_name]
    return field.as_widget(attrs={
        'class': f'w-full rounded-lg border-gray-300 focus:border-primary focus:ring-primary {classes}',
        'placeholder': field.label
    })