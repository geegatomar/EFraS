import gbl
from main_classes import Host
from substrate import SubstrateHost
from typing import List
import helpers as hp
from mininet.cli import CLI
import output as op


class VNRVirtualHost(Host):
    """
    A class to represent the vnr virtual hosts in the spine-leaf topology network; which are
    being mapped to some substrate host. Inherits from Host class.

    Attributes
    ----------
    substrate_host : SubstrateHost
        The SubstrateHost object to which this vnr virtual host is mapped in the network.
    host_switch_attached : Switch
        The host switch to which this virtual host is being attached to. It will be the same
        host switch that the substrate host is attached to as well.
    vlan_id: int
        The VLAN identifier, to uniquely identify and differentiate each VNR from another,
        and to ensure isolation between VNRs.
    """

    def __init__(self, vnr_host_name, substrate_host, ip_addr, host_switch, cpu_limit):
        super().__init__(vnr_host_name, ip_addr, cpu_limit)
        self.substrate_host = substrate_host
        self.host_switch_attached = host_switch
        self.vlan_id = 0


class MappedVNR:
    """
    A class to represent the mapped virtual network requests served in the spine-leaf topology network.

    Attributes
    ----------
    substrate_hosts : List[SubstrateHost]
        List of SubstrateHost objects that are used as substrate hosts for the mapping of this VNR.
    virtual_hosts : List[VNRVirtualHost]
        List of VNRVirtualHost objects that have been created as virtual hosts to serve this VNR.
    vnr_number: int
        Virtual Network Request number.
    vlan_id: int
        The VLAN identifier, to uniquely identify and differentiate each VNR from another,
        and to ensure isolation between VNRs. Same as the vnr_number.
    vnr_host_names: List[str]
        List of the VNR substrate host names.
    vnr_links_with_bw: List[Tuple(str, str, int)]
        List of the links along with bandwidth. Each link is represented as a tuple of 
        host name, other host name, and the bandwidth of the link between them.
    """

    def __init__(self, substrate_hosts: List[SubstrateHost], virtual_hosts: List[VNRVirtualHost], vnr_number: int):
        self.substrate_hosts = substrate_hosts
        self.virtual_hosts = virtual_hosts
        self.vnr_number = vnr_number
        self.vlan_id = vnr_number
        self.vnr_host_names = None
        self.vnr_links_with_bw = None

        # Virtual host mapped on substrate hostname.
        self.hostname_x_vh = {}
        for (vh, host) in zip(virtual_hosts, substrate_hosts):
            self.hostname_x_vh[host.name] = vh


def _add_vnr_host_on_substrate_host(net, vnr_host_name: str, substrate_host_name: str, cpu_requirement: int, vlan_id: int):
    """ Add/map a vnr virtual host onto an existing substrate host in the network.
    vnr_host_name: str
        Virtual host name. E.g. 'vnr1_vh2'.
    substrate_host_name: str
        Substrate host name. E.g. 'h1'.
    cpu_requirement: int
        CPU requirement/limit of this virtual host. Must be less than the remaining cpu limit of the 
        underlying substrate host.
    vlan_id: int
        VLAN identifier. Same as the VNR number.
    """
    # Dealing with our code's classes and objects first (i.e. Host, Switch, SubstrateHost, VNRVirtualHost),
    # not that of mininet's objects yet.
    substrate_host = gbl.HOSTNAME_x_HOST[substrate_host_name]
    host_switch = substrate_host.host_switch_attached
    # Assigning IP address for the vnr virtual host. The scheme we are following here for the IP addressing
    # of vnr virtual hosts is to maintain the same /24 subnet as that of the substrate host that they are
    # being mapped onto, and depending on how many virtual hosts have already been mapped, the info of which
    # we get from `next_port_number`, the IP addressing is done. For example, for the substrate host having
    # IP address '10.1.0.0/24', the first virtual host mapped onto it will be given IP address '10.1.0.1',
    # and next '10.1.0.2', and so on.
    x = substrate_host.ip_addr.split(".")
    x[-1] = str(host_switch.next_port_number - 2)
    ip_addr_vnrhost = ".".join(x)
    vnr_host = VNRVirtualHost(
        vnr_host_name, substrate_host, ip_addr_vnrhost, host_switch, cpu_requirement)
    # Updating the virtual hosts mapped for this substrate host.
    substrate_host.virtual_hosts_mapped.append(vnr_host)
    # Adding the vnr virtual host to maintained dict HOSTNAME_x_HOST.
    gbl.HOSTNAME_x_HOST[vnr_host_name] = vnr_host

    # Reducing that much cpu bandwidth from the substrate host, since we just mapped
    # a virtual node on it, and gave it that cpu limit.
    substrate_host.cpu_limit = substrate_host.cpu_limit - cpu_requirement
    if substrate_host.cpu_limit < 0:
        raise Exception(
            "You cannot allocate more cpu limit for the virtual hosts than the cpu limit of this substrate host!")

    cpu_percentage = cpu_requirement / SubstrateHost.cpu_all_hosts

    # Dealing with mininet structures now. Note that here 'vnr_host' is an object of our created class,
    # but 'virtual_host' is in the terms of what mininet will actually understand.
    virtual_host = net.addHost(vnr_host.name, cpu=cpu_percentage, ip=vnr_host.ip_addr + '/24', defaultRoute='via {}'.format(
        hp.get_default_router_for_host(vnr_host)))
    sh_switch = net[host_switch.name]
    link = net.addLink(sh_switch, virtual_host)
    sh_switch.attach(link.intf1)
    net.configHosts()

    # Adding ARP entries
    hp.add_arp_entry_for_host(vnr_host, net)

    # Adding flow table entries for the virtual host along with VLAN logic for isolation of each VNRs from the other.
    # Obtaining the mac address of the virtual host.
    vh_mac = str.rstrip(virtual_host.cmd(
        "ip -a link | grep ether | awk '{print $2}'"))
    # Depending on which in_port the packet comes from, it is assigned a different vlan_id,
    # and this helps in isolation of the VNR's traffic.
    CLI.do_sh(net, 'ovs-ofctl add-flow {} priority=3005,ip,in_port={},dl_vlan=0xffff,actions=mod_vlan_vid:{},output:1'.format(
        host_switch.name, str(host_switch.next_port_number), str(vlan_id)))
    CLI.do_sh(net, 'ovs-ofctl add-flow {} priority=3005,ip,nw_dst={},dl_vlan={},actions=strip_vlan,mod_dl_dst:{},output:{}'.format(
        host_switch.name, vnr_host.ip_addr, str(vlan_id), vh_mac, str(host_switch.next_port_number)))

    # Increment because one more link was added to this host switch, since virtual host was added.
    host_switch.next_port_number += 1

    return substrate_host, vnr_host


def _add_tc_htb(net, vhost_name: str, bandwidth_list: List[int], dst_ip_list: List[str]):
    """ Add traffic control, with HTB (Hierarchical Token Bucket) filtering qdisc.
    vhost_name: str
        Virtual host name. E.g. 'vnr1_vh2'.
    bandwidth_list: List[int]
        List of bandwidths to assign between this virtual host and all the other virtual hosts
        to which it has a link in the VNR.
    dst_ip_list: List[str]
        List of destination IP addresses of all the other virtual hosts to which this vitual host
        has a direct link in the VNR. The tc filtering here is being done based on the 
        destination IP address.
    """
    print("Adding tc htb for {}; bandwidths: {}, dst_ip_list: {}.".format(
        vhost_name, bandwidth_list, dst_ip_list))
    vhost = net[vhost_name]
    interface = vhost_name + '-eth0'
    if len(bandwidth_list) != len(dst_ip_list):
        raise Exception(
            "The bandwidth list and dst_ip_list must have same length.")

    classid_numbers = list(range(10, 10 + len(bandwidth_list)))
    total_bandwidth = sum(bandwidth_list)
    # Adding tc qdisc and tc class rules for the interface of this virtual host.
    # Setting the bandwidth limits for each classids.
    vhost.cmd("tc qdisc add dev {} root handle 1: htb default 10".format(interface))
    vhost.cmd(
        "tc class add dev {} parent 1: classid 1:1 htb rate {}mbit ceil {}mbit".format(interface, str(total_bandwidth), str(total_bandwidth)))
    for (classid_number, bandwidth) in zip(classid_numbers, bandwidth_list):
        vhost.cmd(
            "tc class add dev {} parent 1:1 classid 1:{} htb rate {}mbit ceil {}mbit".format(interface, str(classid_number), str(bandwidth), str(bandwidth)))

    # Attaching tc filtering rules based on the destination IP address of the packets,
    # to decide which class of the qdisc that traffic belongs to.
    for(dst_ip, classid_number) in zip(dst_ip_list, classid_numbers):
        vhost.cmd("tc filter add dev {} protocol ip parent 1:0 prio 1 u32 match ip dst {} flowid 1:{}".format(
            interface, dst_ip, str(classid_number)))

    print("------------------------------------------\n tc qdisc show for {}: ".format(vhost_name))
    print(vhost.cmd("tc qdisc show dev {}".format(interface)))
    print("------------------------------------------\n tc class show for {}: ".format(vhost_name))
    print(vhost.cmd("tc class show dev {}".format(interface)))
    print("------------------------------------------\n")


#######################################################################################

def map_vnr_on_substrate_network(net, host_requirements, links_with_bw):
    """ Map virtual network request on the substrate network.
    host_requirements: List[Tuple(str, int)]
        List of (host_name, cpu_requirement); list of substrate network hosts to map the vnr's virtual hosts, 
        along with the cpu limit requirement for those virtual hosts. 
        E.g. [('h1', 10), ('h2', 20), ('h3', 10), ('h4', 30)].
    links_with_bw: List[Tuple(str, str, int)]
        List of links (the two substrate host endpoints for the link), and the bandwidth between them.
        E.g. [('h1', 'h2', 40),
                ('h2', 'h3', 90),
                ('h1', 'h3', 20),
                ('h2', 'h4', 60)]
    """
    # Tracking 'cost' and 'revenue' with respect to bandwidth for output results.
    total_bw_cost_spent_on_substrate = 0
    total_bw_requested = 0
    total_cpu_reqs = 0

    vnr_number = len(gbl.MAPPED_VNRS) + 1
    substrate_hosts = []
    virtual_hosts = []
    for i, (host_name, cpu_req) in enumerate(host_requirements):
        virtual_host_name = 'vnr{}_vh{}'.format(vnr_number, i + 1)
        substrate_host, virtual_host = _add_vnr_host_on_substrate_host(
            net, virtual_host_name, host_name, cpu_req, vnr_number)
        substrate_hosts.append(substrate_host)
        virtual_hosts.append(virtual_host)
        op.SUBSTRATE_HOSTS_USED.add(host_name)
        total_cpu_reqs += cpu_req

    host_names = [h[0] for h in host_requirements]
    vnr = MappedVNR(substrate_hosts, virtual_hosts, vnr_number)

    # Storing the original VNR request data as well so that it can be tested later in iperf, ping, etc.
    vnr.vnr_host_names = host_names
    vnr.vnr_links_with_bw = links_with_bw

    gbl.MAPPED_VNRS.append(vnr)

    # Populating `vhost_x_links` dictionary to keep track of all the links for every
    # virtual host, for ultimately doing traffic control.
    vhost_x_links = {}
    for vhost in virtual_hosts:
        vhost_x_links[vhost] = []
        for link in links_with_bw:
            if link[0] not in host_names or link[1] not in host_names:
                raise Exception("You have specified a link between hosts {} and {} which are not used in the node mappings (Hosts: {}).".format(
                    link[0], link[1], host_names))
            vh1_on_link, vh2_on_link = vnr.hostname_x_vh[link[0]
                                                         ], vnr.hostname_x_vh[link[1]]
            bw_of_link = link[2]
            if vhost.name is vh1_on_link.name:
                vhost_x_links[vhost].append((bw_of_link, vh2_on_link))
            if vhost.name is vh2_on_link.name:
                vhost_x_links[vhost].append((bw_of_link, vh1_on_link))

    # Adding traffic control rules for each virtual host.
    for vhost in virtual_hosts:
        bws = []
        dst_ips = []
        links_for_this_vhost = vhost_x_links[vhost]
        for link in links_for_this_vhost:
            bws.append(link[0])
            dst_ips.append(link[1].ip_addr)
        _add_tc_htb(net, vhost.name, bws, dst_ips)

    # Reducing the bandwidth values in gbl.SWITCH_PAIR_x_BW
    for (h1_name, h2_name, bw) in links_with_bw:
        h1 = gbl.HOSTNAME_x_HOST[h1_name]
        h2 = gbl.HOSTNAME_x_HOST[h2_name]

        gbl.SWITCH_PAIR_x_BW, bw_cost_spent_on_substrate = add_link_mapping_between_hosts(
            (h1, h2), bw, gbl.SWITCH_PAIR_x_BW, "final-vnr-mapping")
        total_bw_cost_spent_on_substrate += bw_cost_spent_on_substrate
        total_bw_requested += bw

    print("\n===============================================================")
    print("op.SUBSTRATE_HOSTS_USED: ", op.SUBSTRATE_HOSTS_USED)
    print("op.SUBSTRATE_LINKS_USED: ", op.SUBSTRATE_LINKS_USED)
    print("===============================================================\n")

    # Updating the 'cost' and 'revenue' with respect to bandwidth and cpu.
    op.output_dict["total_cost"] += total_bw_cost_spent_on_substrate
    op.output_dict["revenue"] += total_bw_requested
    op.output_dict["total_cost"] += total_cpu_reqs
    op.output_dict["revenue"] += total_cpu_reqs


def add_link_mapping_between_hosts(host_pair, bw_req, SWITCH_PAIR_x_BW, purpose="check"):
    """ Once a host pair has been selected for doing mapping of some virtual link on it,
    the bandwidth of all the links in the path b/w the hosts shall be reduced by how
    much ever that virtual link has consumed on all the links in the path between hosts.

    host_pair: Pair of substrate hosts.
    bw_req: The bandwidth requirement of the virtual link, which needs to be subtracted
        since this link is being mapped.
    SWITCH_PAIR_x_BW: The variable storing the bw of switch pairs values, which shall be
        updated and returned to the caller.
    purpose: This function `add_link_mapping_between_hosts` can be called by the vne algorithms 
        module as well, to check while its selecting hosts and links for mapping. Hence the 
        'purpose' variable helps here. If purpose == 'final-vnr-mapping', only then we update 
        the op.SUBSTRATE_LINKS_USED. Otherwise its just a 'check' as part of trying a vne algorithm, 
        and we shall not update the op.SUBSTRATE_LINKS_USED yet.
    """
    # When adding a link mapping between substrate hosts, the bw provided to the
    # link between these hosts must be subtracted from all the links in the path
    # between these hosts.
    bw_cost_spent_on_substrate = 0
    (h1, h2) = host_pair
    if int(h1.name[1:]) > int(h2.name[1:]):
        host_pair = (h2, h1)

    path = gbl.PATH_BETWEEN_HOSTS[host_pair]
    for each_link in path:
        (node1, node2) = each_link

        for ((p1, p2), _) in SWITCH_PAIR_x_BW.items():
            if (p1 == node1.name and p2 == node2.name):
                SWITCH_PAIR_x_BW[(p1, p2)] -= bw_req
                SWITCH_PAIR_x_BW[(p2, p1)] -= bw_req
                bw_cost_spent_on_substrate += bw_req
                # Note: Remember that the spine leaf achitecture we have in our project is
                # implemented as a 'modified spine leaf' architecture, and so there is an
                # additional layer of links in the last layer. And when we compute the 'cost'
                # for bandwidth spent, we DON'T count that last 'modified' layer's links
                # since this is just an implementation optimization.
                if purpose == "final-vnr-mapping":
                    op.SUBSTRATE_LINKS_USED.add((node1.name, node2.name))
                    op.SUBSTRATE_LINKS_USED.add((node2.name, node1.name))

    return SWITCH_PAIR_x_BW, bw_cost_spent_on_substrate
