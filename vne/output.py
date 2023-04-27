import pickle

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
}

# Variables used to store all the links and hosts of the substrate network
# used by all VNRs collectively.
SUBSTRATE_LINKS_USED = set()
SUBSTRATE_HOSTS_USED = set()


def compute_remaining_output_parameters():
    # Some of the parameters of `output_dict` are directly populated from code.
    # And others such as 'ratios' are computed here.
    try:
        output_dict["embeddingratio"] = output_dict["accepted"] / \
            output_dict["total_request"]
    except:
        output_dict["embeddingratio"] = None
    try:
        output_dict["revenuetocostratio"] = output_dict["revenue"] / \
            output_dict["total_cost"]
    except:
        output_dict["revenuetocostratio"] = None
    output_dict["consumed"] = output_dict["total_cost"]
    output_dict["post_resource"] = output_dict["pre_resource"] - \
        output_dict["consumed"]
    # Reason for diving by 2 is that we have the links (a, b) and (b, a) stored twice
    output_dict["No_of_Links_used"] = len(SUBSTRATE_LINKS_USED) / 2
    output_dict["No_of_Nodes_used"] = len(SUBSTRATE_HOSTS_USED)
    print("\n\noutput_dict: ", output_dict, "\n")

    # Write the output dict to a pickle file, which will be read by the runner.py file.
    with open('output_dict.pickle', 'wb') as handle:
        pickle.dump(output_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
