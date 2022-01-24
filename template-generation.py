from jinja2 import Template
from rich.traceback import install
from rich.console import Console
import yaml
import ipaddress
import glob
import os


if __name__ == "__main__":
    install(show_locals=True)
    console = Console()

    path = "/*.yaml"
    for filename in glob.glob(path):
        with open(filename, "r") as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
    if "template" in config.keys():
        template = config["template"]
    else:
        template = r"""
stash-agent-options true;
{% if global_options is not none +%}
{{ global_options }}
{% endif %}
  shared-network network {% raw %}{{% endraw %}
    {% for network in networks %}
    subnet {{ network['ip'] }} netmask {{ network['netmask'] }} {% raw %}{{% endraw %}
      option routers {{ network['gateway'] }};
      option subnet-mask {{ network['netmask'] }};
      option broadcast-address {{ network['broadcast'] }};
    {% raw %}}{% endraw %}
    {% endfor %}
    subnet 0.0.0.0 netmask 0.0.0.0 {} #this is required so dhcpd listens on the random-assigned docker interface address.
{% raw %}}{% endraw %}
{% for client in clients %}
host {{ client['circuit_id_stripped'] }} {% raw %}{{% endraw %}
  host-identifier option agent.circuit-id "{{ client['circuit_id'] }}";
  fixed-address {{ client['ip'] }};
{% raw %}}{% endraw %}
{% endfor %}
"""
    if "global-options" in config.keys():
        global_options = config["global-options"]
    else:
        global_options = None
    networks = []
    for vlan, cfg_network in config["networks"].items():
        network = dict()
        network["gateway"] = cfg_network.split("/")[0]
        network["ip"] = str(
            ipaddress.ip_network(cfg_network, strict=False).network_address
        )
        network["broadcast"] = str(
            ipaddress.ip_network(cfg_network, strict=False).broadcast_address
        )
        network["netmask"] = str(
            ipaddress.ip_network(cfg_network, strict=False).netmask
        )
        networks.append(network)
    clients = list()
    for item in config["clients"].splitlines():
        circuit_id, ip = item.split(",")
        client = dict()
        client["circuit_id"] = circuit_id
        client["circuit_id_stripped"] = circuit_id.replace("/", "")
        client["ip"] = ip
        clients.append(client)
    t = Template(template)

    with open("/etc/dhcp/dhcpd.conf", "w") as f:
        f.write(
            t.render(
                global_options=global_options,
                clients=clients,
                networks=networks,
            )
        )
