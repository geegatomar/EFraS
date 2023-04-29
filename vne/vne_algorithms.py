import gbl
import helpers as hp
import copy
import output as op
import vnr_mapping
from nord import nord_support
from nrm import nrm_support
from ahp import ahp_support

# VNE ALGORTHM FUNCTIONS

# Each VNE algorithm shall take the 3 inputs specifying the VNR's requirements:
# 1. num_hosts: How many virtual nodes does tenant want in the network.
# 2. cpu_reqs: The CPU requirement limits for each host in network.
# 3. link_bw_reqs: The links between hosts and the bandwidth requirement for that link.

# It shall then generate the list of `ranked virtual hosts` and list of `ranked substrate
# hosts`, and then call the `_greedy_vne_embedding` function passing those ranked
# host lists as input.


def _first_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ First fit algorithm which ranks virtual hosts in the order they are given, and also
    ranks substrate hosts in the order they are given. """
    ranked_virtual_hosts = [i for i in range(1, num_hosts + 1)]
    ranked_substrate_hosts = gbl.HOSTS
    return _greedy_vne_embedding(num_hosts, cpu_reqs, link_bw_reqs, ranked_virtual_hosts, ranked_substrate_hosts)


def _worst_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ Worst fit algorithm which ranks virtual hosts in the order they are given. And for
    substrate hosts, it ranks them in the decreasing order of their remaining CPU limit/capacity, 
    i.e. substrate hosts with highe remaining cpu/crb limits will be tried first for the mapping 
    of vnr hosts. """
    ranked_virtual_hosts = [i for i in range(1, num_hosts + 1)]
    ranked_substrate_hosts = sorted(
        gbl.HOSTS, key=lambda x: x.cpu_limit, reverse=True)
    return _greedy_vne_embedding(num_hosts, cpu_reqs, link_bw_reqs, ranked_virtual_hosts, ranked_substrate_hosts)


def _nord_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ NORD algorithm follows a topsis ranking strategy which handles the ranking for both the
    substrate hosts and virtual hosts. """
    ranked_virtual_hosts, ranked_substrate_hosts = nord_support.get_ranked_hosts(
        num_hosts, cpu_reqs, link_bw_reqs)
    return _greedy_vne_embedding(num_hosts, cpu_reqs, link_bw_reqs, ranked_virtual_hosts, ranked_substrate_hosts)


def _nrm_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ NRM algorithm handles the ranking for both the substrate hosts and virtual hosts. """
    ranked_virtual_hosts, ranked_substrate_hosts = nrm_support.get_ranked_hosts(
        num_hosts, cpu_reqs, link_bw_reqs)
    return _greedy_vne_embedding(num_hosts, cpu_reqs, link_bw_reqs, ranked_virtual_hosts, ranked_substrate_hosts)


def _ahp_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ AHP algorithm handles the ranking for both the substrate hosts and virtual hosts. """
    ranked_virtual_hosts, ranked_substrate_hosts = ahp_support.get_ranked_hosts(
        num_hosts, cpu_reqs, link_bw_reqs)
    return _greedy_vne_embedding(num_hosts, cpu_reqs, link_bw_reqs, ranked_virtual_hosts, ranked_substrate_hosts)


def _greedy_vne_embedding(num_hosts, cpu_reqs, link_bw_reqs, ranked_virtual_hosts, ranked_substrate_hosts):
    """ Tries to performs greedy VNE embedding given the list of ranked virtual hosts and ranked substrate
    hosts. Note that this is still in the `vne_algorithms` module, and this function shall only return
    the selected substrate hosts after trying out the mapping greedily. The actual mapping of the hosts 
    will happen in the `vnr_mapping` module based on the results returned from this function.

    num_hosts: Number of hosts as provided by tenants requirement for the VNR. 
        Example: 4
    cpu_reqs: The CPU requirement values of every host in the VNR.
        Example: [20, 10, 5, 15]
    link_bw_reqs: The links as specified in the VNR, along with the expected bandwidth
        between the hosts. List of Tuple(host, host, bandwidth req)
        Example: [(1, 2, 5), (2, 3, 3), (2, 4, 6), (3, 4, 8)]
    ranked_virtual_hosts: List of ranked virtual hosts, i.e. in the order in which they shall be served/tried 
        for mapping.
        Example: [3, 1, 2, 4]
        This means that mapping will first be tried for virtual host 3, and then 1, and so on.
    ranked_substrate_hosts: List of ranked substrate hosts, i.e. in the order in which substrate hosts shall
        be tried for mapping of virtual hosts. Its a (ordered) list of SubstrateHost objects.
        Example: [SubstrateHost('h2'), SubstrateHost('h3'), SubstrateHost('h1')]
    """

    COPY_SWITCH_PAIR_x_BW = copy.deepcopy(gbl.SWITCH_PAIR_x_BW)

    # For every host, obtaining what all links it needs to have with other hosts, and their bws.
    hostpair_x_bw = {}
    for h in range(1, num_hosts + 1):
        for (h1, h2, bw) in link_bw_reqs:
            hostpair_x_bw[(h1, h2)] = bw
            hostpair_x_bw[(h2, h1)] = bw

    # Maintain mapped hosts, and onto which substrate hosts they were mapped.
    mapped_host_x_substrate_host = {}

    # Going over every virtual host to try a mapping (in order of 'ranked' virtual hosts).
    for h in ranked_virtual_hosts:
        host_mapped_successfully = False
        # Trying the mapping onto substrate hosts in the order of 'ranked' substrate hosts.
        for substrate_host in ranked_substrate_hosts:
            if substrate_host in mapped_host_x_substrate_host.values():
                # It means that this substrate host is already being used in another host's mapping,
                # so we cannot use it here for this host.
                continue
            # Check if that substrate host can satisfy the cpu requirement of this host.
            if cpu_reqs[h - 1] < substrate_host.cpu_limit:
                # Can try mapping this host.
                print("\nTrying to map host {} on substrate host {},  cpu_reqs[h]: {}, substrate_host.cpu_limit: {}".format(
                    h, substrate_host.name, cpu_reqs[h - 1], substrate_host.cpu_limit))
                local_COPY_SWITCH_PAIR_x_BW = COPY_SWITCH_PAIR_x_BW
                mapped_host_x_substrate_host[h] = substrate_host
                host_mapped_successfully = True
                # Then check for all the link's bandwidth requirements between this
                # host and other previously mapped hosts, to verify if mapping is valid.
                for other_h, _ in mapped_host_x_substrate_host.items():
                    if h == other_h:
                        continue
                    H1 = mapped_host_x_substrate_host[h]
                    H2 = mapped_host_x_substrate_host[other_h]
                    # If theres a link, then try to satisfy the link, by subtracting the
                    # bw values.
                    if hostpair_x_bw.get((h, other_h)):
                        bw_req = hostpair_x_bw[(h, other_h)]
                        print("Checking bandwidth requirments between {} and {}... bw_req = {}, actual bw limit b/w hosts: {}".format(
                            H1.name, H2.name, bw_req, hp.get_bandwidth_limit_between_host_pair((H1, H2), local_COPY_SWITCH_PAIR_x_BW)))
                        # If bandwidth req is less than the limit between hosts, only then the
                        # mapping of this host is possible, else just remove this host mapping,
                        # and try another.
                        if bw_req <= hp.get_bandwidth_limit_between_host_pair((H1, H2), local_COPY_SWITCH_PAIR_x_BW):
                            local_COPY_SWITCH_PAIR_x_BW, _ = vnr_mapping.add_link_mapping_between_hosts(
                                (H1, H2), bw_req, local_COPY_SWITCH_PAIR_x_BW)
                        else:
                            host_mapped_successfully = False
                            break

                if not host_mapped_successfully:
                    # Remove mapping of host since host mapping was not successful.
                    print("Removing the mapping of {} on substrate {}".format(
                        h, substrate_host.name))
                    del mapped_host_x_substrate_host[h]
                else:
                    print("Host {} mapped on substrate host {}!".format(
                        h, substrate_host.name))
                    # Only once the mapping of this virtual host is confirmed on this substrate host,
                    # only then you update the COPY_SWITCH_PAIR_x_BW variable.
                    COPY_SWITCH_PAIR_x_BW = local_COPY_SWITCH_PAIR_x_BW
            # If the substrate host for mapping this host has been found, then break out
            # of inner for loop, and continue to finding the mapping for next host.
            if host_mapped_successfully:
                break

        # If you have tried all possible substrate hosts, and still dont find a mapping
        # then just return None and tell the caller that no mapping was found.
        if not host_mapped_successfully:
            return None, None

    # Creating the input for the vnr mapping function, which is returned from this function.
    cpu_reqs_for_vnr_mapping = []
    bw_reqs_for_vnr_mapping = []
    for h, substrate_host in mapped_host_x_substrate_host.items():
        cpu_reqs_for_vnr_mapping.append((substrate_host.name, cpu_reqs[h-1]))
    for (h1, h2, bw) in link_bw_reqs:
        H1 = mapped_host_x_substrate_host[h1]
        H2 = mapped_host_x_substrate_host[h2]
        bw_reqs_for_vnr_mapping.append((H1.name, H2.name, bw))

    print("\nSubstrate hosts selected by the {}:".format(
        gbl.CFG["vne_algorithm"]))
    print("cpu_reqs_for_vnr_mapping: ", cpu_reqs_for_vnr_mapping)
    print("bw_reqs_for_vnr_mapping: ", bw_reqs_for_vnr_mapping)

    return (cpu_reqs_for_vnr_mapping, bw_reqs_for_vnr_mapping)


def vne_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ This function selects the VNE (Virtual Network Embedding) algorithm to
    use based on the specifications in the configuration files.

    num_hosts: Number of hosts as provided by tenants requirement for the VNR. 
        Example: 4
    cpu_reqs: The CPU requirement values of every host in the VNR.
        Example: [20, 10, 5, 15]
    link_bw_reqs: The links as specified in the VNR, along with the expected bandwidth
        between the hosts. List of Tuple(vhost, vhost, bandwidth requirement)
        Example: [(1, 2, 5), (2, 3, 3), (2, 4, 6), (3, 4, 8)]
    """
    if gbl.CFG["vne_algorithm"] == "worst-fit-algorithm":
        return _worst_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs)
    if gbl.CFG["vne_algorithm"] == "first-fit-algorithm":
        return _first_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs)
    if gbl.CFG["vne_algorithm"] == "nord-algorithm":
        return _nord_algorithm(num_hosts, cpu_reqs, link_bw_reqs)
    if gbl.CFG["vne_algorithm"] == "nrm-algorithm":
        return _nrm_algorithm(num_hosts, cpu_reqs, link_bw_reqs)
    if gbl.CFG["vne_algorithm"] == "ahp-algorithm":
        return _ahp_algorithm(num_hosts, cpu_reqs, link_bw_reqs)
