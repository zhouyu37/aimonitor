from django.conf.urls import url

from monitor import views

urlpatterns = [
    url(r'^groups/status/$',views.hostgroups_status,name='get_hostgroups_status'),
    url(r'^hosts/status/$',views.hosts_status,name='get_hosts_status'),
    url(r'^graphs/$',views.get_graphs,name='get_graphs'),
    url(r'^client/service/report/$',views.service_data_report),
    url(r'^client/config/(\d+)/$',views.client_configs),
]