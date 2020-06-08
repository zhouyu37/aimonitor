from monitor import models
import json
import time

from django.core.exceptions import ObjectDoesNotExist
class ClientHandler(object):
    def __init__(self,client_id):
        self.client_id = client_id
        self.client_configs = {
            "services":{}
        }
    def fetch_configs(self):
        try:
            host_obj = models.Host.objects.get(id=self.client_id)
            template_list = list(host_obj.templates.select_related())
            for host_group in host_obj.host_groups.select_related():
                template_list.extend(host_group.templates.select_related())
            print(template_list)
            for template in template_list:
                print(template.services.select_related())
                for service in template.services.select_related():
                    print(service)
                    self.client_configs["services"][service] = [service.plugin_name,service.interval]
        except ObjectDoesNotExist:
            pass
        return self.client_configs

class StatusSerializer(object):
    def __init__(self,request,redis):
        self.request = request
        self.redis = redis

    def by_hosts(self):
        host_obj_list = models.Host.objects.all()
        host_data_list=[]
        for h in host_obj_list:
            host_data_list.append(self.single_host_info(h))
        return host_data_list

    def single_host_info(self,host_obj):
        data = {
            'id':host_obj.id,
            'name':host_obj.name,
            'ip_addr':host_obj.ip_addr,
            'status':host_obj.get_status_display(),
            'uptime':None,
            'last_update':None,
            'total_services':None,
            'ok_nums':None,
        }
        uptime=self.get_host_uptime(host_obj)
        self.get_triggers(host_obj)
        if uptime:
            print('uptime',uptime)
            data['uptime']=uptime[0]['uptime']
            data['last_update']=time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(uptime[1]))

        data['triggers']=self.get_triggers(host_obj)
        return data


    def get_host_uptime(self,host_obj):
        redis_key='StatusData_%s_uptime'%host_obj.id
        last_data_point=self.redis.lrange(redis_key,-1,-1)
        if last_data_point:
            last_data_point,last_update=json.dumps(last_data_point[0])
            return last_data_point,last_update

    def get_triggers(self,host_obj):
        trigger_keys=self.redis.keys("host_%s_trigger_*"%host_obj.id)
        trigger_dic={
            1:[],
            2:[],
            3:[],
            4:[],
            5:[]
        }
        for trigger_key in trigger_keys:
            trigger_data=self.redis.get(trigger_key)
            print("trigger_key",trigger_key)
            if trigger_key.decode().endswith("None"):
                trigger_dic[4].append(json.loads(trigger_data.decode()))
            else:
                trigger_id=trigger_key.decode().split('_')[-1]
                trigger_obj=models.Trigger.objects.get(id=trigger_id)
                trigger_dic[trigger_obj.severity].append(json.loads(trigger_data.decode()))

        return trigger_dic



class GroupStatusSerializer(object):
    def __init__(self,request,redis):
        self.request = request
        self.redis = redis

    def get_all_groups_status(self):
        data_set=[]
        group_objs=models.HostGroup.objects.all()

        for group in group_objs:
            group_data={
                'hosts':[],
                'services':[],
                'triggers':[],
                'events':{
                        'diaster':[],
                        'high':[],
                        'average':[],
                        'warning':[],
                        'info':[],
                },
                'last_update':None,
            }

            host_list = group.host_set.all()

            template_list = []
            service_list = []

            template_list.extend(group.templates.all())
            for host_obj in host_list:
                template_list.extend(host_obj.templates.select_related())

            template_list=set(template_list)
            for template_obj in template_list:
                service_list.extend(template_obj.services.all())

            service_list=set(service_list)
            group_data['hosts']=[{'id':obj.id} for obj in set(host_list)]
            group_data['services'] = [{'id':obj.id} for obj in set(service_list)]
            group_data['group_id'] =group.id
            data_set.append(group_data)
        print(json.dumps(data_set))

def get_host_traggers(host_obj):
    triggers = []
    for template in host_obj.templates.select_related():
        triggers.extend(template.triggers.select_related())
    for group in host_obj.host_groups.select_related():
        for template in group.templates.select_related():
            triggers.extend(template.triggers.select_related())
    return set(triggers)
