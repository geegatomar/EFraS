import pandas as pd

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

OUTPUT_RESULTS = {
    "algorithm": [],
    "revenue": [],
    "total_cost": [],
    "revenuetocostratio": [],
    "accepted": [],
    "total_request": [],
    "embeddingratio": [],
    "pre_resource": [],
    "post_resource": [],
    "consumed": [],
    "No_of_Links_used": [],
    "No_of_Nodes_used": [],
    "total_nodes": [],
    "total_links": [],
}


def add_row_to_excel(op):
    OUTPUT_RESULTS["algorithm"].append(op["algorithm"])
    OUTPUT_RESULTS["revenue"].append(op["revenue"])
    OUTPUT_RESULTS["total_cost"].append(op["total_cost"])
    OUTPUT_RESULTS["revenuetocostratio"].append(op["revenuetocostratio"])
    OUTPUT_RESULTS["accepted"].append(op["accepted"])
    OUTPUT_RESULTS["total_request"].append(op["total_request"])
    OUTPUT_RESULTS["embeddingratio"].append(op["embeddingratio"])
    OUTPUT_RESULTS["pre_resource"].append(op["pre_resource"])
    OUTPUT_RESULTS["post_resource"].append(op["post_resource"])
    OUTPUT_RESULTS["consumed"].append(op["consumed"])
    OUTPUT_RESULTS["No_of_Links_used"].append(op["No_of_Links_used"])
    OUTPUT_RESULTS["No_of_Nodes_used"].append(op["No_of_Nodes_used"])
    OUTPUT_RESULTS["total_nodes"].append(op["total_nodes"])
    OUTPUT_RESULTS["total_links"].append(op["total_links"])


def compute_remaining_output_parameters():
    # Some of the parameters of `output_dict` are directly populated from code.
    # And others such as 'ratios' are computed here.
    output_dict["embeddingratio"] = output_dict["accepted"] / \
        output_dict["total_request"]
    output_dict["revenuetocostratio"] = output_dict["revenue"] / \
        output_dict["total_cost"]
    output_dict["consumed"] = output_dict["total_cost"]
    output_dict["post_resource"] = output_dict["pre_resource"] - \
        output_dict["consumed"]
    # Reason for diving by 2 is that we have the links (a, b) and (b, a) stored twice
    output_dict["No_of_Links_used"] = len(SUBSTRATE_LINKS_USED) / 2
    output_dict["No_of_Nodes_used"] = len(SUBSTRATE_HOSTS_USED)
    print("\n\noutput_dict: ", output_dict, "\n")

    # Output the results to excel sheet as well.
    add_row_to_excel(output_dict)
    excel = pd.DataFrame(OUTPUT_RESULTS)
    excel.to_excel("Results.xlsx")
