# Virtual Network Embedding (VNE) using mininet (SDN), with RYU controller.
# Command to run file:      sudo python3 main.py

from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.node import Controller, RemoteController, OVSController
from mininet.cli import CLI
from mininet.util import custom
from mininet.node import CPULimitedHost
import gbl
import helpers as hp
import substrate
import vnr_mapping
import tests
import vne_algorithms
import json

# Note that all examples for the variables/data structures below are for the topology
# when sl_factor = 3, ll_factor = 2, hl_factor = 2.
# Topology visualization for this example can be found here: https://tinyurl.com/mr3c5ap3


def runVNE(sl_factor=2, ll_factor=3, hl_factor=5):
    """ Generates spine-leaf topology network in mininet based on the multiplier factors 
    given for spine layer (sl), leaf layer (ll), and host layer (hl). Do not exceed 240 for each of 
    these factors. 
    Does the virtual network embedding for specified VNRs, and runs necessary tests.
    Example of topology where (sl=3, ll=2, hl=2) can be found here: https://tinyurl.com/mr3c5ap3
    sl_factor: Number of switches in spine layer (sl).
    ll_factor: Number of leaf layer (ll) switches under the subnet of each spine switch.
    hl_factor: Number of host layer (hl) hosts under (connected to) each leaf switch.
    """
    gbl.NUM_HOSTS_PER_LEAF_SWITCH = hl_factor

    substrate.generate_topology(sl_factor, ll_factor, hl_factor)

    topo = substrate.SpineLeafSubstrateNetwork()
    substrate.populate_path_between_hosts()

    # Connecting to remote controller, since we use the RYU controller to populate
    # the flow table entries for ARP flooding.
    host = custom(CPULimitedHost, sched='cfs')
    net = Mininet(topo, host=host, controller=RemoteController)
    net.start()

    # Add ARP table entries for the defaultRoute IPs.
    for host in gbl.HOSTS:
        hp.add_arp_entry_for_host(host, net)

    # Populating flow entries for substrate network.
    substrate.add_flow_entries_for_substrate_network(net)

    # Creating input VNRs.
    cfg_vnrs = gbl.CFG["vnrs"]
    inputs_for_vnr_mapping_algo = hp.create_vnrs(
        num_vnrs=cfg_vnrs["num_vnrs"],
        min_nodes=cfg_vnrs["min_nodes"],
        max_nodes=cfg_vnrs["max_nodes"],
        probability=cfg_vnrs["probability"],
        min_cpu=cfg_vnrs["min_cpu"],
        max_cpu=cfg_vnrs["max_cpu"],
        min_bw=cfg_vnrs["min_bw"],
        max_bw=cfg_vnrs["max_bw"])

    total_num_vnrs = len(inputs_for_vnr_mapping_algo)
    num_vnrs_mapped = 0
    for i, (num_hosts, cpu_reqs, link_reqs) in enumerate(inputs_for_vnr_mapping_algo):
        cpu_reqs_for_vnr_mapping, bw_reqs_for_vnr_mapping = vne_algorithms.random_mapping_algorithm(
            num_hosts, cpu_reqs, link_reqs)
        if not cpu_reqs_for_vnr_mapping:
            print("Unable to map VNR{}...".format(i))
            continue
        print("\nBW_SWITCH_PAIR after mapping VNR {}...".format(i))
        for (s1, s2), bw in gbl.BW_SWITCH_PAIR.items():
            print("Bandwidth between switches {} and {} is {}".format(
                s1.name, s2.name, bw))
        vnr_mapping.map_vnr_on_substrate_network(
            net, cpu_reqs_for_vnr_mapping, bw_reqs_for_vnr_mapping)
        num_vnrs_mapped += 1
    print("\n", gbl.bcolors.OKCYAN + "Successfully mapped {} / {} Virtual Network Requests using the {} algorithm!".format(
        num_vnrs_mapped, total_num_vnrs, gbl.CFG["vne_algorithm"]) + gbl.bcolors.ENDC, "\n")

    hp.update_cpu_limits_of_substrate_hosts_after_vnr_mapping(net)

    tests.test_cpu_limits_for_all_hosts(net)
    tests.test_ping_within_vnr_vhosts(net)
    tests.test_iperf_bandwidth_within_vnr_vhosts(net)

    # show_flow_table_entries(net)
    # net.pingAll()

    CLI(net)
    net.stop()


def main():
    f = open('configurations.json')
    gbl.CFG = json.load(f)
    f.close()

    cfg_s = gbl.CFG["substrate"]

    runVNE(sl_factor=cfg_s["sl_factor"],
           ll_factor=cfg_s["ll_factor"], hl_factor=cfg_s["hl_factor"])


if __name__ == '__main__':
    setLogLevel('info')
    main()
