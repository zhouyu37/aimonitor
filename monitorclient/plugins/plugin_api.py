#_*_coding:utf-8_*_

from linux import sysinfo,load,cpu_mac,cpu,memory,network,host_alive

def LinuxSysInfo():
    return sysinfo.collect()

def get_linux_cpu():
    return cpu.monitor()

def host_alive_check():
    return host_alive.monitor()

def GetMacCPU():
    return cpu_mac.monitor()

def GetNetworkStatus():
    return network.monitor()

def get_memory_info():
    return memory.monitor()

def get_linux_load():
    return load.monitor()