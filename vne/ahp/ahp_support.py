# The main file which provides AHP support/integration with our VNE emulator code.

import gbl
from nord import graph_u
from ahp import Rematch_AHP
import helpers as hp


def _h_to_s(host_name):
    """ Converts 'host name' (our code convention) to 'string' (AHP code convention) 
    such that AHP code can understand it. Doing the additional -1 to comply with 
    AHP code's conventions. """
    return str(int(host_name[1:]) - 1)


def _s_to_h(s):
    """ Converts 'string' (AHP code convention) back to 'host name' (our code convention). """
    return 'h' + str(s + 1)


def _generate_substrate_graph_u_object():
    """ Generates and returns the substrate graph_u.Graph object (as per AHP 
    code convention) since AHP expects the substrate network represented in this
    graph_u.Graph object.
    This function shall take the data structures represented in my code, and 
    convert/create appropriate data structures so that AHP algorithms's code can 
    directly be called, hence providing direct integration with AHP. """

    substrate_cfg = gbl.CFG["substrate"]

    substrate_num_hosts = substrate_cfg["sl_factor"] * \
        substrate_cfg["ll_factor"] * substrate_cfg["hl_factor"]

    # Populating node weights.
    substrate_node_weights = {}
    for substrate_host in gbl.HOSTS:
        substrate_node_weights[int(
            _h_to_s(substrate_host.name))] = substrate_host.cpu_limit

    # Populating edges and edge weights.
    substrate_edges = []
    substrate_edge_weights = {}
    for i in range(len(gbl.HOSTS)):
        for j in range(i + 1, len(gbl.HOSTS)):
            # Note that in our spine leaf topology, there is a link between every host pair.
            h1, h2 = gbl.HOSTS[i], gbl.HOSTS[j]
            bw_limit = hp.get_bandwidth_limit_between_host_pair(
                (h1, h2), gbl.SWITCH_PAIR_x_BW)
            substrate_edges.append((_h_to_s(h1.name), _h_to_s(h2.name)))
            substrate_edges.append((_h_to_s(h2.name), _h_to_s(h1.name)))
            substrate_edge_weights[(
                _h_to_s(h1.name), _h_to_s(h2.name))] = bw_limit
            substrate_edge_weights[(
                _h_to_s(h2.name), _h_to_s(h1.name))] = bw_limit

    # Neighbor population for each substrate host: For every host, other hosts under
    # the same /16 subnet are considered to be its neighbors. Reason for making this
    # assumption is that the number of links in the path between such pair of nodes
    # (belonging to same /16 subnet) is lesser compared to any other pair of hosts.
    substrate_neighbours = {}
    for h1 in gbl.HOSTS:
        substrate_neighbours[int(_h_to_s(h1.name))] = set()
        for h2 in gbl.HOSTS:
            ip_subnet_h1 = ".".join(h1.ip_addr.split(".")[0:2])
            ip_subnet_h2 = ".".join(h2.ip_addr.split(".")[0:2])
            if ip_subnet_h1 == ip_subnet_h2 and h1 != h2:
                substrate_neighbours[int(_h_to_s(h1.name))].add(
                    _h_to_s(h2.name))

    print("\nsubstrate_num_hosts: ", substrate_num_hosts)
    print("\nsubstrate_neighbours: ", substrate_neighbours)
    print("\nsubstrate_edges: ", substrate_edges)
    print("\nsubstrate_edge_weights: ", substrate_edge_weights)
    print("\nsubstrate_node_weights: ", substrate_node_weights)

    return graph_u.Graph(substrate_num_hosts, substrate_edges,
                         substrate_neighbours, substrate_node_weights, substrate_edge_weights)


def _v_to_s(v):
    """ Convert from virtual host (in our code convention) to AHP's code convention. """
    return v - 1


def _s_to_v(s):
    """ Convert from AHP's code convention to virtual host (in our code convention). """
    return s + 1


def _generate_vnr_graph_u_object(vnr_num_hosts, vnr_cpu_reqs, vnr_link_reqs):
    """ Generates and returns the VNR graph_u.Graph object (as per AHP code convention) 
    since AHP expects the VNR represented in this graph_u.Graph object.
    This function shall take the data structures represented in my code, and 
    convert/create appropriate data structures so that AHP algorithms's code can 
    directly be called, hence providing direct integration with AHP. """

    # Populating edges and edge weights.
    vnr_edges = []
    vnr_edge_weights = {}
    for vnr_link_requirement in vnr_link_reqs:
        (vh1, vh2, bw) = vnr_link_requirement
        vnr_edges.append((str(_v_to_s(vh1)), str(_v_to_s(vh2))))
        vnr_edges.append((str(_v_to_s(vh2)), str(_v_to_s(vh1))))
        vnr_edge_weights[(str(_v_to_s(vh1)), str(_v_to_s(vh2)))] = bw
        vnr_edge_weights[(str(_v_to_s(vh2)), str(_v_to_s(vh1)))] = bw

    # Populating node weights.
    vnr_node_weights = {}
    for i, vnr_cpu_requirement in enumerate(vnr_cpu_reqs):
        vnr_node_weights[i] = vnr_cpu_requirement

    # Neighbor population for each virtual host of VNR.
    vnr_neighbours = {}
    for vhost in range(vnr_num_hosts):
        vnr_neighbours[vhost] = set()
        for a, b in vnr_edges:
            if int(a) == vhost:
                vnr_neighbours[vhost].add(b)

    print("\nvnr_num_hosts: ", vnr_num_hosts)
    print("\nvnr_neighbours: ", vnr_neighbours)
    print("\nvnr_edges: ", vnr_edges)
    print("\nvnr_edge_weights: ", vnr_edge_weights)
    print("\nvnr_node_weights: ", vnr_node_weights)

    return graph_u.Graph(vnr_num_hosts, vnr_edges, vnr_neighbours, vnr_node_weights, vnr_edge_weights)


def get_ranked_hosts(vnr_num_hosts, vnr_cpu_reqs, vnr_link_reqs):
    """ Returns list of `ranked virtual hosts`, and `ranked substrate hosts` (so that the ranked
    list of hosts can be used for performing embedding by the called, for example greedy VNE 
    embedding). 

    vnr_num_hosts: Number of hosts as provided by tenants requirement for the VNR. 
        Example: 4
    vnr_cpu_reqs: The CPU requirement values of every host in the VNR.
        Example: [20, 10, 5, 15]
    vnr_link_bw_reqs: The links as specified in the VNR, along with the expected bandwidth
        between the hosts. List of Tuple(vhost, vhost, bandwidth requirement)
        Example: [(1, 2, 5), (2, 3, 3), (2, 4, 6), (3, 4, 8)]
    """

    # Creating the graph_u.Graph object (AHP code convention) for substrate network.
    substrate_graph_u = _generate_substrate_graph_u_object()

    # Creating the graph_u.Graph object (AHP code convention) for virtual network request.
    vnr_graph_u = _generate_vnr_graph_u_object(
        vnr_num_hosts, vnr_cpu_reqs, vnr_link_reqs)

    # Once both graph_u.Graph objects for the 'substrate' and 'vnr' have been created, then
    # the node ranking function of AHP can be called.
    ahp_ranked_virtual_nodes, ahp_ranked_substrate_nodes = Rematch_AHP.node_rank(
        substrate_graph_u, vnr_graph_u, 1)

    print("\nahp_ranked_virtual_nodes: ", ahp_ranked_virtual_nodes)
    print("\nahp_ranked_substrate_nodes: ", ahp_ranked_substrate_nodes)

    # The results (ahp_ranked_virtual_nodes, ahp_ranked_substrate_nodes) obtained from
    # calling `ahp.node_rank()`, i.e. AHP's node ranking function are still in
    # AHP code's convention. They shall now be converted back to our code convention before
    # returning from this function.
    # Populating `ranked virtual hosts` in our code convention.
    ranked_virtual_hosts = []
    for vh in ahp_ranked_virtual_nodes:
        ranked_virtual_hosts.append(_s_to_v(vh))

    # Populating `ranked substrate hosts` in our code convention.
    ranked_substrate_hosts = []
    for sh in ahp_ranked_substrate_nodes:
        host_name = _s_to_h(sh)
        ranked_substrate_hosts.append(gbl.HOSTNAME_x_HOST[host_name])

    print("\nranked_virtual_hosts: ", ranked_virtual_hosts)
    print("\nranked_substrate_hosts: ", ranked_substrate_hosts)

    return ranked_virtual_hosts, ranked_substrate_hosts
