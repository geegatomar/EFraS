# GLOBAL Variables shared accross files; defined here

# Colors for printing output to terminal.
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# Mapping of host names to the Host objects created in the spine-leaf topology; both substrate and virtual hosts included.
# Example: {'h1': <__main__.SubstrateHost object at 0x7f9b8daa73a0>, 'h2': <__main__.SubstrateHost object at 0x7f9b8daa7490>,
# 'vnr1_vh1': <__main__.VNRVirtualHost object at 0x7f9b8d223610>, 'vnr1_vh2': <__main__.VNRVirtualHost object at 0x7f9b8d222140>}
HOSTNAME_x_HOST = {}
# All the spine layer switches created in the spine-leaf topology.
# Example: [<__main__.Switch object at 0x7f9bccbf1e10>, <__main__.Switch object at 0x7f9b8daa7340>]
SPINE_SWITCHES = []
# All the leaf layer switches created in the spine-leaf topology.
# Example: [<__main__.Switch object at 0x7f9b8daa7310>, <__main__.Switch object at 0x7f9b8daa73d0>]
LEAF_SWITCHES = []
# All the host switches created in the spine-leaf topology.
# Example: [<__main__.Switch object at 0x7f9b8daa7430>, <__main__.Switch object at 0x7f9b8daa74f0>]
HOST_SWITCHES = []
# All the hosts in the spine-leaf topology network.
# Example: [<__main__.SubstrateHost object at 0x7f9b8daa73a0>, <__main__.SubstrateHost object at 0x7f9b8daa7490>]
HOSTS = []


# Number of hosts connected to every leaf switch. This variable is from user as
# hl_factor argument, and populated.
NUM_HOSTS_PER_LEAF_SWITCH = 1


# Mapping of spine layer 'ip subnet' and the 'Switch' object. 'x' denotes 'mapping of'.
# Example: {'10': Switch('s1_1'), '11': Switch('s1_2'), '12': Switch('s1_3')}
SPINE_LAYER_IP_SUBNET_x_SWITCH = {}
# Mapping of leaf layer 'ip subnet' and the 'Switch' object.
# Example: {'10.0': Switch('s2_1'), '10.1': Switch('s2_2'), '11.0': Switch('s2_3'),
# '11.1': Switch('s2_4'), '12.0': Switch('s2_5'), '12.1': Switch('s2_6')}
LEAF_LAYER_IP_SUBNET_x_SWITCH = {}
# Mapping of host switches 'ip subnet' and the 'Switch' object.
# Example: {'10.0.0': Switch('sh1'), '10.0.1': Switch('sh2'), '10.1.0': Switch('sh3')}
HOST_LAYER_IP_SUBNET_x_SWITCH = {}


# Graph related data structures needed to execute the actual VNR mapping algorithms.

# The full path between every 2 hosts. Consists of every switch encountered hop by hop in the
# deterministic path between the given host pair.
# Note that in the example below 'switch names' and 'host names' are shown, but in the
# datastructure, we are storing the whole Host and Switch object, not just the names.
# Example: {(h1, h2): [('h1', 'sh1'), ('sh1', 's2_1'), ('s2_1', 'sh2'), ('sh2', 'h2')]
# (h1, h3): [('h1', 'sh1'), ('sh1', 's2_1'), ('s2_1', 's1_1'), ('s1_1', 's2_2'), ('s2_2', 'sh3'), ('sh3', 'h3')]}
PATH_BETWEEN_HOSTS = {}


# Bandwidth of the link between the given switch pair. This variable is used to keep track
# of whether there is enough link bandwidth when trying out new mappings. And hence is updated
# in the `vnr_mapping` module when a VNR is being served.
# Switch pair is specified in Names (strings) instead of the objects itself.
# Example: {('s1_1', 's2_1'): 29, ('s2_1', 's1_1'): 29}
SWITCH_PAIR_x_BW = {}

# The original switch pair bw values which is initialized to SWITCH_PAIR_x_BW, and is not
# updated unlike SWITCH_PAIR_x_BW (which is updated throughout the execution of the program).
ORIGINAL_SWITCH_PAIR_x_BW = {}

# List of MappedVNR objects. Consists of information of all the Virtual Network Requests that
# have been mapped and served in the topology network.
MAPPED_VNRS = []

# The user configurable values obtained from `configurations.json` file populate this variable.
CFG = None

# Seed value used for generating the random numbers for topology.
SEED = None
