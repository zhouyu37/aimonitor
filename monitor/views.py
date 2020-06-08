# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.shortcuts import render,HttpResponse
from monitor import models
from aimonitor import settings
from monitor.backends import redis_conn
from monitor.backends import data_optimization
from monitor.backends import data_processing
from monitor import serializer
from monitor import graphs
from django.views.decorators.csrf import csrf_exempt
# Create your views here.

REDIS_OBJ=redis_conn.redis_conn(settings)

def dashboard(request):
    return render(request,'monitor/dashboard.html')

def triggers(request):
    return render(request,'monitor/triggers.html')

def hosts(request):
    hostlist=models.Host.objects.all()
    print("hosts",hostlist)
    return render(request,'monitor/hosts.html',{'hostlist':hostlist})

def host_detail(request,host_id):
    host_obj=models.Host.objects.get(id=host_id)
    return render(request,'monitor/host_detail.html',{'host_obj':host_obj})


def host_groups(request):
    return HttpResponse("host_groups")

def hosts_status(request):
    hosts_data_serializer=serializer.StatusSerializer(request,REDIS_OBJ)
    hosts_data=hosts_data_serializer.by_hosts()
    return HttpResponse(json.dumps(hosts_data))

def trigger_list(request):
    host_id = request.GET.get('by_host_id')
    host_obj=models.Host.objects.get(id=host_id)
    alert_list=host_obj.eventlog_set.all().order_by('-date')
    return render(request,'monitor/trigger_list.html',locals())

def get_graphs(request):
    graphs_generator = graphs.GraphGenerator2(request,REDIS_OBJ)
    graphs_data=graphs_generator.get_host_graph()
    print("graphs_data",graphs_data)
    return HttpResponse(json.dumps(graphs_data))


def hostgroups_status(request):
    group_serializer = serializer.GroupStatusSerializer(request,REDIS_OBJ)
    group_serializer.get_all_groups_status()

    return HttpResponse("ss")

@csrf_exempt
def service_data_report(request):
    if request.method == 'POST':
        print("----->",request.POST)
        try:
            print('host=%s,service=%s'%(request.POST.get('client_id'),request.POST.get('service_name')))
            data=json.loads(request.POST['data'])
            client_id=request.POST.get('client_id')
            service_name=request.POST.get('service_name')
            data_saveing_obj = data_optimization.DataStore(client_id,service_name,data,REDIS_OBJ)

            host_obj=models.Host.objects.get(id=client_id)
            service_triggers = get_host_traggers(host_obj)

            trigger_handler=data_processing.DataHandler(settings,connect_redis=False)
            for trigger in service_triggers:
                trigger_handler.load_service_data_and_calulating(host_obj,trigger,REDIS_OBJ)
        except ImportError as e:
            print(".....error...::",e)
    return HttpResponse(json.dumps("--report success--"))


def client_configs(request,client_id):
    print("---->",client_id)
    config_obj = serializer.ClientHandler(client_id)
    config = config_obj.fetch_configs()
    if config:
        return HttpResponse(json.dumps(config))


