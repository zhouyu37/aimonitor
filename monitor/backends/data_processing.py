import time
from monitor import models
import pickle,json,time
from aimonitor import settings
from monitor.backends import redis_conn
import operator

class DataHandler(object):
    def __init__(self,django_settings,connect_redis=True):
        self.django_settings = django_settings
        self.poll_interval = 3
        self.config_update_interval = 120
        self.config_last_loading_time= time.time()
        self.global_monitor_dic = {}
        self.exit_flag = False
        if connect_redis:
            self.redis = redis_conn.redis_conn(django_settings)

    def looping(self):
        self.update_or_load_configs()
        count = 0
        while not self.exit_flag:
            print("looping %s" % count)
            count +=1
            if time.time() - self.config_last_loading_time > self.config_update_interval:
                self.update_or_load_configs()
            if self.global_monitor_dic:
                for h,config_dic in self.global_monitor_dic.items():
                    for service_id,val in config_dic['service'].items():
                        service_obj,last_monitor_time = val
                        if time.time() - last_monitor_time >= service_obj.interval:
                            self.global_monitor_dic[h]['services'][service_obj.id][1] = time.time()
                            self.data_point_validation(h,service_obj)
                        else:
                            next_monitor_time = time.time()-last_monitor_time-service_obj.interval
                            print("service %s next monitor is %s"%(service_obj.name,next_monitor_time))
                    if time.time() - self.global_monitor_dic[h]['status_last_check'] > 10:
                        trigger_redis_key = "host_%s_trigger"%(h.id)
                        trigger_keys = self.redis.keys(trigger_redis_key)
                        if len(trigger_keys) == 0:
                            h.status = 1
                            h.save()
            time.sleep(self.poll_interval)

    def data_point_validation(self,host_obj,service_obj):
        service_redis_key = "StatusData_%s_%s_latest" % (host_obj.id,service_obj.name)
        latest_data_point = self.redis.lrange(service_redis_key,-1,-1)
        if latest_data_point:
            latest_data_point = json.loads(latest_data_point[0].decode())
            print("latest data point %s" % latest_data_point)
            latest_service_data,last_report_time = latest_data_point
            monitor_interval = service_obj.interval + self.django_settings.REPORT_LATE_TOLERANCE_TIME
            if time.time() - last_report_time > monitor_interval:
                no_data_secs = time.time() - last_report_time
                msg='''some thing must be wrong with client %s because havenot recieve data of service %s for %s  s interval is %s'''%(host_obj.ip_)
                self.trigger_notifier(host_obj=host_obj,trigger_id=None,positive_expressions=None,msg=msg)
                if service_obj.name == 'uptime':
                    host_obj.status = 3
                    host_obj.save()
                else:
                    host_obj.status = 5
                    host_obj.save()
        else:
            msg='''no data for service %s host %s at all...'''%(service_obj.name,host_obj.name)
            self.trigger_notifier(host_obj=host_obj, trigger_id=None, positive_expressions=None, msg=msg)
            host_obj.status = 5
            host_obj.save()


    def trigger_notifier(self,host_obj,trigger_id,positive_expressions,redis_obj=None,msg=None):
        if redis_obj:
            self.redis=redis_obj
        msg_dic = {
            'host_id':host_obj.id,
            'trigger_id':trigger_id,
            'positive_expressions':positive_expressions,
            'msg':msg,
            'time':time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),
            'start_time':time.time(),
            'duration':None,
        }
        self.redis.publish(self.django_settings.TRIGGER_CHAN,pickle.dumps(msg_dic))

        trigger_redis_key = "host_%s_trigger_%s"%(host_obj.id,trigger_id)
        old_trigger_data = self.redis.get(trigger_redis_key)
        if old_trigger_data:
            old_trigger_data = old_trigger_data.decode()
            trigger_startime=json.loads(old_trigger_data)['start_time']
            msg_dic['start_time'] = trigger_startime
            msg_dic['duration'] = round(time.time()-trigger_startime)
        self.redis.set(trigger_redis_key,json.dumps(msg_dic),300)

    def load_service_data_and_calulating(self,host_obj,trigger_obj,redis_obj):
        self.redis = redis_obj
        calc_sub_res_list = []
        positive_expressions = []
        expression_res_string = ''
        for expression in trigger_obj.triggerexpression_set.select_related().order_by("id"):
            print(expression,expression.logic_type)
            expression_process_obj = ExpressionProcess(self,host_obj,expression)
            single_expression_res = expression_process_obj.process()
            if single_expression_res:
                calc_sub_res_list.append(single_expression_res)
                if single_expression_res['expression_obj'].logic_type:
                    expression_res_string+=str(single_expression_res['calc_res'])+' '+single_expression_res['expression_obj'].logic_type+' '
                else:
                    expression_res_string += str(single_expression_res['calc_res'])+' '

                if single_expression_res['calc_res'] == True:
                    single_expression_res['expression_obj'] = single_expression_res['expression_obj'].id
                    positive_expressions.append(single_expression_res)
        print("whole trigger res:",trigger_obj.name,expression_res_string)
        if expression_res_string:
            trigger_res = eval(expression_res_string)
            if trigger_res:
                self.trigger_notifier(host_obj,trigger_obj.id,positive_expressions,msg=trigger_obj.name)





    def update_or_load_configs(self):
        all_enabled_hosts = models.Host.objects.all()
        for h in all_enabled_hosts:
            if h not in self.global_monitor_dic:
                self.global_monitor_dic[h] = {'services':{},'triggers':{}}
            service_list = []
            trigger_list = []
            for group in h.host_groups.select_related():
                for template in group.templates.select_related():
                    service_list.extend(template.services.select_related())
                    trigger_list.extend(template.triggers.select_related())
                for service in service_list:
                    if service.id not in self.global_monitor_dic[h]['services']:
                        self.global_monitor_dic[h]['services'][service.id] = [service,0]
                    else:
                        self.global_monitor_dic[h]['services'][service.id][0] = service
                for trigger in trigger_list:
                    self.global_monitor_dic[h]['triggers'][trigger.id] = trigger

            for template in h.templates.select_related():
                service_list.extend(template.services.select_related())
                trigger_list.extend(template.triggers.select_related())
            for service in service_list:
                if service.id not in self.global_monitor_dic[h]['services']:
                    self.global_monitor_dic[h]['services'][service.id] = [service, 0]
                else:
                    self.global_monitor_dic[h]['services'][service.id][0] = service
            for trigger in trigger_list:
                self.global_monitor_dic[h]['triggers'][trigger.id] = trigger

        self.config_last_loading_time = time.time()
        return True


class ExpressionProcess(object):
    def __init__(self,main_ins,host_obj,expression_obj,specified_item=None):
        self.host_obj = host_obj
        self.expression_obj = expression_obj
        self.main_ins = main_ins
        self.service_redis_key = "StatusData_%s_%s_latest" %(host_obj.id,expression_obj.service.name)
        self.time_range = self.expression_obj.data_calc_args.split(',')[0]

    def load_data_from_redis(self):
        time_in_sec = int(self.time_range) * 60
        approximate_data_points = (time_in_sec + 60)/self.expression_obj.service.interval
        data_range_raw=self.main_ins.redis.lrange(self.service_redis_key,-int(approximate_data_points ),-1)
        approximate_data_range = [json.loads(i.decode()) for i in data_range_raw]
        data_range = []
        for point in approximate_data_range:
            val,saving_time = point
            if time.time() -saving_time < time_in_sec:
                data_range.append(point)
        print(data_range)
        return data_range

    def process(self):
        data_list = self.load_data_from_redis()
        data_calc_func = getattr(self,'get_%s'% self.expression_obj.data_calc_func)
        single_expression_calc_res = data_calc_func(data_list)
        if single_expression_calc_res:
            res_dic = {
                'calc_res':single_expression_calc_res[0],
                'calc_res_val':single_expression_calc_res[1],
                'expression_obj':self.expression_obj,
                'service_item':single_expression_calc_res[2],
            }
            return res_dic
        else:
            return False

    def get_avg(self,data_set):
        clean_data_list = []
        clean_data_dic = {}
        for point in data_set:
            val,save_time = point
            if val:
                if 'data' not in val:
                    clean_data_list.append(val[self.expression_obj.service_index.key])
                else:
                    for k,v in val['data'].items():
                        if k not in clean_data_dic:
                            clean_data_dic[k] = []
                        clean_data_dic[k].append(v[self.expression_obj.service_index.key])

        if clean_data_list:
            clean_data_list = [float(i) for i in clean_data_list]
            avg_res = sum(clean_data_list)/len(clean_data_list)
            return [self.judge(avg_res),avg_res,None]
        elif clean_data_dic:
            for k,v in clean_data_dic.items():
                clean_v_list = [float(i) for i in  v]
                avg_res = 0 if sum(clean_v_list) == 0 else sum(clean_v_list)/len(clean_v_list)
                if self.expression_obj.specified_index_key:
                    if k == self.expression_obj.specified_index_key:
                        calc_res = self.judge(avg_res)
                        if calc_res:
                            return [calc_res,avg_res,k]
                else:
                    calc_res=self.judge(avg_res)
                    if calc_res:
                        return [calc_res,avg_res,k]
            else:
                return [False,avg_res,k]
        else:
            return [False,None,None]

    def judge(self,calculated_val):
        calc_func = getattr(operator,self.expression_obj.operator_type)
        return calc_func(calculated_val,self.expression_obj.threshold)