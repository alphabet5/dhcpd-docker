from jinja2 import Template
import yaml
import ipaddress
import glob


if __name__ == "__main__":
    path = "/*.yaml"
    for filename in glob.glob(path):
        with open(filename, "r") as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
    if "template" in config.keys():
        template = config["template"]
    else:
        template = r"""
stash-agent-options true;
{% for network in networks %}
subnet {{ network['ip'] }} netmask {{ network['subnetmask'] }} {% raw %}{{% endraw %}
  {% if subnet_options is not none +%}
  {{ subnet_options }}
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
"""
    if "subnet-options" in config.keys():
        subnet_options = config["subnet-options"]
    else:
        subnet_options = None
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
        client["ip"] = ip
        client["circuit_id_raw"] = (
            r"\x01\x" + hex(len(circuit_id)).replace("0x", "").zfill(2) + circuit_id
        )
        clients.append(client)
    t = Template(template)

    with open("/etc/dhcp/dhcpd.conf", "w") as f:
        f.write(
            t.render(
                subnet_options=subnet_options,
                clients=clients,
                networks=networks,
            )
        )
