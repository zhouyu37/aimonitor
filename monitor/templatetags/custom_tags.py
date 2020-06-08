#_*_coding:utf-8_*_

from django import template
from monitor import models
from django.utils.safestring import mark_safe

register=template.Library()

@register.simple_tag
def get_trigger_severity_color(alert_obj):
    severity_choices = {
        1:'white',
        2:'yellow',
        3:'orange',
        4:'red',
        5:'darkred',
    }
    return severity_choices.get(alert_obj.trigger.severity) or ''