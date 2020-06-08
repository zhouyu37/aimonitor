from monitor import models

class GraphGenerator2(object):
    def __init__(self,request,redis_obj):
        self.request = request
        self.redis = redis_obj
        self.host_id = self.request.GET.get('host_id')
        self.time_range=self.request.GET.get('time_range')

    def get_host_graph(self):
        host_obj=models.Host.objects.get(id=self.host_id)
        service_data_dic = {}
        template_list=list(host_obj.templates.select_related())
        for g in host_obj.host_groups.select_related():
            template_list.extend(g.templates.select_related())
        template_list=set(template_list)

        for template in template_list:
            for service in template.services.select_related():
                service_data_dic[service.id] = {
                    'name':service.name,
                    'index_data':{},
                    'has_sub_service':service.has_sub_service,
                    'raw_data':[],
                    'items':[item.key for item in service.items.select_related()],
                }

        print(service_data_dic)

        for service_id,val_dic in service_data_dic:
            service_redis_key = "StatusData_%s_%s_%s"%(host_obj.id,val_dic['name'],self.time_range)
            service_raw_data = self.redis.lrange(service_redis_key,0,-1)
            service_raw_data=[item.decode() for item in service_raw_data]
            service_data_dic[service_id]['raw_data'] = service_raw_data

        return service_data_dic


