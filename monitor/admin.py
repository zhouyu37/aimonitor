# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from monitor import models
# Register your models here.

class HostAdmin(admin.ModelAdmin):
    list_display = ('id','name','ip_addr','status')
    filter_horizontal = ('host_groups','templates')

admin.site.register(models.Host,HostAdmin)
