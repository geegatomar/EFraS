import gbl
from mininet.cli import CLI
from substrate import SubstrateHost


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
    the default router. 
    host_str: Host expected in string format. Example: 'h1'."""
    default_router_ip = get_default_router_for_host(host)
    net[host.name].cmd('arp -s {} 11:22:33:44:55:66'.format(default_router_ip))

    for i in range(0, 254):
        ip_split = host.ip_addr.split(".")
        ip_split[-1] = str(i)
        ip_addr = ".".join(ip_split)
        if host.ip_addr != ip_addr:
            net[host.name].cmd('arp -s {} 11:22:33:44:55:66'.format(ip_addr))


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
