import pickle
import gbl
from statistics import mean
from main_classes import Host

output_dict = {
    "algorithm": None,

    # Sum of all demanded resources (cpu & bw) of VNRs.
    "revenue": 0,
    # Sum of all spent resources (cpu & bw) for embedding VNRs.
    "total_cost": 0,
    # Ratio of revenue / total_cost
    "revenuetocostratio": None,

    # Number of accepted requests.
    "accepted": 0,
    "total_request": 0,
    "embeddingratio": None,

    # Pre-resource is the sum of all resources (cpu & bw) before embedding.
    "pre_resource": 0,
    # Post-resource is the sum of all resources (cpu & bw) after embedding.
    "post_resource": 0,
    # Consumed = Post - Pre.
    "consumed": 0,

    # Number of substrate links onto which any vnr's links are mapped, i.e.
    # number of substrate links used for any mapping.
    "No_of_Links_used": 0,
    # Number of substrate nodes onto which any vnr's hosts are mapped, i.e.
    # number of substrate nodes used for any mapping.
    "No_of_Nodes_used": 0,

    # Total number of hosts in the substrate network
    "total_nodes": 0,
    # Total number of links in the substrate network
    "total_links": 0,

    # Average Bandwidth Utilization is defined as the average bandwidth
    # utilization of the used links in the substrate network. It can be
    # calculated by first calculating the bandwidth utilization of each
    # link that is being used, and next taking the average of all these values.
    "avg_bandwidth_utilization": None,
    # Similar to average bandwidth utilization, average CRB utilization is
    # defined as the average CRB utilization of used nodes in the substrate
    # network. This can be calculated by first calculating the CRB utilization
    # of each node that is being used, and next taking the average of all these
    # values.
    "avg_crb_utilization": None,
    # Average link utilization is defined as the total number of substrate
    # links utilized during the embedding of the VNRs divided by the total
    # number of links in the substrate network.
    "avg_link_utilization": None,
    # Average node utilization is defined as the total number of substrate nodes
    # utilized during the embedding of the VNRs divided by the total number of
    # nodes in the substrate network.
    "avg_node_utilization": None
}

# Variables used to store all the links and hosts of the substrate network
# used by all VNRs collectively.
SUBSTRATE_LINKS_USED = set()
SUBSTRATE_HOSTS_USED = set()


def get_avg_bandwidth_utilization():
    bandwidth_utilization_of_used_links = []
    for (s1_name, s2_name), orig_bw in gbl.ORIGINAL_SWITCH_PAIR_x_BW.items():
        bw_after_mappings = gbl.SWITCH_PAIR_x_BW[(s1_name, s2_name)]
        # If the link has been utilized, then append its utilization to list.
        if bw_after_mappings != orig_bw:
            bandwidth_utilization_of_this_link = (
                orig_bw - bw_after_mappings) / (orig_bw)
            bandwidth_utilization_of_used_links.append(
                bandwidth_utilization_of_this_link)
    try:
        return mean(bandwidth_utilization_of_used_links) * 100
    except:
        return None


def get_avg_crb_utilization():
    crb_utilization_of_used_hosts = []
    for substrate_host in gbl.HOSTS:
        # If the substrate host has been utilized in mapping, then append to list.
        if substrate_host.original_cpu_limit != substrate_host.cpu_limit:
            crb_utilization_of_this_host = (
                substrate_host.original_cpu_limit - substrate_host.cpu_limit) / substrate_host.original_cpu_limit
            crb_utilization_of_used_hosts.append(crb_utilization_of_this_host)
    try:
        return mean(crb_utilization_of_used_hosts) * 100
    except:
        return None


def compute_remaining_output_parameters():
    # Some of the parameters of `output_dict` are directly populated from code.
    # And others such as 'ratios' are computed here.
    try:
        output_dict["embeddingratio"] = (
            output_dict["accepted"] / output_dict["total_request"]) * 100
    except:
        output_dict["embeddingratio"] = None
    try:
        output_dict["revenuetocostratio"] = (
            output_dict["revenue"] / output_dict["total_cost"]) * 100
    except:
        output_dict["revenuetocostratio"] = None
    output_dict["consumed"] = output_dict["total_cost"]
    output_dict["post_resource"] = output_dict["pre_resource"] - \
        output_dict["consumed"]
    # Reason for diving by 2 is that we have the links (a, b) and (b, a) stored twice
    output_dict["No_of_Links_used"] = len(SUBSTRATE_LINKS_USED) / 2
    output_dict["No_of_Nodes_used"] = len(SUBSTRATE_HOSTS_USED)

    try:
        output_dict["avg_link_utilization"] = (
            output_dict["No_of_Links_used"] / output_dict["total_links"]) * 100
    except:
        output_dict["avg_link_utilization"] = None
    try:
        output_dict["avg_node_utilization"] = (
            output_dict["No_of_Nodes_used"] / output_dict["total_nodes"]) * 100
    except:
        output_dict["avg_node_utilization"] = None

    output_dict["avg_bandwidth_utilization"] = get_avg_bandwidth_utilization()
    output_dict["avg_crb_utilization"] = get_avg_crb_utilization()

    print("\n\noutput_dict: ", output_dict, "\n")

    # Write the output dict to a pickle file, which will be read by the runner.py file.
    with open('output_dict.pickle', 'wb') as handle:
        pickle.dump(output_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
