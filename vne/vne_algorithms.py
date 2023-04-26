import gbl
import helpers as hp
import copy
import output as op
import vnr_mapping


def _get_bandwidth_limit_between_host_pair(host_pair, COPY_SWITCH_PAIR_x_BW):
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


# VNE ALGORTHM FUNCTIONS

# Each VNE algorithm shall take the 3 inputs specifying the VNR's requirements:
# 1. num_hosts: How many virtual nodes does tenant want in the network.
# 2. cpu_reqs: The CPU requirement limits for each host in network.
# 3. link_bw_reqs: The links between hosts and the bandwidth requirement for that link.

# After this vne algorithm function figures out which substrate hosts it wants to select to
# do the mapping of given VNR's requirement, then the actual mapping logic is handled by the
# vnr_mapping module.

# The VNE algorithm function shall return the two variables `cpu_reqs_for_vnr_mapping` &
# `bw_reqs_for_vnr_mapping`, an example for which is as follows
#   cpu_reqs_for_vnr_mapping:  [('h5', 13), ('h6', 15), ('h8', 13)]
#   bw_reqs_for_vnr_mapping:  [('h5', 'h6', 3), ('h5', 'h8', 3)]


def first_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ First fit algorithm, which just iterates over every possible host once in order,
    and based on whether it has enough CPU limit, tries to map virtual host on it, and 
    then checks if all the virtual link's bandwidth requirements are satisfied or not. 
    If any of the bandwidth requirement fails, it goes on to try another substrate host 
    for the mapping of that host.

    This function shall figure out which substrate host to map each of the
    given hosts. The actual mapping with VLAN logic, traffic control, etc. will be 
    implemented in the vnr_mapping module which is called based on the output returned
    from this function.

    num_hosts: Number of hosts as provided by tenants requirement for the VNR. 
        Example: 4
    cpu_reqs: The CPU requirement values of every host in the VNR.
        Example: [20, 10, 5, 15]
    link_bw_reqs: The links as specified in the VNR, along with the expected bandwidth
        between the hosts. List of Tuple(host, host, bandwidth req)
        Example: [(1, 2, 5), (2, 3, 3), (2, 4, 6), (3, 4, 8)]
    """

    COPY_SWITCH_PAIR_x_BW = copy.deepcopy(gbl.SWITCH_PAIR_x_BW)

    # For every host, obtaining what all links it needs to have with other hosts, and their bws
    hostpair_x_bw = {}
    for h in range(1, num_hosts + 1):
        for (h1, h2, bw) in link_bw_reqs:
            hostpair_x_bw[(h1, h2)] = bw
            hostpair_x_bw[(h2, h1)] = bw

    # Maintain mapped hosts, and onto which substrate hosts they were mapped.
    mapped_host_x_substrate_host = {}

    # Going over every host to try a mapping (as per this algorithm).
    for h in range(1, num_hosts + 1):
        host_mapped_successfully = False
        # In this algorithm, we iterate in the order of the given hosts; more like fcfs.
        for substrate_host in gbl.HOSTS:
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
                            H1.name, H2.name, bw_req, _get_bandwidth_limit_between_host_pair((H1, H2), local_COPY_SWITCH_PAIR_x_BW)))
                        # If bandwidth req is less than the limit between hosts, only then the
                        # mapping of this host is possible, else just remove this host mapping,
                        # and try another.
                        if bw_req <= _get_bandwidth_limit_between_host_pair((H1, H2), local_COPY_SWITCH_PAIR_x_BW):
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

    print("\nSubstrate hosts selected by the VNE algorithm:")
    print("cpu_reqs_for_vnr_mapping: ", cpu_reqs_for_vnr_mapping)
    print("bw_reqs_for_vnr_mapping: ", bw_reqs_for_vnr_mapping)
    print("\n")

    return (cpu_reqs_for_vnr_mapping, bw_reqs_for_vnr_mapping)


#################################################################################


def worst_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ Worst fit algorithm, which just iterates over every host in descending order of their remaining
    cpu capacities, and based on whether it has enough CPU limit, tries to map virtual host on it,
    and then checks if all the virtual link's bandwidth requirements are satisfied or not.
    If any of the bandwidth requirement fails, it goes on to try another substrate host
    for the mapping of that host.

    This function shall figure out which substrate host to map each of the
    given hosts. The actual mapping with VLAN logic, traffic control, etc. will be 
    implemented in the vnr_mapping module which is called based on the output returned
    from this function.

    num_hosts: Number of hosts as provided by tenants requirement for the VNR. 
        Example: 4
    cpu_reqs: The CPU requirement values of every host in the VNR.
        Example: [20, 10, 5, 15]
    link_bw_reqs: The links as specified in the VNR, along with the expected bandwidth
        between the hosts. List of Tuple(host, host, bandwidth req)
        Example: [(1, 2, 5), (2, 3, 3), (2, 4, 6), (3, 4, 8)]
    """

    COPY_SWITCH_PAIR_x_BW = copy.deepcopy(gbl.SWITCH_PAIR_x_BW)

    # For every host, obtaining what all links it needs to have with other hosts, and their bws
    hostpair_x_bw = {}
    for h in range(1, num_hosts + 1):
        for (h1, h2, bw) in link_bw_reqs:
            hostpair_x_bw[(h1, h2)] = bw
            hostpair_x_bw[(h2, h1)] = bw

    # Maintain mapped hosts, and onto which substrate hosts they were mapped.
    mapped_host_x_substrate_host = {}

    # The only difference between first-fit and worst-fit is that the order in
    # which we try hosts in worst-fit is in the descending order of remaining
    # available limit of each substrate host.
    SORTED_gbl_HOSTS = sorted(
        gbl.HOSTS, key=lambda x: x.cpu_limit, reverse=True)

    # Going over every host to try a mapping (as per this algorithm).
    for h in range(1, num_hosts + 1):
        host_mapped_successfully = False
        # In this algorithm, we iterate in the order of the decreasing order of host's remaining cpu capacity limits;
        # so called Worst fit algorithm.
        for substrate_host in SORTED_gbl_HOSTS:
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
                            H1.name, H2.name, bw_req, _get_bandwidth_limit_between_host_pair((H1, H2), local_COPY_SWITCH_PAIR_x_BW)))
                        # If bandwidth req is less than the limit between hosts, only then the
                        # mapping of this host is possible, else just remove this host mapping,
                        # and try another.
                        if bw_req <= _get_bandwidth_limit_between_host_pair((H1, H2), local_COPY_SWITCH_PAIR_x_BW):
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

    print("\nSubstrate hosts selected by the VNE algorithm:")
    print("cpu_reqs_for_vnr_mapping: ", cpu_reqs_for_vnr_mapping)
    print("bw_reqs_for_vnr_mapping: ", bw_reqs_for_vnr_mapping)
    print("\n")

    return (cpu_reqs_for_vnr_mapping, bw_reqs_for_vnr_mapping)


###############################################################################################

def vne_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ This function selects the VNE (Virtual Network Embedding) algorithm to
    use based on the specifications in the configuration files.

    num_hosts: Number of hosts as provided by tenants requirement for the VNR. 
        Example: 4
    cpu_reqs: The CPU requirement values of every host in the VNR.
        Example: [20, 10, 5, 15]
    link_bw_reqs: The links as specified in the VNR, along with the expected bandwidth
        between the hosts. List of Tuple(host, host, bandwidth req)
        Example: [(1, 2, 5), (2, 3, 3), (2, 4, 6), (3, 4, 8)]
    """
    if gbl.CFG["vne_algorithm"] == "worst-fit-algorithm":
        return worst_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs)
    if gbl.CFG["vne_algorithm"] == "first-fit-algorithm":
        return first_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs)
