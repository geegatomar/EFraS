from main_classes import Switch, Host
import random
import gbl
from mininet.topo import Topo
from mininet.link import TCLink
import helpers as hp
from mininet.cli import CLI
import output as op
import copy


class SubstrateHost(Host):
    """
    A class to represent the substrate hosts used in the spine-leaf topology network being 
    created. Inherits from Host class.

    Attributes
    ----------
    cpu_all_hosts : int
        This is a class attribute, hence common for all objects of this class, i.e. common 
        value for all substrate hosts representing how much total CPU they have alogether 
        combined. 
        Starting with some percentage of CPU reserved (here 1000), then will keep adding 
        the cpu_limits of all substrate hosts to this variable. Reason for doing this is 
        so that at all times, 100% of CPU is not totally given to all mininet hosts combined 
        as that leads to values less that expected on running runCpuLimitTest().
    virtual_hosts_mapped : List[VNRVirtualHost]
        List of virtual hosts that are mapped onto this substrate host; updated upon serving 
        the VNR requests.
    """

    cpu_all_hosts = 1000

    def __init__(self, host_name, ip_addr, cpu_limit):
        super().__init__(host_name, ip_addr, cpu_limit)
        self.virtual_hosts_mapped = []
        self.original_cpu_limit = cpu_limit


def generate_topology(sl_factor, ll_factor, hl_factor):
    """ Generates the switches for spine (layer 1) and leaf (layer 2) layers. 
    Generates the hosts, and does the IP addressing of all hosts.
    sl_factor: Number of switches in spine layer (sl).
    ll_factor: Number of leaf layer (ll) switches under the subnet of each spine switch.
    hl_factor: Number of host layer (hl) hosts under (connected to) each leaf switch. """

    # If your requirement is to generate the same physical substrate network over
    # multiple iterations, then keep the random.seed value same for each of the iterations.
    # But if you want to generate new substrate network each time, replace the below line
    # with: `random.seed(gbl.SEED)``
    random.seed(gbl.CFG["seed_for_substrate_network"])

    # Starting IP addressing of hosts with "10.0.0.0"
    first_ip_subnet = 10
    for i in range(0, sl_factor):
        # The subnet for layer 1 (spine) switches. For example layer_1_subnet="10"
        # denotes 10.0.0.0/8 subnet, meaning any nodes with first 8 bits of IP address
        # as 10 will come under this switch's network. Name given to this switch will
        # be s1_1 (denoting layer 1, switch 1).
        layer_1_subnet = str(first_ip_subnet + i)
        spine_switch = Switch("s1_{}".format(i + 1), layer_1_subnet)
        gbl.SPINE_SWITCHES.append(spine_switch)
        gbl.SPINE_LAYER_IP_SUBNET_x_SWITCH[layer_1_subnet] = spine_switch

        # For every spine layer switch, add 'll_factor' leaf layer switches.
        for j in range(0, ll_factor):
            # The subnet for layer 2 (leaf) switches. For example, layer_2_subnet="10.0"
            # denotes the 10.0.0.0/16 subnet, meaning any nodes with first 16 bits
            # matching this will come under this switch's network. Name given to this
            # switch is s2_1 (denoting layer 2, switch 1).
            layer_2_subnet = layer_1_subnet + ".{}".format(j)
            leaf_switch = Switch("s2_{}".format(
                ll_factor*i + j + 1), layer_2_subnet)
            gbl.LEAF_SWITCHES.append(leaf_switch)
            gbl.LEAF_LAYER_IP_SUBNET_x_SWITCH[layer_2_subnet] = leaf_switch

            # For every leaf layer switch, add 'hl_factor' hosts under it.
            for k in range(0, hl_factor):
                # For denoting host, we use first 24 bit subnets. For example,
                # "10.0.0.0/24". Host naming here is simply 'h1' denoting first host.
                host_layer_subnet = layer_2_subnet + ".{}".format(k)
                host_name = "h{}".format(
                    hl_factor*ll_factor*i + hl_factor*j + k + 1)

                # Randomly generating cpu limits for substrate host in given range
                cpu_limit = random.randrange(
                    gbl.CFG["substrate"]["cpu_limit_min"], gbl.CFG["substrate"]["cpu_limit_max"])
                host = SubstrateHost(
                    host_name, host_layer_subnet + ".0/24", cpu_limit)
                SubstrateHost.cpu_all_hosts += cpu_limit

                op.output_dict["pre_resource"] += cpu_limit
                op.output_dict["total_nodes"] += 1

                host_switch = Switch("sh{}".format(
                    hl_factor*ll_factor*i + hl_factor*j + k + 1), host_layer_subnet)
                gbl.HOSTS.append(host)
                gbl.HOSTNAME_x_HOST[host_name] = host
                gbl.HOST_SWITCHES.append(host_switch)
                gbl.HOST_LAYER_IP_SUBNET_x_SWITCH[host_layer_subnet] = host_switch
                host.host_switch_attached = host_switch
                leaf_switch.host_ips_under_this_switch.append(
                    host_layer_subnet + ".0")


class SpineLeafSubstrateNetwork(Topo):
    def __init__(self):
        Topo.__init__(self)

        # If your requirement is to generate the same physical substrate network over
        # multiple iterations, then keep the random.seed value same for each of the iterations.
        # But if you want to generate new substrate network each time, replace the below line
        # with: `random.seed(gbl.SEED)``
        random.seed(gbl.CFG["seed_for_substrate_network"])

        # Add spine switches (layer 1 switches in spine-leaf topology), named s2_XYZ.
        for spine_switch in gbl.SPINE_SWITCHES:
            self.addSwitch(spine_switch.name)

        # Add leaf switches (layer 2 switches in spine-leaf topology), named s2_XYZ.
        for leaf_switch in gbl.LEAF_SWITCHES:
            self.addSwitch(leaf_switch.name)

        # Add host switches
        for host_switch in gbl.HOST_SWITCHES:
            self.addSwitch(host_switch.name)

        # Add hosts (final layer in spine-leaf topology), named hXYZ.
        for host in gbl.HOSTS:
            cpu_percentage = host.cpu_limit / host.cpu_all_hosts
            self.addHost(
                host.name, cpu=cpu_percentage, ip=host.ip_addr, defaultRoute='via {}'.format(hp.get_default_router_for_host(host)))

        # Add links between every spine layer and leaf layer switches.
        # Everytime link is added, update the next_port_addr for the switch.
        for spine_switch in gbl.SPINE_SWITCHES:
            for leaf_switch in gbl.LEAF_SWITCHES:
                bw_random = random.randrange(gbl.CFG["substrate"]["spine_to_leaf_links"]
                                             ["bw_limit_min"], gbl.CFG["substrate"]["spine_to_leaf_links"]["bw_limit_max"])
                self.addLink(spine_switch.name,
                             leaf_switch.name, cls=TCLink, bw=bw_random)
                gbl.SWITCH_PAIR_x_BW[(
                    spine_switch.name, leaf_switch.name)] = bw_random
                gbl.SWITCH_PAIR_x_BW[(
                    leaf_switch.name, spine_switch.name)] = bw_random
                spine_switch.next_port_number += 1
                leaf_switch.next_port_number += 1
                op.output_dict["pre_resource"] += bw_random
                op.output_dict["total_links"] += 1

        # Add links between leaf layer switches and host switches.
        # Everytime link is added, update the next_port_addr for the switch.
        host_index = 0
        for leaf_switch in gbl.LEAF_SWITCHES:
            for i in range(gbl.NUM_HOSTS_PER_LEAF_SWITCH):
                host_switch = gbl.HOST_SWITCHES[host_index]
                bw_random = random.randrange(gbl.CFG["substrate"]["leaf_to_host_links"]
                                             ["bw_limit_min"], gbl.CFG["substrate"]["leaf_to_host_links"]["bw_limit_max"])
                self.addLink(host_switch.name, leaf_switch.name,
                             cls=TCLink, bw=bw_random)
                gbl.SWITCH_PAIR_x_BW[(
                    host_switch.name, leaf_switch.name)] = bw_random
                gbl.SWITCH_PAIR_x_BW[(
                    leaf_switch.name, host_switch.name)] = bw_random
                host_index += 1
                leaf_switch.next_port_number += 1
                host_switch.next_port_number += 1
                op.output_dict["pre_resource"] += bw_random
                op.output_dict["total_links"] += 1

        # Add link between the host switches and the hosts.
        for (host_switch, host) in zip(gbl.HOST_SWITCHES, gbl.HOSTS):
            self.addLink(host_switch.name, host.name)
            host_switch.next_port_number += 1
            # Note that we DON'T count this as a link in the total_links as its a
            # 'modified spine leaf' architecture and the last layer's links are mainly
            # used for implementation purposes. And, since we are counting the total
            # links in the spine leaf topology, we only count the links between
            # spine-leaf and leaf-host, which has already been done above.
            op.output_dict["total_links"] += 0

        # Populate the original switch pair bandwidth values. The variable `ORIGINAL_SWITCH_PAIR_x_BW`
        # shall not update, whereas `SWITCH_PAIR_x_BW` dynamically changes as VNRs are served.
        gbl.ORIGINAL_SWITCH_PAIR_x_BW = copy.deepcopy(gbl.SWITCH_PAIR_x_BW)


def add_flow_entries_for_substrate_network(net):
    """ Adding flow table entries for the substrate network."""
    # Add flow entries for all leaf switches.
    for ll_switch in gbl.LEAF_SWITCHES:
        # For every leaf layer switch, add flow table entries for the upward flow,
        # i.e. packets flowing towards the spine switches.
        for ss in gbl.SPINE_SWITCHES:
            sl_ip_subnet = ss.ip_subnet
            ip_subnet_8_bit = sl_ip_subnet + ".0.0.0/8"
            port = hp.get_output_port_for_leaf_switches_towards_spine(
                ll_switch, ip_subnet_8_bit)
            hp.add_flow_ip(net, ll_switch.name, 3000, ip_subnet_8_bit, port)
        # For every leaf layer switch, add flow table entries for the downward flow,
        # i.e. packets flowing towards the hosts.
        for host_ip in ll_switch.host_ips_under_this_switch:
            port = hp.get_output_port_for_leaf_switches_towards_hosts(
                host_ip, len(gbl.SPINE_SWITCHES))
            # Hosts within that subnet shall be given higher priority in the
            # flow table. For example in the topology (sl=3, ll=2, h=2), if
            # h5 wants to communicate with h6. They both lie under switch s2_3,
            # and when s2_3 gets the packet destined for h6, it shall send it
            # to h6 directly instead of forwarding to s1_2 (which is what the
            # above sl rule says). Hence if host is reachable from that switch,
            # give it higher prioirty (here 3001) in the flow table.
            hp.add_flow_ip(net, ll_switch.name, 3001, host_ip + '/24', port)

    # Add flow entries for all spine switches.
    for sl_switch in gbl.SPINE_SWITCHES:
        # For every spine layer switch, add flow table entries for the downward
        # flow towards the leaf switches.
        for ll in gbl.LEAF_SWITCHES:
            ll_ip_subnet = ll.ip_subnet
            ip_subnet_16_bit = ll_ip_subnet + ".0.0/16"
            port = hp.get_output_port_for_spine_switches(ll_ip_subnet)
            hp.add_flow_ip(net, sl_switch.name, 3000, ip_subnet_16_bit, port)

    for (hl_switch, host) in zip(gbl.HOST_SWITCHES, gbl.HOSTS):
        ip_add = host.ip_addr.split('/')[0]
        # Obtaining the host mac address.
        host_mac = str.rstrip(net[host.name].cmd(
            "ip -a link | grep ether | awk '{print $2}'"))
        CLI.do_sh(net, "ovs-ofctl add-flow {} eth_type=0x0800,priority={},nw_dst={},actions=mod_dl_dst:{},output:{}".format(
            hl_switch.name, 3001, ip_add, host_mac, 2))
        CLI.do_sh(
            net, "ovs-ofctl add-flow {} eth_type=0x0800,priority=3000,actions=output:1".format(hl_switch.name))


def populate_path_between_hosts():
    """ Populates the exact path between every pair of hosts in the network in the
    spine leaf topology. This function basically populates the gbl.PATH_BETWEEN_HOSTS 
    global variable, which is then used in the vnr mapping algorithms.
    """
    # Going upwards from host layer. Adding the first host switch link in path.
    for i in range(len(gbl.HOSTS)):
        for j in range(i + 1, len(gbl.HOSTS)):
            host_pair = (gbl.HOSTS[i], gbl.HOSTS[j])
            gbl.PATH_BETWEEN_HOSTS[host_pair] = []
            gbl.PATH_BETWEEN_HOSTS[host_pair].append(
                (gbl.HOSTS[i], gbl.HOSTS[i].host_switch_attached))

    # Going upwards from host switches layer. Adding next link, i.e. host switch
    # and leaf switch link in the path.
    for host_pair, path in gbl.PATH_BETWEEN_HOSTS.items():
        current_host_switch = path[-1][1]
        host_switch_ip_subnet = current_host_switch.ip_subnet
        next_leaf_switch_subnet = ".".join(
            host_switch_ip_subnet.split(".")[0:2])
        next_leaf_switch = gbl.LEAF_LAYER_IP_SUBNET_x_SWITCH[next_leaf_switch_subnet]
        gbl.PATH_BETWEEN_HOSTS[host_pair].append(
            (current_host_switch, next_leaf_switch))

    # Now depending on the dst IP address, we either go up a layer to the spine switches
    # in the path, or else directly go down back to host switches.
    for (src_h, dst_h), path in gbl.PATH_BETWEEN_HOSTS.items():
        current_leaf_switch = path[-1][1]
        leaf_switch_ip_subnet = current_leaf_switch.ip_subnet
        dst_h_under_ip_subnet = ".".join(dst_h.ip_addr.split(".")[0:2])
        # If destination host is under this leaf switch, then packet doesn't go to
        # spine leaf layer at all.
        if dst_h_under_ip_subnet != leaf_switch_ip_subnet:
            # Update the next spine switch in the path. Note that the spine leaf switch is
            # selected based on the destination host's IP subnet. The same logic is used
            # in `get_output_port_for_leaf_switches_towards_spine` function in `helpers` module.
            next_spine_switch_subnet = dst_h_under_ip_subnet.split(".")[0]
            next_spine_switch = gbl.SPINE_LAYER_IP_SUBNET_x_SWITCH[next_spine_switch_subnet]
            gbl.PATH_BETWEEN_HOSTS[(src_h, dst_h)].append(
                (current_leaf_switch, next_spine_switch))

    # Starting the downwards journey. Need to find the next spine-leaf switch path if
    # and only if spine path was added in previous block of code.
    for (src_h, dst_h), path in gbl.PATH_BETWEEN_HOSTS.items():
        current_switch = path[-1][1]
        if current_switch not in gbl.SPINE_SWITCHES:
            continue
        dst_h_under_ip_subnet = ".".join(dst_h.ip_addr.split(".")[0:2])
        next_leaf_switch = gbl.LEAF_LAYER_IP_SUBNET_x_SWITCH[dst_h_under_ip_subnet]
        gbl.PATH_BETWEEN_HOSTS[(src_h, dst_h)].append(
            (current_switch, next_leaf_switch))

    # Now every host pair has the latest leaf layer switch updated, and we continue
    # the downward journey, to get the next host switch in the path.
    for (src_h, dst_h), path in gbl.PATH_BETWEEN_HOSTS.items():
        current_leaf_switch = path[-1][1]
        next_host_switch_subnet = ".".join(dst_h.ip_addr.split(".")[0:3])
        next_host_switch = gbl.HOST_LAYER_IP_SUBNET_x_SWITCH[next_host_switch_subnet]
        gbl.PATH_BETWEEN_HOSTS[(src_h, dst_h)].append(
            (current_leaf_switch, next_host_switch))

    # Finally the last link between host layer switch and destination host is added.
    for (src_h, dst_h), path in gbl.PATH_BETWEEN_HOSTS.items():
        current_host_switch = path[-1][1]
        gbl.PATH_BETWEEN_HOSTS[(src_h, dst_h)].append(
            (current_host_switch, dst_h))

    print("\nPopulated the path between all host pairs...")
    for (src_h, dst_h), path in gbl.PATH_BETWEEN_HOSTS.items():
        print("({}, {}): {}".format(src_h.name, dst_h.name,
                                    [(x.name, y.name) for (x, y) in path]))
