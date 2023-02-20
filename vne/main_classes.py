class Switch:
    """
    A class to represent the switches used in the spine-leaf topology network being created.
    Used for all 3 kinds of switches; i.e. spine layer siwtches, leaf layer switches, and
    host switches. Note that this class is only for our reference, and differs from the 
    internal switch class that mininet creates.

    Attributes
    ----------
    name : str
        Name of the switch. Spine layer switches are named 's1_x' (e.g. 's1_2'), leaf layer 
        switches are named 's2_x' (e.g. 's2_2'), and host switches are named shx (e.g. 'sh2').
    ip_subnet : str
        The IP subnet under this switch. E.g. IP subnet for spine layer switch can be '10',
        for leaf layer switch can be '10.0', for host switch can be '10.0.1'.
    host_ips_under_this_switch : List[str]
        The list of host IPs under this switch.
    next_port_number : int
        The next available port number on the switch. Everytime a device (host or switch) is 
        linked to this host, a port gets utilized in that link, and this counter increases.
    """

    def __init__(self, switch_name: str, ip_subnet: str):
        self.name = switch_name
        self.ip_subnet = ip_subnet
        self.host_ips_under_this_switch = []
        self.next_port_number = 1


class Host:
    """
    A class to represent the hosts used in the spine-leaf topology network being created.
    Used for the 2 kinds of hosts in the network; i.e. substrate hosts representing hosts
    on the physical network, and the virtual hosts representing the VNR hosts which are being 
    mapped on the substrate network. Note that this class is only for our reference, and 
    differs from the internal host class that mininet creates.
    Classes SubstrateHost and VNRVirtualHost inherit from this class.

    Attributes
    ----------
    name : str
        Name of the host. Substrate hosts are named 'hx' (e.g. 'h12'), and VNR virtual hosts
        hosts are named 'vnrx_vhy' (e.g. 'vnr2_vh3').
    ip_addr : str
        The IP address of this host. E.g. IP for host can be '10.0.1.2/24'.
    host_switch_attached : Switch
        The host switch attached directly to this host.
    cpu_limit : int
        The assigned CPU limit for this host. E.g. 140.
    """

    def __init__(self, host_name, ip_addr, cpu_limit):
        self.name = host_name
        self.ip_addr = ip_addr
        self.host_switch_attached = None
        self.cpu_limit = cpu_limit
