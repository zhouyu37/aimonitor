# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from monitor import auth
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from django.db import models

# Create your models here.

class Host(models.Model):
    name = models.CharField(max_length=64,unique=True)
    ip_addr = models.GenericIPAddressField(unique=True)
    host_groups=models.ManyToManyField('HostGroup',blank=True)
    templates=models.ManyToManyField("Template",blank=True)
    monitored_by_choices=(
        ('agent','AGENT'),
        ('snmp','SNMP'),
        ('wget','WGET')
    )
    monitored_by=models.CharField(u'monitor_way',max_length=32,choices=monitored_by_choices)
    status_choices=(
        (1,'Online'),
        (2,'Down'),
        (3,'Unreachable'),
        (4,'Offline'),
        (5,'Problem'),
    )
    host_alive_check_interval=models.IntegerField(u"hostalivecheckinterval",default=30)
    status=models.IntegerField(u'status',choices=status_choices,default=1)
    memo=models.TextField(u'remarks',blank=True,null=True)

    def __str__(self):
        return self.name

class HostGroup(models.Model):
    name=models.CharField(max_length=64,unique=True)
    templates=models.ManyToManyField("Template",blank=True)
    memo = models.TextField(u'remarks', blank=True, null=True)

    def __str__(self):
        return self.name

class ServiceIndex(models.Model):
    name=models.CharField(max_length=64)
    key=models.CharField(max_length=64)
    data_type_choices=(
        ('int','int'),
        ('float','float'),
        ('str','string'),
    )
    data_type=models.CharField(u'datatype',max_length=32,choices=data_type_choices,default='int')
    memo = models.CharField(u"remarks", max_length=128, blank=True, null=True)

    def __str__(self):
        return "%s.%s"%(self.name,self.key)

class Service(models.Model):
    name=models.CharField(u'servicename',max_length=64,unique=True)
    interval=models.IntegerField(u'monitorinterval',default=60)
    plugin_name=models.CharField(u'pluginname',max_length=64,default='n/a')
    items=models.ManyToManyField('ServiceIndex',verbose_name=u'itemlist',blank=True)
    has_sub_service=models.BooleanField(default=False,verbose_name=u"whetherhassubservice")
    memo = models.CharField(u"remarks", max_length=128, blank=True, null=True)

    def __str__(self):
        return self.name

class Template(models.Model):
    name=models.CharField(u'template',max_length=64,unique=True)
    services=models.ManyToManyField('Service',verbose_name=u"servicelist")
    triggers=models.ManyToManyField('Trigger',verbose_name=u'triggerlist',blank=True)

    def __str__(self):
        return self.name

class TriggerExpression(models.Model):
    trigger=models.ForeignKey('Trigger',verbose_name=u"undertrigger")
    service=models.ForeignKey('Service',verbose_name=u'relatedservice')
    service_index=models.ForeignKey('ServiceIndex',verbose_name=u'relatedservicekey')
    specified_index_key=models.CharField(verbose_name=u'onlymoniterspecifiedkey',max_length=64,blank=True,null=True)
    operator_type_choices=(
        ('eq','='),
        ('lt','<'),
        ('gt','>'),
    )
    operator_type=models.CharField(u'operatortype',choices=operator_type_choices,max_length=32)
    data_calc_type_choices=(
        ('avg','Avg'),
        ('max','Max'),
        ('hit','Hit'),
        ('last','Last'),
    )
    data_calc_func=models.CharField(u"datadealtype",choices=data_calc_type_choices,max_length=32)
    data_calc_args=models.CharField(u'funcargs',help_text="ifgt2usercommathefirstistime",max_length=64)
    threshold=models.IntegerField(u'threshold')
    logic_type_choices=(('or','OR'),('and','AND'))
    logic_type=models.CharField(u'logicrelationship',choices=logic_type_choices,max_length=16,blank=True,null=True)

    def __str__(self):
        return "%s %s(%s(%s))"%(self.service_index,self.operator_type,self.data_calc_func,self.data_calc_args)

class Trigger(models.Model):
    name=models.CharField(u'trigger',max_length=32)
    severity_choices=(
        (1,'Info'),
        (2,'Warning'),
        (3,'Error'),
    )
    severity=models.IntegerField(u'monitorlevel',choices=severity_choices)
    enabled=models.BooleanField(default=True)
    memo = models.CharField(u"remarks", max_length=128, blank=True, null=True)

    def __str__(self):
        return "<service:%s,severity:%s>"%(self.name,self.get_severity_display())

class Action(models.Model):
    name=models.CharField(max_length=64,unique=True)
    host_groups = models.ManyToManyField('HostGroup',blank=True)
    hosts=models.ManyToManyField('Host',blank=True)
    triggers=models.ManyToManyField('Trigger',blank=True,help_text=u'whichtriggerswanttobeacted')
    interval=models.IntegerField(u'shijianjiange',default=300)
    recover_notice=models.BooleanField(u'guzhanghuifuhoufasongxiaoxi',default=True)
    recover_subject=models.CharField(max_length=128,blank=True,null=True)
    recover_message=models.TextField(blank=True,null=True)
    enabled=models.BooleanField(default=True)

    def __str__(self):
        return self.name

class ActionOperation(models.Model):
    name=models.CharField(max_length=32)
    step=models.SmallIntegerField(u'dincigaojing',default=1,help_text="none")
    action_type_choices=(
        ('email','Email'),
        ('script','Script'),
    )
    action_type=models.CharField(u'dongzuoleixing',choices=action_type_choices,default='email',max_length=32)
    notifiers=models.ManyToManyField('UserProfile',verbose_name='tongzhiduixiang',blank=True)
    _msg_format = '''Host({hostname},{ip}) service({service_name}) has issue,msg:{msg}'''
    msg_format=models.TextField(u'xiaoxigeshi',default=_msg_format)

    def __str__(self):
        return self.name

class Maintenance(models.Model):
    name=models.CharField(max_length=32,unique=True)
    hosts=models.ManyToManyField('Host',blank=True)
    host_groups=models.ManyToManyField('HostGroup',blank=True)
    content=models.TextField(u'weihuneirong')
    start_time=models.DateTimeField()
    end_time=models.DateTimeField()

    def __str__(self):
        return self.name

class EventLog(models.Model):
    event_type_choices=(
        (0,'baojingshijian'),
        (1,'weihushijian'),
    )
    event_type=models.SmallIntegerField(choices=event_type_choices,default=0)
    host=models.ForeignKey('Host')
    trigger=models.ForeignKey('Trigger',blank=True,null=True)
    log=models.TextField(blank=True,null=True)
    date=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "host%s %s"%(self.host,self.log)

class UserProfile(auth.AbstractBaseUser, auth.PermissionsMixin):
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,

    )
    password = models.CharField(_('password'), max_length=128,
                                help_text=mark_safe('''<a class='btn-link' href='password'>resetpass</a>'''))
    phone = models.BigIntegerField(blank=True,null=True)
    weixin = models.CharField(max_length=64,blank=True,null=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(
        verbose_name='staff status',
        default=True,
        help_text='Designates whether the user can log into this admin site.',
    )
    name = models.CharField(max_length=32)
    #role = models.ForeignKey("Role",verbose_name="权限角色")

    memo = models.TextField('备注', blank=True, null=True, default=None)
    date_joined = models.DateTimeField(blank=True, null=True, auto_now_add=True)

    USERNAME_FIELD = 'email'
    # REQUIRED_FIELDS = ['name','token','department','tel','mobile','memo']
    REQUIRED_FIELDS = ['name']

    def get_full_name(self):
        # The user is identified by their email address
        return self.email

    def get_short_name(self):
        # The user is identified by their email address
        return self.email

    def __str__(self):  # __str__ on Python 2
        return self.email

    def has_perms(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True


    @property
    def is_superuser(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin


    objects = auth.UserManager()

    class Meta:
        verbose_name = 'account'
        verbose_name_plural = 'account'

