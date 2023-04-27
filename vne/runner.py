# The runner.py file is used to execute the main.py for multiple iterations and for
# multiple vne algorithms at once, as per the specifications in the configurations.json
# file.
# Command to run this file: `sudo python3 runner.py`

# NOTE: To run this file, you must make sure to specify all the configurations in
# the configurations.json file; especially these 3 configurations which are specific
# to this runner.py file (which main.py doesn't look at):
# - Number of iterations to run for:   "iterations": 5,
# - List of VNE algorithms to run on:  "vne_algorithms": ["first-fit-algorithm", "worst-fit-algorithm"],
# - List of number of VNRs to run for: "num_vnrs_list": [1, 2, 3]

import gbl
import json
import pandas as pd
import os
import time
import random
import pickle


OUTPUT_RESULTS = {
    "seed": [],
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
    "total_execution_time": [],
    "avg_bandwidth_utilization": [],
    "avg_crb_utilization": [],
    "avg_link_utilization": [],
    "avg_node_utilization": []
}


def add_row_to_excel(op, seed_value):
    OUTPUT_RESULTS["seed"].append(seed_value)
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
    OUTPUT_RESULTS["total_execution_time"].append(op["total_execution_time"])
    OUTPUT_RESULTS["avg_bandwidth_utilization"].append(
        op["avg_bandwidth_utilization"])
    OUTPUT_RESULTS["avg_crb_utilization"].append(op["avg_crb_utilization"])
    OUTPUT_RESULTS["avg_link_utilization"].append(op["avg_link_utilization"])
    OUTPUT_RESULTS["avg_node_utilization"].append(op["avg_node_utilization"])


def main():
    f = open('configurations.json')
    gbl.CFG = json.load(f)
    f.close()

    # Clean up (mininet)
    print("\nPerforming clean up (mininet)...\n\n")
    os.system('sudo mn -c')

    num_iterations = gbl.CFG["iterations"]
    vne_algorithms_to_run = gbl.CFG["vne_algorithms"]
    num_vnrs_list = gbl.CFG["num_vnrs_list"]

    for iter in range(1, num_iterations + 1):
        print("\n\nRUNNING ITERATION {}...".format(iter))
        seed_value = random.randint(1, 10000)

        for num_vnrs in num_vnrs_list:

            for vne_algo in vne_algorithms_to_run:
                print("\n\nRUNNING VNE ALGORITHM {}  (iteration = {}, num vnrs = {}, seed = {})...\n\n".format(
                    vne_algo, iter, num_vnrs, seed_value))

                # Running the `main.py` by specifying the command line arguments for the
                # seed value and the vne algorithm to use for vnr mapping.
                start = time.time()
                os.system(
                    'sudo python3 main.py -s {} -a {} -n {}'.format(seed_value, vne_algo, num_vnrs))
                end = time.time()

                try:
                    # Read results of this one iteration of one vne algorithm from pickle file, and
                    # add the row to excel's output results.
                    with open('output_dict.pickle', 'rb') as handle:
                        output_dict = pickle.load(handle)
                    # Compute execution time in seconds
                    output_dict["total_execution_time"] = end - start
                    # The same seed value signifies that the randomly generated configurations were same
                    # for the multiple vne algorithms.
                    add_row_to_excel(output_dict, seed_value)
                except:
                    print("Unable to obtain output_dict results for iteration={}, num_vnrs={}, vne_algo={}".format(
                        iter, num_vnrs, vne_algo))

                time.sleep(2)

    excel = pd.DataFrame(OUTPUT_RESULTS)
    excel.to_excel("Results.xlsx")

    try:
        # Delete the intermediary pickle file after the Results.xlsx has been generated.
        os.remove("output_dict.pickle")
    except:
        pass


if __name__ == '__main__':
    main()
