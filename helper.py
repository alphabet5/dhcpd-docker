from napalm import get_network_driver
from rich.traceback import install
from rich.console import Console
from napalm.base.helpers import canonical_interface_name
from ciscoconfparse import CiscoConfParse
import re
import os
import argparse

if __name__ == "__main__":
    install(show_locals=True)
    console = Console()
    description = """
This is a helper script that can configure the circuit-id data insertion on switches.

It can also export a list of the clients. (If there is an arp entry for the device on one of the switches listed.)

If arp entries cannot be found on any of the switches, interfaces that are currently 'up' will have blank addresses.

Example:
```text
switch_hostnameGi1/0/1,192.168.1.123
switch_hostnameGi1/0/2,192.168.1.124
switch_hostnameGi1/0/3,
switch_hostnameGi1/0/4,192.168.2.123
```

It requires /switch_list.txt (filename within the container can be specified with --sw-list) to be mapped to the docker container. The format should be a list of IP's.

Example:
```text
192.168.1.1
192.168.1.2
192.168.1.3
```

Napalm is used to connect to the switches. Environment variables SW_USER, and SW_PASS are required for switch credentials.
Currently only Cisco IOS is supported. 

    """
    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--configure",
        help="Configure the interfaces on the list of switches for inserting the circuit-id.",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--export-clients",
        help="TODO: Export a list of circuit-id's and ip's for use in the DHCP server.",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--sw-user",
        help="Optional: Switch Username. Can also be added by ENV SW_USER",
        type=str,
        default="",
    )
    parser.add_argument(
        "--sw-pass",
        help="Optional: Switch Password. Can also be added by ENV SW_PASS",
        type=str,
        default="",
    )
    parser.add_argument(
        "--sw-list",
        help="Optional: Switch list /directory/filename.txt. Defaults to /switch_list.txt.",
        type=str,
        default="/switch_list.txt",
    )
    args = vars(parser.parse_args())
    if args["configure"] or args["export_clients"]:
        with open(args["sw_list"], "r") as f:
            switches = f.readlines()
        if args["sw_user"] == "":
            username = os.environ["SW_USER"]
        else:
            username = args["sw_user"]
        if args["sw_pass"] == "":
            password = os.environ["SW_PASS"]
        else:
            password = args["sw_pass"]
        if args["export-clients"]:
            console.print("Currently not implemented. :( Pull requests welcome. :)")
        if args["configure"]:
            for switch in switches:
                cfg = """
ip dhcp snooping
ip dhcp snooping vlan 1-4094
"""
                driver = get_network_driver("ios")
                device = driver(switch, username, password)
                device.open()
                configs = device.get_config()
                parse = CiscoConfParse(configs["running"].splitlines(), syntax="ios")
                hostname = parse.find_objects(r"^hostname")[0].text.replace(
                    "hostname ", ""
                )
                interfaces_raw = parse.find_objects(r"^interface")
                interfaces = list()
                interface_config_remove = dict()
                for interface in interfaces_raw:
                    if "vlan" not in interface.text.lower():
                        if " switchport mode access" in [
                            c.text for c in interface.children
                        ]:
                            snooping_vlans = list()
                            for child in interface.children:
                                if "switchport access vlan" in child.text:
                                    vlan = re.match(
                                        r".*vlan (\d+).*", child.text
                                    ).group(1)
                                if "ip dhcp snooping vlan" in child.text:
                                    snooping_vlans.append(
                                        re.match(r".*vlan (\d+).*", child.text).group(1)
                                    )
                            if [vlan] != snooping_vlans:
                                snooping_vlans.remove(vlan)
                                interface_config_remove[interface.text] = list()
                                for vlan_to_remove_circuit_id in snooping_vlans:
                                    interface_config_remove[interface.text].append(
                                        "no ip dhcp snooping vlan "
                                        + vlan_to_remove_circuit_id
                                        + " information option"
                                    )

                        interfaces.append(
                            canonical_interface_name(
                                interface.text.replace("interface ", "")
                            )
                        )

                for interface in interfaces:
                    cfg = (
                        cfg
                        + f"""
interface {interface}
ip dhcp snooping vlan 2 information option format-type circuit-id string switch01Gi1/0/3
"""
                    )
                    if interface in interface_config_remove:
                        cfg = cfg + "\n" + "\n".join(interface_config_remove[interface])
                device.load_merge_candidate(config=cfg)
                console.print(device.compare_config())
                accept = console.input(
                    "Accept config merge for " + switch + "? (y/n) [n]"
                )
                if accept.lower() in ["y", "ye", "yes"]:
                    device.commit_config()
                else:
                    device.discard_config()
