import gbl


def _get_bandwidth_limit_between_host_pair(host_pair):
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
            bw_limit = min(bw_limit, gbl.BW_SWITCH_PAIR[each_link])
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
    """ This function is a helper for the `random_mapping_algorithm` algorithm.
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
    (h1, h2) = host_pair
    if int(h1.name[1:]) > int(h2.name[1:]):
        host_pair = (h2, h1)

    path = gbl.PATH_BETWEEN_HOSTS[host_pair]
    for each_link in path:
        if COPY_BW_SWITCH_PAIR.get(each_link):
            COPY_BW_SWITCH_PAIR[each_link] -= bw_req
            # Update bothways bw, since we are storing that twice.
            (node1, node2) = each_link
            other_way_link = (node2, node1)
            COPY_BW_SWITCH_PAIR[other_way_link] -= bw_req


# Currently, I'm implementing a random algorithm, which randomly does the mapping based
# on no specific logic, but ensures to satisfy all the requirements as given by VNR tenant.


def random_mapping_algorithm(num_hosts, cpu_reqs, link_bw_reqs):
    """ Random mapping algorithm, which just iterates over every possible host once,
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
    COPY_BW_SWITCH_PAIR = gbl.BW_SWITCH_PAIR

    # For every host, obtaining what all links it needs to have with other hosts, and their bws
    hostpair_x_bw = {}
    for h in range(1, num_hosts + 1):
        for (h1, h2, bw) in link_bw_reqs:
            hostpair_x_bw[(h1, h2)] = bw
            hostpair_x_bw[(h2, h1)] = bw

    # Maintain mapped hosts, and onto which substrate hosts they were mapped.
    mapped_host_x_substrate_host = {}

    # Going over every host to try a mapping (as per this random algorithm).
    for h in range(1, num_hosts + 1):
        host_mapped_successfully = False
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
                            H1.name, H2.name, bw_req, _get_bandwidth_limit_between_host_pair((H1, H2))))
                        # If bandwidth req is less than the limit between hosts, only then the
                        # mapping of this host is possible, else just remove this host mapping,
                        # and try another.
                        if bw_req <= _get_bandwidth_limit_between_host_pair((H1, H2)):
                            _add_link_mapping_between_hosts(
                                (H1, H2), bw_req, COPY_BW_SWITCH_PAIR)
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
    gbl.BW_SWITCH_PAIR = COPY_BW_SWITCH_PAIR

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
    if gbl.CFG["vne_algorithm"] == "random-testing-algorithm":
        random_mapping_algorithm(num_hosts, cpu_reqs, link_bw_reqs)
