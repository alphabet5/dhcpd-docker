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
- A core switch with valid IP addresses in each network for each vlan that needs dhcp.
- Docker

### Example Core Switch Configuration:

```text
service dhcp 
# Doesn't show up in 'sh run' FYI.

ip dhcp-relay source-interface Vlan1 
#Vlan1 is on the same network as the DHCP server. This is the address/interface the DHCP server will send the responses to be relayed back to the clients.

ip dhcp snooping vlan 1-4094
ip dhcp snooping
```

#### Interface configurations 

##### Core switch interface configurations

```text
!
interface Vlan2
 ip address 192.168.2.1 255.255.255.0
 ip helper-address 192.168.1.250 
 # helper-address is the address of the DHCP server.
end
```

##### Trunk Link Configuration to Layer 2 Access Switches

```text
!
interface Gi1/0/1
 switchport mode trunk
 switchport trunk native vlan 999
 ip dhcp snooping trust
end
```

##### DHCP Server Interface

```text
!
interface GigabitEthernet1/0/47
 switchport mode access
 spanning-tree portfast edge
 spanning-tree bpduguard enable
 ip dhcp snooping trust
end
```
##### End Device Interfaces

```text
!
interface GigabitEthernet1/0/2
 switchport access vlan 2
 switchport mode access
 spanning-tree portfast edge
 spanning-tree bpduguard enable
 ip dhcp snooping vlan 2 information option format-type circuit-id string prsw01Gi1/0/2
end
!
interface GigabitEthernet1/0/3
 switchport access vlan 3
 switchport mode access
 shutdown
 spanning-tree portfast edge
 spanning-tree bpduguard enable
 ip dhcp snooping vlan 3 information option format-type circuit-id string prsw01Gi1/0/3
end
!
interface GigabitEthernet1/0/4
 switchport access vlan 4
 switchport mode access
 spanning-tree portfast edge
 spanning-tree bpduguard enable
 ip dhcp snooping vlan 4 information option format-type circuit-id string prsw01Gi1/0/4
end
```

#### Layer 2 Access Switch Configuration

```text
ip dhcp snooping vlan 1-4094
ip dhcp snooping
```

```text
!
interface GigabitEthernet1/0/2
 switchport access vlan 2
 switchport mode access
 spanning-tree portfast edge
 spanning-tree bpduguard enable
 ip dhcp snooping vlan 2 information option format-type circuit-id string prsw02Gi1/0/2
end
!
interface GigabitEthernet1/0/3
 switchport access vlan 3
 switchport mode access
 spanning-tree portfast edge
 spanning-tree bpduguard enable
 ip dhcp snooping vlan 3 information option format-type circuit-id string prsw02Gi1/0/3
end
!
interface GigabitEthernet1/0/4
 switchport access vlan 4
 switchport mode access
 spanning-tree portfast edge
 spanning-tree bpduguard enable
 ip dhcp snooping vlan 4 information option format-type circuit-id string prsw02Gi1/0/4
end
```

## Usage

### Example config.yaml

```yaml
global-options: | #Optional, gets added before the subnet config.
  default-lease-time -1;
  max-lease-time -1;
  option domain-name-servers 192.168.1.1, 1.1.1.1;
  option domain-name "domain.com";
  option tftp-server-name "192.168.1.250";
  option bootfile-name "tmboot64.bin";
networks:
# vlan: gateway/subnet
  2: 192.168.2.1/24
  3: 192.168.3.1/24
  4: 192.168.4.1/24
  5: 192.168.5.1/24
  6: 192.168.6.1/24
clients: | #circuit-id,ip
  prsw01Gi1/0/2,192.168.2.12
  prsw01Gi1/0/3,192.168.3.13
  prsw01Gi1/0/4,192.168.4.14
  prsw01Gi1/0/5,192.168.5.15
  prsw01Gi1/0/6,192.168.6.16
  prsw02Gi1/0/2,192.168.2.22
  prsw02Gi1/0/3,192.168.3.23
  prsw02Gi1/0/4,192.168.4.24
  prsw02Gi1/0/5,192.168.5.25
  prsw02Gi1/0/6,192.168.6.26
template: | #Optional. This replace the whole config template and can cause errors if it's not valid.
  stash-agent-options true;
  {% if global_options is not none +%}
  {{ global_options }}
  {% endif %}
    shared-network network {% raw %}{{% endraw %}
      subnet 0.0.0.0 netmask 0.0.0.0 {} #this is required so dhcpd listens on the random-assigned docker interface address.
      {% for network in networks %}
      subnet {{ network['ip'] }} netmask {{ network['netmask'] }} {% raw %}{{% endraw %}
        option routers {{ network['gateway'] }};
        option subnet-mask {{ network['netmask'] }};
        option broadcast-address {{ network['broadcast'] }};
      {% raw %}}{% endraw %}
  {% endfor %}
  {% raw %}}{% endraw %}
  {% for client in clients %}
  host {{ client['circuit_id_stripped'] }} {% raw %}{{% endraw %}
    host-identifier option agent.circuit-id "{{ client['circuit_id_raw'] }}";
    fixed-address {{ client['ip'] }};
  {% raw %}}{% endraw %}
  {% endfor %}
```

### Example Docker Command

```bash
docker run -d \
  -p 67:67/udp \
  -v /home/user/dhcpd.yaml:/dhcpd.yaml \
  alphabet5/dhcpd
```

## Helper Functions

By default, if /*.yaml (config file) exists, /etc/dhcp/dhcpd.conf will be overwritten with the template based on the configuration.

If you want to manually map a dhcpd.conf file, do not map a /*.yaml file. 

### Example With Custom dhcpd.conf:

```bash
docker run -d \
  -p 67:67/udp \
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

## Changelog

### 0.0.1-a1
- Changed subnet-options -> global options, and moved outside the subnet section in the config.
- Updated the documentation to reflect a more typical setup with a core switch acting as a dhcp relay.
    - This allows for kubernetes deployment with a lot simpler networking.
- No more bridged networking with interfaces on each vlan.
- Fixed the /*.yaml check in the entrypoint for config generation.
- Renaming of some variables
- Fixed the jinja2 template.
- Basic testing has passed.
- Applied black formatting to helper.py

