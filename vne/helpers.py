import gbl
from mininet.cli import CLI
from substrate import SubstrateHost
import networkx as nx
import random


def get_output_port_for_spine_switches(dst_16_bit_subnet):
    """ Rules for spine (layer 1) switches.
    dst_16_bit_subnet: Destination IP subnet (16 bits) in dotted decimal format. Example: '12.0'. """
    leaf_switch = gbl.LEAF_LAYER_IP_SUBNET_x_SWITCH[dst_16_bit_subnet]
    port_of_leaf_switch = gbl.LEAF_SWITCHES.index(leaf_switch) + 1
    return port_of_leaf_switch


def get_output_port_for_leaf_switches_towards_spine(ll_switch, dst_ip):
    """ Rules for leaf (layer 2) switches, where packets are travelling upwards.
    Gets the output port number of leaf switch, for packets that need to be 
    forwarded upwards from the leaf layer, i.e. towards the spine switches.
    ll_switch: Leaf layer switch for which we are finding output port number.
    dst_ip: Destination IP address in dotted decimal format. Example: '12.1.1.0/24'. """
    dst_8_bit_subnet = int(dst_ip.split(".")[0])
    src_8_bit_subnet = int(ll_switch.ip_subnet.split(".")[0])
    # We consider the larger of the src and dst subnets to find the spine layer
    # switch to forward the packet. Reason for doing this (and not just basing
    # the decision off of destination address) is because if we decide the spine
    # layer switch only based on the destination address, then the request & reply
    # packets will not follow the same route. For example, in the topology (sl=3,
    # ll=2, hl=2), if h1 (10.0.0) wants to communicate with h6 (11.0.0), it will
    # communicate via the switch s1_2 (because dst_ip is under 11 subnet). But when
    # h6 sends reply to h1, then the dst_ip is considered of h1, which is under
    # 10 subnet, and would now route via s1_1. Hence, to avoid this problem, we make
    # the decision of selecting spine switch based on the larger of the two addresses.
    subnet = max(dst_8_bit_subnet, src_8_bit_subnet)
    spine_switch = gbl.SPINE_LAYER_IP_SUBNET_x_SWITCH[str(subnet)]
    port = gbl.SPINE_SWITCHES.index(spine_switch) + 1
    return port


def get_output_port_for_leaf_switches_towards_hosts(dst_ip, num_sl_connections):
    """ Rules for leaf (layer 2) switches, where packets are travelling downwards.
    Gets the output port number of leaf switch, for packets that need to be 
    forwarded downwards from the leaf layer, i.e. towards the hosts. 
    dst_ip: Destination IP address in dotted decimal format. 
    num_sl_connections: Number of spine layer connections; i.e. the number of spine layer 
    switches that this leaf layer switch is connected to. In the case of spine leaf 
    topology this will be the number of spine switches since every spine switch is connected 
    to every leaf switch. """
    # Reason for adding `num_sl_connections` is that the first n port numbers (of the
    # leaf layer switch) will be consumed by the connections with spine layer switches.
    return int(dst_ip.split(".")[2]) + 1 + num_sl_connections


def add_flow_ip(net, switch, priority, nw_dst, output_port):
    """ ovs-ofctl command to add flow table entry for specified OpenFlow Switch.
    net: Mininet object.
    switch: OpenFlow Switch in mininet, expected in string format. Example: 's1_2'. 
    nw_dst: Destination IPv4 address for matching the flow.
    output_port: Port number of the switch to output the packet on. """
    command = "ovs-ofctl add-flow {} eth_type=0x0800,priority={},nw_dst={},actions=output:{}".format(
        switch, str(priority), nw_dst, str(output_port))
    CLI.do_sh(net, command)


def get_default_router_for_host(host):
    """ Generate a dummy IP of a default router for every host, such that the 
    default gateway is in the same subnet as the host. 
    host_str: Host expected in string format. Example: 'h1'."""
    ip_split = host.ip_addr.split(".")
    ip_split[-1] = "254"
    return ".".join(ip_split)


def add_arp_entry_for_host(host, net):
    """ Add entry in ARP table of host so that it doesn't send ARP request for 
    the default router. """
    default_router_ip = get_default_router_for_host(host)
    net[host.name].cmd('arp -s {} 11:22:33:44:55:66'.format(default_router_ip))

    for i in range(0, 254):
        ip_split = host.ip_addr.split(".")
        ip_split[-1] = str(i)
        ip_addr = ".".join(ip_split)
        if host.ip_addr != ip_addr:
            net[host.name].cmd('arp -s {} 11:22:33:44:55:66'.format(ip_addr))


def add_arp_flood_entry(switch, net):
    """ Adding ARP flood entries for specified switch. """
    command = "ovs-ofctl add-flow {} eth_type=0x0806,priority=0,actions=FLOOD".format(
        switch.name)
    CLI.do_sh(net, command)


def show_flow_table_entries(net):
    """ Shows the flow table entries of all the spine and leaf layer switches. """
    for switch in gbl.SPINE_SWITCHES + gbl.LEAF_SWITCHES + gbl.HOST_SWITCHES:
        print("The flow table entries in switch {}:\n".format(switch.name))
        CLI.do_sh(net, "ovs-ofctl dump-flows {}".format(switch.name))
        print("-----------------------------------------------------------------\n")

    for switch in gbl.SPINE_SWITCHES + gbl.LEAF_SWITCHES + gbl.HOST_SWITCHES:
        print(switch.name, switch.next_port_number)


def update_cpu_limits_of_substrate_hosts_after_vnr_mapping(net):
    """ Update the cpu limits for substrate hosts after VNR mapping is performed."""
    for host in gbl.HOSTS:
        cpu_f_host = host.cpu_limit / SubstrateHost.cpu_all_hosts
        net[host.name].setCPUFrac(f=cpu_f_host, sched='cfs')
        print("\nUpdated the cpu limit of {} to {}%, i.e. {} units.".format(
            host.name, f'{cpu_f_host:.4f}', host.cpu_limit))


def create_vnrs(num_vnrs=5, min_nodes=2, max_nodes=6, probability=0.4, min_cpu=10, max_cpu=50, min_bw=1, max_bw=5):
    # Note: If you want a connected graph, do not give a probability of less than 0.1.
    random.seed(gbl.SEED)

    vnrs = []
    print("\nCreating VNRs...")
    for req in range(num_vnrs):
        num_nodes = random.randint(min_nodes, max_nodes)
        g = nx.erdos_renyi_graph(
            num_nodes, probability, seed=123, directed=False)

        # Generating random values for CPU values and link bandwidths specified in given ranges.
        cpu_reqs = []
        link_reqs = []
        for _ in g.nodes():
            cpu_req = random.randint(min_cpu, max_cpu)
            cpu_reqs.append(cpu_req)
        for edge in g.edges():
            bw_req = random.randint(min_bw, max_bw)
            link_reqs.append((edge[0]+1, edge[1]+1, bw_req))

        vnrs.append((num_nodes, cpu_reqs, link_reqs))
        print("VNR {}: {}".format(req, (num_nodes, cpu_reqs, link_reqs)))
    return vnrs


def rank_vnrs_in_order(vnr_list):
    """ Orders/ranks VNRs in the VNR list to decide which VNR to serve before others.
    Currently we are ranking them based on the ascending order of revenue generated
    from them, but the flexibility to add other strategies of ranking can be plugged in here."""
    return _rank_vnrs_in_ascending_order_of_revenue(vnr_list)


def _rank_vnrs_in_ascending_order_of_revenue(vnr_list):
    """ Orders/ranks VNRs in ascending order of their revenue. Revenue of a VNR is 
    computed by summing the node weights (i.e. CRB requirements of all virtual host) and 
    the edge weights (i.e. bandwidth requirement of all the links in the VNR)"""
    def _get_node_weights(vnr):
        (_, cpu_reqs, _) = vnr
        return sum(cpu_reqs)

    def _get_edge_weights(vnr):
        (_, _, link_reqs) = vnr
        edge_weights = 0
        for (_, _, wt) in link_reqs:
            edge_weights += wt
        return edge_weights

    def _get_revenue(vnr):
        return _get_node_weights(vnr) + _get_edge_weights(vnr)

    vnr_list.sort(key=lambda vnr: _get_revenue(vnr))
    print("\n\nAfter ordering/ranking VNRs by ascending order of revenue...")
    for vnr in vnr_list:
        print(vnr)
    return vnr_list


def get_bandwidth_limit_between_host_pair(host_pair, COPY_SWITCH_PAIR_x_BW):
    """ Gets the bandwidth limit between given pair of hosts.
    Between any pair of hosts, there are multiple hops of switches that any packet goes 
    through if it wants to travel from one host to the other. The bandwidth between the
    pair of hosts is the minimum of all the bandwidths of the links encountered in
    that path.

    host_pair: (Host, Host)
        The pair of hosts between bandwidth limit is supposed to be found.
    """
    # First rearrange the host_pair such that the smaller host value comes first, because
    # we have stored values in COPY_SWITCH_PAIR_x_BW in such a way only.
    (h1, h2) = host_pair
    if int(h1.name[1:]) > int(h2.name[1:]):
        host_pair = (h2, h1)

    bw_limits = []

    # The bandwidth limit between given host pair is the minimum of the bandwidths between
    # every link on the path between the two hosts.
    path = gbl.PATH_BETWEEN_HOSTS[host_pair]
    # Start with assigning max possible value
    bw_limit = 10000000
    for each_link in path:
        # Find that switch pair in the COPY_SWITCH_PAIR_x_BW dict.
        for (s1_name, s2_name), bw in COPY_SWITCH_PAIR_x_BW.items():
            if each_link[0].name == s1_name and each_link[1].name == s2_name:
                bw_limit = min(bw_limit, bw)
                bw_limits.append(bw)
                break
    # print("Bandwidth values on path between hosts {} & {}: {}".format(
    #     h1.name, h2.name, bw_limits))
    return bw_limit
