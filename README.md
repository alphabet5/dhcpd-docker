# dhcpd-docker
 ISC DHCP Server Docker container.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

This container is used as a dhcp server for port-persistent DHCP on Cisco Catlyst switches.

## Requirements

- A list of circuit-id's and addresses.
  ```text
  sw01Gi1/0/3,192.168.1.50
  sw02Gi1/0/1,192.168.2.123
  ```
- Interfaces with valid IP addresses in each network for each vlan on the host.
- The docker container running with 'host' networking.
- A docker host that supports a trunk network interface. (Docker running in WSL, VMWare Workstation, VMWare Fustion, etc will likely not work. ESXi works fine with a proper trunk port group.)
- Switches configured with ip dhcp snooping to insert option-82 information. 

### Example Switch Configuration:

```text
switch01#sh run | s dhcp
ip dhcp snooping vlan 1-4094
ip dhcp snooping

switch01#sh run int Gi1/0/3
interface GigabitEthernet1/0/3
 switchport access vlan 2
 switchport mode access
 spanning-tree portfast edge
 spanning-tree bpduguard enable
 ip dhcp snooping vlan 2 information option format-type circuit-id string switch01Gi1/0/3
end
```

# Usage

In order to use this, your docker host will need to have an interface on each vlan that the DHCP server will be serving.

Each interface should be configured with a valid IP and gateway for the network.

### Example Ubuntu VM Netplan Config:

```text
user@dhcp-server~$ cat /etc/netplan/00-installer-config.yaml
network:
  ethernets:
    ens33: {}
  vlans:
    vlan.2:
      id: 2
      link: ens33
      addresses:
      - 192.168.2.254/24
    vlan.3:
      id: 3
      link: ens33
      addresses:
      - 192.168.3.254/24
    
```

### Example config.yaml

```yaml
subnet-options: | #Optional, gets added to the beginning of the subnet config.
  default-lease-time -1;
  max-lease-time -1;
  option domain-name-servers 192.168.1.1, 1.1.1.1;
  option domain-name "domain.com";
  option tftp-server-name tftp.server.hostname.or.ip;
  option bootfile-name "tmboot64.bin";
networks:
# vlan: gateway/subnet
  2: 192.168.2.1/24
  3: 192.168.3.1/24
clients: | #circuit-id,ip
  sw02Gi1/0/3,192.168.2.50
  sw01Gi1/0/3,192.168.3.50
template: | #Optional. This replaces the whole jinja2 config template and can cause errors if it's not valid.
  stash-agent-options true;
  {% for network in networks %}
  subnet {{ network['ip'] }} netmask {{ network['subnetmask'] }} {% raw %}{{% endraw %}
    default-lease-time -1;
    max-lease-time -1;
    {% if domain_name is not none +%}
    option domain-name "{{ domain_name }}";
    {% endif %}
    {% if domain_name_servers is not none +%}
    option domain-name-servers {{ nameservers }};
    {% endif %}
    option routers {{ network['gateway'] }};
    option subnet-mask {{ network['subnetmask'] }};
    option broadcast-address {{ network['broadcast'] }};
  {% raw %}}{% endraw %}
  {% endfor %}

  {% for client in clients %}
  host {{ client['circuit_id'] }} {% raw %}{{% endraw %}
    host-identifier option agent.circuit-id "{{ client['circuit_id_raw'] }}";
    fixed-address {{ client['ip'] }};
  {% raw %}}{% endraw %}
  {% endfor %}
```

### Example Docker Command

```bash
docker run -d \
  --name=dhcpd \
  --net=host \
  -v /home/user/config.yaml:/config.yaml \
  alphbet5/dhcpd
```

## Helper Functions

By default, if /*.yaml (config file) exists, /etc/dhcp/dhcpd.conf will be overwritten with the template based on the configuration.

If you want to manually map a dhcpd.conf file, do not map a /*.yaml file. 

### Example With Custom dhcpd.conf:

```bash
docker run -d \
  --name=dhcpd \
  --net=host \
  -v /home/user/dhcpd.conf:/etc/dhcp/dhcpd.conf \
  alphabet5/dhcpd
```

The helper function can do two things:

- Apply updates to switch interfaces to add dhcp snooping and circuit-id information. (See Example Switch Configuration above)
- Print out a client list based on the currently connected devices. (Devices not in the arp table for any switches, or interfaces that are not up will not be listed.)

### Helper Function Usage

```bash
docker run -it --rm --net=bridge alphabet5/dhcpd python3.9 /helper.py --help
usage: helper.py [-h] [--configure] [--export-clients] [--sw-user SW_USER] [--sw-pass SW_PASS] [--sw-list SW_LIST]

This is a helper script that can configure the circuit-id data insertion on switches.

It can also export a list of the clients. (If there is an arp entry for the device on one of the switches listed.)

If arp entries cannot be found on any of the switches, interfaces that are currently 'up' will have blank addresses.

Example:
'''text
switch_hostnameGi1/0/1,192.168.1.123
switch_hostnameGi1/0/2,192.168.1.124
switch_hostnameGi1/0/3,
switch_hostnameGi1/0/4,192.168.2.123
'''

It requires /switch_list.txt (filename within the container can be specified with --sw-list) to be mapped to the docker container. The format should be a list of IP's.

Example:
'''text
192.168.1.1
192.168.1.2
192.168.1.3
'''

Napalm is used to connect to the switches. Environment variables SW_USER, and SW_PASS are required for switch credentials.
Currently only Cisco IOS is supported. 

    

optional arguments:
  -h, --help         show this help message and exit
  --configure        Configure the interfaces on the list of switches for inserting the circuit-id.
  --export-clients   Export a list of circuit-id's and ip's for use in the DHCP server.
  --sw-user SW_USER  Optional: Switch Username. Can also be added by ENV SW_USER
  --sw-pass SW_PASS  Optional: Switch Password. Can also be added by ENV SW_PASS
  --sw-list SW_LIST  Optional: Switch list /directory/filename.txt. Defaults to /switch_list.txt.
```
