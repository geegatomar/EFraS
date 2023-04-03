import gbl
import helpers as hp
import copy
import output as op


def _get_bandwidth_limit_between_host_pair(host_pair, COPY_BW_SWITCH_PAIR):
    """ Gets the bandwidth limit between given pair of hosts.
    Between any pair of hosts, there are multiple hops of switches that any packet goes 
    through if it wants to travel from one host to the other. The bandwidth between the
    pair of hosts is the minimum of all the bandwidths of the links encountered in
    that path.

    host_pair: (Host, Host)
        The pair of hosts between bandwidth limit is supposed to be found.
    """
    # First rearrange the host_pair such that the smaller host value comes first, because
    # we have stored values in gbl.BW_SWITCH_PAIR in such a way only.
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
        # Update the bandwidth limit to be mininum of all links' bandwidths in the path.
        # Note that we haven't restricted bandwidths between the last layer of host to
        # host switch pair, hence those values will not exist in gbl.BW_SWITCH_PAIR.
        if gbl.BW_SWITCH_PAIR.get(each_link):
            # bw_limit = min(bw_limit, COPY_BW_SWITCH_PAIR[each_link])
            # bw_limits.append(COPY_BW_SWITCH_PAIR[each_link])

            # Find that switch pair in the COPY_BW_SWITCH_PAIR dict.
            for (s1, s2), bw in COPY_BW_SWITCH_PAIR.items():
                if each_link[0].name == s1.name and each_link[1].name == s2.name:
                    bw_limit = min(bw_limit, COPY_BW_SWITCH_PAIR[(s1, s2)])
                    bw_limits.append(COPY_BW_SWITCH_PAIR[(s1, s2)])
                    break

    print("Bandwidth values on path between hosts {} & {}: {}".format(
        h1.name, h2.name, bw_limits))
    return bw_limit


# =======================================================================================

# MAPPING ALGORTHM FUNCTIONS

# In each VNR, the user (or another funtion creating VNR) specifies its requirements as:
# 1. num_hosts: How many virtual nodes does tenant want in the network.
# 2. cpu_reqs: The CPU requirement limits for each host in network.
# 3. link_bw_reqs: The links between hosts and the bandwidth requirement for that link.

# After this mapping algorithm function figures out which substrate hosts it wants to select to
# do the mapping of given VNR's requirement, then to do the actual mapping, we call
# the `map_vnr_on_substrate_network` function itself.

def _add_link_mapping_between_hosts(host_pair, bw_req, COPY_BW_SWITCH_PAIR):
    """ This function is a helper for the `mapping_algorithm` algorithm.
    Once a host pair has been selected for doing mapping of some virtual link on it,
    the bandwidth of all the links in the path b/w the hosts shall be reduced by how
    much ever that virtual link has consumed.
    host_pair: Pair of substrate hosts.
    bw_req: The bandwidth requirement of the virtual link, which needs to be subtracted
        since this link is being mapped.
    COPY_BW_SWITCH_PAIR: Copy of the variable gbl.BW_SWITCH_PAIR.
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
        # Note: Remember that the spine leaf achitecture we have in our project is
        # implemented as a 'modified spine leaf' architecture, and so there is an
        # additional layer of links in the last layer. But when we compute the 'cost'
        # for bandwidth spent, we don't count that last 'modified' layer's links
        # because that layer is mainly for implementation purposes, and logically its
        # still a spine-leaf architecture.
        for ((p1, p2), _) in COPY_BW_SWITCH_PAIR.items():
            if (p1.name == node1.name and p2.name == node2.name):
                COPY_BW_SWITCH_PAIR[(p1, p2)] -= bw_req
                COPY_BW_SWITCH_PAIR[(p2, p1)] -= bw_req
                bw_cost_spent_on_substrate += bw_req

    return COPY_BW_SWITCH_PAIR, bw_cost_spent_on_substrate


def _update_bw_switch_pair_values(new_bw_switch_pair):
    for ((node1, node2), old_val) in gbl.BW_SWITCH_PAIR.items():
        for ((p1, p2), new_val) in new_bw_switch_pair.items():
            if node1.name == p1.name and node2.name == p2.name:
                gbl.BW_SWITCH_PAIR[(node1, node2)] = new_val
                # If this link value was changed, it means that this link was utilized
                # in the vnr mapping.
                if new_val != old_val:
                    op.SUBSTRATE_LINKS_USED.add((node1.name, node2.name))
            if node2.name == p1.name and node1.name == p2.name:
                gbl.BW_SWITCH_PAIR[(node2, node1)] = new_val
                if new_val != old_val:
                    op.SUBSTRATE_LINKS_USED.add((node2.name, node1.name))


# Currently, I'm implementing a simple testing algorithm, which does the mapping based
# simply based on the order in which we have the given hosts, and ensures to satisfy all the
# requirements as given by VNR tenant.
def first_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ First fit algorithm, which just iterates over every possible host once in order,
    and based on whether it has enough CPU limit, tries to map virtual host on it, and 
    then checks if all the virtual link's bandwidth requirements are satisfied or not. 
    If any of the bandwidth requirement fails, it goes on to try another substrate host 
    for the mapping of that host.

    This function shall figure out which substrate host to map each of the
    given hosts. Note that this function only reduces the bandwidths in gbl.BW_SWITCH_PAIR
    if mapping is successful. You shall ensure to call the `map_vnr_on_substrate_network`
    function to do the reduction of CPU limits, and to do the actual mapping with VLAN
    logic, traffic control, etc.
    In this function, the current logic is to return the inputs needed for calling the
    map_vnr_on_substrate_network function later (instead of calling that function from
    here itself). Reason to do this is to de-couple the functionalities, but you can
    choose to do otherwise as well.

    num_hosts: Number of hosts as provided by tenants requirement for the VNR. 
        Example: 4
    cpu_reqs: The CPU requirement values of every host in the VNR.
        Example: [20, 10, 5, 15]
    link_bw_reqs: The links as specified in the VNR, along with the expected bandwidth
        between the hosts. List of Tuple(host, host, bandwidth req)
        Example: [(1, 2, 5), (2, 3, 3), (2, 4, 6), (3, 4, 8)]
    """

    # Making a copy of this gbl.BW_SWITCH_PAIR, since we will update it at intermediate stages to
    # try out if a mapping works or not. If it doesn't work, discard that.
    COPY_BW_SWITCH_PAIR = copy.deepcopy(gbl.BW_SWITCH_PAIR)

    # For every host, obtaining what all links it needs to have with other hosts, and their bws
    hostpair_x_bw = {}
    for h in range(1, num_hosts + 1):
        for (h1, h2, bw) in link_bw_reqs:
            hostpair_x_bw[(h1, h2)] = bw
            hostpair_x_bw[(h2, h1)] = bw

    # Maintain mapped hosts, and onto which substrate hosts they were mapped.
    mapped_host_x_substrate_host = {}

    # Tracking 'cost' and 'revenue' with respect to bandwidth for output results.
    total_bw_cost_spent_on_substrate = 0
    total_bw_requested = 0
    total_cpu_reqs = 0

    substrate_hosts_used_for_mapping_vnr_hosts = []

    # Going over every host to try a mapping (as per this random algorithm).
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
                local_COPY_BW_SWITCH_PAIR = COPY_BW_SWITCH_PAIR
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
                            H1.name, H2.name, bw_req, _get_bandwidth_limit_between_host_pair((H1, H2), local_COPY_BW_SWITCH_PAIR)))
                        # If bandwidth req is less than the limit between hosts, only then the
                        # mapping of this host is possible, else just remove this host mapping,
                        # and try another.
                        if bw_req <= _get_bandwidth_limit_between_host_pair((H1, H2), local_COPY_BW_SWITCH_PAIR):
                            updated_COPY_BW_SWITCH_PAIR, bw_cost_spent_on_substrate = _add_link_mapping_between_hosts(
                                (H1, H2), bw_req, local_COPY_BW_SWITCH_PAIR)
                            local_COPY_BW_SWITCH_PAIR = updated_COPY_BW_SWITCH_PAIR
                            total_bw_cost_spent_on_substrate += bw_cost_spent_on_substrate
                            total_bw_requested += bw_req
                        else:
                            host_mapped_successfully = False
                            break

                if not host_mapped_successfully:
                    # Remove mapping of host since host mapping was not successful.
                    print("Removing the mapping of {} on substrate {}".format(
                        h, substrate_host.name))
                    del mapped_host_x_substrate_host[h]
                else:
                    substrate_hosts_used_for_mapping_vnr_hosts.append(
                        substrate_host.name)
                    print("Host {} mapped on substrate host {}!".format(
                        h, substrate_host.name))
                    # Only once the mapping of this virtual host is confirmed on this substrate host,
                    # only then you update the COPY_BW_SWITCH_PAIR variable.
                    COPY_BW_SWITCH_PAIR = local_COPY_BW_SWITCH_PAIR
            # If the substrate host for mapping this host has been found, then break out
            # of inner for loop, and continue to finding the mapping for next host.
            if host_mapped_successfully:
                break

        # If you have tried all possible substrate hosts, and still dont find a mapping
        # then just return None and tell the caller that no mapping was found.
        if not host_mapped_successfully:
            print(gbl.bcolors.FAIL +
                  "\nNO MAPPING WAS FOUND FOR THIS VNR!" + gbl.bcolors.ENDC)
            return None, None

    # If we have reached till here, means that mappings were found for every host
    # and we have successfully been able to serve this VNR. Hence update the
    # gbl.BW_SWITCH_PAIR with updated reduced bandwidths.
    # Since we don't want address of the deep copied objects, we need to update the original
    # BW_SWITCH_PAIR values itself.
    _update_bw_switch_pair_values(COPY_BW_SWITCH_PAIR)
    # Updating the 'cost' and 'revenue' with respect to bandwidth.
    op.output_dict["total_cost"] += total_bw_cost_spent_on_substrate
    op.output_dict["revenue"] += total_bw_requested

    # If all hosts of vnr were mapped, then total cost of cpu can be computed
    for h in range(1, num_hosts + 1):
        total_cpu_reqs += cpu_reqs[h - 1]
    print("\ntotal_cpu_reqs: ", total_cpu_reqs, "\n")
    op.output_dict["total_cost"] += total_cpu_reqs
    op.output_dict["revenue"] += total_cpu_reqs

    for sh in substrate_hosts_used_for_mapping_vnr_hosts:
        op.SUBSTRATE_HOSTS_USED.add(sh)

    print(gbl.bcolors.OKGREEN +
          "\nMAPPING SUCCESSFUL FOR THIS VNR!" + gbl.bcolors.ENDC)

    # Creating the input for the mapping function, which is returned from this function.
    cpu_reqs_for_vnr_mapping = []
    bw_reqs_for_vnr_mapping = []
    for h, substrate_host in mapped_host_x_substrate_host.items():
        cpu_reqs_for_vnr_mapping.append((substrate_host.name, cpu_reqs[h-1]))
    for (h1, h2, bw) in link_bw_reqs:
        H1 = mapped_host_x_substrate_host[h1]
        H2 = mapped_host_x_substrate_host[h2]
        bw_reqs_for_vnr_mapping.append((H1.name, H2.name, bw))

    print("\n===============================================================")
    print("op.SUBSTRATE_HOSTS_USED: ", op.SUBSTRATE_HOSTS_USED)
    print("op.SUBSTRATE_LINKS_USED: ", op.SUBSTRATE_LINKS_USED)
    print("===============================================================\n")

    return (cpu_reqs_for_vnr_mapping, bw_reqs_for_vnr_mapping)


#################################################################################

def worst_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ Worst fit algorithm, which just iterates over every host in descending order of their remaining
    cpu capacities, and based on whether it has enough CPU limit, tries to map virtual host on it,
    and then checks if all the virtual link's bandwidth requirements are satisfied or not. 
    If any of the bandwidth requirement fails, it goes on to try another substrate host 
    for the mapping of that host.

    This function shall figure out which substrate host to map each of the
    given hosts. Note that this function only reduces the bandwidths in gbl.BW_SWITCH_PAIR
    if mapping is successful. You shall ensure to call the `map_vnr_on_substrate_network`
    function to do the reduction of CPU limits, and to do the actual mapping with VLAN
    logic, traffic control, etc.
    In this function, the current logic is to return the inputs needed for calling the
    map_vnr_on_substrate_network function later (instead of calling that function from
    here itself). Reason to do this is to de-couple the functionalities, but you can
    choose to do otherwise as well.

    num_hosts: Number of hosts as provided by tenants requirement for the VNR. 
        Example: 4
    cpu_reqs: The CPU requirement values of every host in the VNR.
        Example: [20, 10, 5, 15]
    link_bw_reqs: The links as specified in the VNR, along with the expected bandwidth
        between the hosts. List of Tuple(host, host, bandwidth req)
        Example: [(1, 2, 5), (2, 3, 3), (2, 4, 6), (3, 4, 8)]
    """

    # Making a copy of this gbl.BW_SWITCH_PAIR, since we will update it at intermediate stages to
    # try out if a mapping works or not. If it doesn't work, discard that.
    COPY_BW_SWITCH_PAIR = copy.deepcopy(gbl.BW_SWITCH_PAIR)

    # For every host, obtaining what all links it needs to have with other hosts, and their bws
    hostpair_x_bw = {}
    for h in range(1, num_hosts + 1):
        for (h1, h2, bw) in link_bw_reqs:
            hostpair_x_bw[(h1, h2)] = bw
            hostpair_x_bw[(h2, h1)] = bw

    # Maintain mapped hosts, and onto which substrate hosts they were mapped.
    mapped_host_x_substrate_host = {}

    # Tracking 'cost' and 'revenue' with respect to bandwidth for output results.
    total_bw_cost_spent_on_substrate = 0
    total_bw_requested = 0
    total_cpu_reqs = 0

    substrate_hosts_used_for_mapping_vnr_hosts = []

    SORTED_gbl_HOSTS = sorted(
        gbl.HOSTS, key=lambda x: x.cpu_limit, reverse=True)

    # Going over every host to try a mapping (as per this random algorithm).
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
                local_COPY_BW_SWITCH_PAIR = COPY_BW_SWITCH_PAIR
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
                            H1.name, H2.name, bw_req, _get_bandwidth_limit_between_host_pair((H1, H2), local_COPY_BW_SWITCH_PAIR)))
                        # If bandwidth req is less than the limit between hosts, only then the
                        # mapping of this host is possible, else just remove this host mapping,
                        # and try another.
                        if bw_req <= _get_bandwidth_limit_between_host_pair((H1, H2), local_COPY_BW_SWITCH_PAIR):
                            updated_COPY_BW_SWITCH_PAIR, bw_cost_spent_on_substrate = _add_link_mapping_between_hosts(
                                (H1, H2), bw_req, local_COPY_BW_SWITCH_PAIR)
                            local_COPY_BW_SWITCH_PAIR = updated_COPY_BW_SWITCH_PAIR
                            total_bw_cost_spent_on_substrate += bw_cost_spent_on_substrate
                            total_bw_requested += bw_req
                        else:
                            host_mapped_successfully = False
                            break

                if not host_mapped_successfully:
                    # Remove mapping of host since host mapping was not successful.
                    print("Removing the mapping of {} on substrate {}".format(
                        h, substrate_host.name))
                    del mapped_host_x_substrate_host[h]
                else:
                    substrate_hosts_used_for_mapping_vnr_hosts.append(
                        substrate_host.name)
                    print("Host {} mapped on substrate host {}!".format(
                        h, substrate_host.name))
                    # Only once the mapping of this virtual host is confirmed on this substrate host,
                    # only then you update the COPY_BW_SWITCH_PAIR variable.
                    COPY_BW_SWITCH_PAIR = local_COPY_BW_SWITCH_PAIR
            # If the substrate host for mapping this host has been found, then break out
            # of inner for loop, and continue to finding the mapping for next host.
            if host_mapped_successfully:
                break

        # If you have tried all possible substrate hosts, and still dont find a mapping
        # then just return None and tell the caller that no mapping was found.
        if not host_mapped_successfully:
            print(gbl.bcolors.FAIL +
                  "\nNO MAPPING WAS FOUND FOR THIS VNR!" + gbl.bcolors.ENDC)
            return None, None

    # If we have reached till here, means that mappings were found for every host
    # and we have successfully been able to serve this VNR. Hence update the
    # gbl.BW_SWITCH_PAIR with updated reduced bandwidths.
    # Since we don't want address of the deep copied objects, we need to update the original
    # BW_SWITCH_PAIR values itself.
    _update_bw_switch_pair_values(COPY_BW_SWITCH_PAIR)
    # Updating the 'cost' and 'revenue' with respect to bandwidth.
    op.output_dict["total_cost"] += total_bw_cost_spent_on_substrate
    op.output_dict["revenue"] += total_bw_requested

    # If all hosts of vnr were mapped, then total cost of cpu can be computed
    for h in range(1, num_hosts + 1):
        total_cpu_reqs += cpu_reqs[h - 1]
    print("\ntotal_cpu_reqs: ", total_cpu_reqs, "\n")
    op.output_dict["total_cost"] += total_cpu_reqs
    op.output_dict["revenue"] += total_cpu_reqs

    for sh in substrate_hosts_used_for_mapping_vnr_hosts:
        op.SUBSTRATE_HOSTS_USED.add(sh)

    print(gbl.bcolors.OKGREEN +
          "\nMAPPING SUCCESSFUL FOR THIS VNR!" + gbl.bcolors.ENDC)

    # Creating the input for the mapping function, which is returned from this function.
    cpu_reqs_for_vnr_mapping = []
    bw_reqs_for_vnr_mapping = []
    for h, substrate_host in mapped_host_x_substrate_host.items():
        cpu_reqs_for_vnr_mapping.append((substrate_host.name, cpu_reqs[h-1]))
    for (h1, h2, bw) in link_bw_reqs:
        H1 = mapped_host_x_substrate_host[h1]
        H2 = mapped_host_x_substrate_host[h2]
        bw_reqs_for_vnr_mapping.append((H1.name, H2.name, bw))

    print("\n===============================================================")
    print("op.SUBSTRATE_HOSTS_USED: ", op.SUBSTRATE_HOSTS_USED)
    print("op.SUBSTRATE_LINKS_USED: ", op.SUBSTRATE_LINKS_USED)
    print("===============================================================\n")

    return (cpu_reqs_for_vnr_mapping, bw_reqs_for_vnr_mapping)


#################################################################################

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
    if gbl.CFG["vne_algorithm"] == "first-fit-algorithm":
        return first_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs)
    if gbl.CFG["vne_algorithm"] == "worst-fit-algorithm":
        return worst_fit_algorithm(num_hosts, cpu_reqs, link_bw_reqs)
