# Virtual Network Embedding (VNE) emulation using Mininet


## Getting Started
- Install [Mininet](http://mininet.org/download/)
- Install [RYU controller](https://ryu.readthedocs.io/en/latest/getting_started.html)
- Instructions to run:
    - Clone the repo </br>
        ```
        $ git clone https://github.com/geegatomar/Official-VNE-SDN-Major-Project.git
        ```
    - Move/copy the ryu controller file `ryu_controller_vne.py` to the location where you installed RYU, into the directory `ryu/app/`
    - Start the ryu controller </br>
        ``` 
        $ ryu-manager ryu/app/ryu_controller_vne.py 
        ```
    - Run the mininet code (in another terminal) </br>
        ``` 
        $ sudo python3 vne/main.py 
        ```
  

## Overview
This project uses mininet to emulate a network topology for the Virtual Network Embedding (VNE) problem. Mininet provides a virtual test bed and development environment for software-defined networks (SDN).
- The switches used in the mininet topology are Open vSwitches, and hence can be configured using the Open Flow protocol. The configuration of OVSSwitches can be done using the ovs-vsctl, ovs-ofctl commands, or collectively via an SDN controller (such as RYU controller). In our project we use RYU controller for populating basic entries that are common to all switches at the beginning, and then use ovs-vsctl and ovs-ofctl commands for populating switch-specific entries.
- RYU controller is used to populate basic common entries; in our case for the ARP flooding entries in the flow tables.
- Traffic control: htb qdiscs are used to restrict the bandwidth of the links between nodes in the network, and filtering is also performed based on specific types of traffic.
- CPU capacity limiting is done for each host, by specifying how much percentage of the machine's CPU it shall restrict for each host in the mininet network. Mininet APIs are used to do this, although internally concepts of cgroups apply.
- iperf and ping tests are performed to test for the bandwidth of the links, and net.runCpuLimitTest() function provided by mininet to test for CPU (which internally runs an infinite while loop to test for the resources).
To run the code; there is one mininet (.py) file which needs to be run with mininet. The other simple ryu controller file must be running to ensure that the ryu controller is up and running on port 6553.


## Project Modules
The project work is broadly divided into the following parts:
### Substrate topology generation
1. Spine leaf topology creation
2. IP addressing of nodes
3. Flow table entry population of OVSwitch
### Mapping VNRs on substrate network
1. VNR algorithm to select which substrate host to map the virtual host onto
2. The actual mapping logic; IP addressing of virtual hosts, VLAN isolation, updating flow table entries, etc.
### Testing
1. Pings for connectivity within VNR hosts
2. Iperf for bandwidth links
3. Cpu limit tests

---

# Substrate Network

## Spine-Leaf Topology
Spine-Leaf Architecture is a two-layer, full-mesh topology composed of a leaf layer and a spine layer, with the leaf and spine switches. </br>
![spine-and-leaf-architecture](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/spine-and-leaf-architecture.jpg?raw=true)
</br>
The substrate network (i.e. physical network onto which Virtual Network Requests will be mapped) in our project follows a spine-leaf architecture. Although we have added an additional layer of switches, called the 'host switch layer' for each host. More on why we did this is in the sections below.

</br>

## IP Addressing
The subnet for layer 1 (spine) switches starts with `10.0.0.0/8`, and addressing of further switches is done by varying the first octet in the dot-decimal notation.. So if there are 3 switches in layer 1 (spine), they will be addressed as '10.0.0.0/8', '11.0.0.0/8', '12.0.0.0/8', and will be named s1_1, s1_2, s1_3 (denoting layer 1 switch 1, 2, 3 respectively). The number of switches in the spine layer in represented as **sl_factor**.

The **ll_factor** represents the number of leaf layer switches that come under the same subnet of each spine layer switch. Hence the total number of leaf layer switches is `sl_factor * ll_factor`.
For every ll_factor number of leaf layer switches under each switch layer switch, the addressing is done by varying the second octet in the dot-decimal notation. So if the ll_factor is 2, then the leaf switches under the '10.0.0.0/8 spine switch' are `10.0.0.0/16` and `10.1.0.0./16`. And the leaf switches under the '11.0.0.0/8 spine switch' are `11.0.0.0/16` and `11.1.0.0./16`, and so on.

The **hl_factor** represents the number of hosts connected to each leaf layer switch. So the total number of hosts in the network is `sl_factor * ll_factor * hl_factor`. For every hl_factor number of hosts under each leaf layer switch, the addressing is done by varying the third octet in the dot-decimal notation. So if the hl_factor is 2, then the hosts under the '12.1.0.0/16 leaf switch' are addressed as`12.1.0.0` and `12.1.1.0`.

![spine-and-leaf-ip-addressed](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/spine_leaf_ip_addressed.png?raw=true)
</br>
In this example; sl_factor = 3, ll_factor = 2, and hl_factor = 2.


</br>

## Modified spine-leaf topology
Since we eventually map virtual nodes (of VNRs) onto these substrate network hosts, to make the implementation (for VNR mapping) logically easier and more intuitive, we have added an additional layer of switches called the 'host layer switches'. Instead of every host being attached directly to the leaf layer switch (as seen above), now there is one additional switch of the '*host layer switch*' in between.
The only modification in the above diagram is the addition of 'host layer switches'; as can be seen below.
</br></br>
![spine-and-leaf-ip-addressed-modified](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/spine_leaf_ip_addressed_modified.png?raw=true)


</br>

## Flow table entry population
Since we want the path taken by any packet from one host to another host to be a *deterministic path*, we populate the flow table entries of every switch accordingly.

- For spine layer switches: For every packet that the spine switch gets, it sends it out downwards towards the leaf layer switch depending on the destination IP address of the packet. For example, if (in the above image), the switch s1_2 gets a packet destined for host h11 (having IP address '12.1.0.0'), then it will send the packet to switch s2_6 (having subnet '12.1.0.0/16') because the host h11 comes under the subnet of s2_6.

- For leaf layer switches: For every packet that the leaf switch gets, there could be 2 situations; either the packet shall travel upwards towards the spine layer switches, or downwards towards the host layer switches. 
    - Towards spine layer switches (upwards): We consider the larger of the src and dst subnets to find the spine layer switch to forward the packet. Reason for doing this (and not just basing the decision off of destination address) is because if we decide the spine layer switch only based on the destination address, then the request & reply packets will not follow the same route. For example, in the topology (sl=3, ll=2, hl=2), if h1 (10.0.0.0) wants to communicate with h6 (11.0.1.0), it will communicate via the switch s1_2 (because dst_ip is under 11 subnet). But when h6 sends reply to h1, then the dst_ip is considered of h1, which is under 10 subnet, and would now route via s1_1. Hence, to avoid this problem, we make the decision of selecting spine switch based on the larger of the two addresses. Hence, in this example packet between h1 (10.0.0.0) and h6 (11.0.1.0) will be travel via the spine switch s1_2 ('11 /8'), and not s1_1 ('10 /8'), because 11 > 10.
    - Towards host layer switches (downwards): This is a simple decision based on the destination address of the host, the packet is output on the respective output port of leaf switch accordingly. For example, if the spine switch s2_1 gets a packet for host h2 (10.0.1.0), it will send it out to the host switch sh2 (10.0.1/24).

- For host layer switches: For everypacket that the host layer switch gets, there could be 2 situations; either the packet is for that host under the subnet of that switch, or its not.
    - Towards host: If the destination ip address corresponds to the address of the host attached to the host layer switch, then it is directly delivered to it (the only host attached to it).
    - Towards leaf layer switches: If the destination ip address is anything but the above case, then it is sent upwards to the only leaf layer switch that the host is attached to.

### Example
1. Packet needs to be sent from h1 (10.0.0.0) to h10 (12.0.1.0). The path followed by the packet will be:
    - For **h1 to h10** (request): &nbsp; h1  &rarr;  sh1  &rarr;  s2_1  &rarr;  s1_3  &rarr;  s2_5  &rarr;  sh10  &rarr;  h10
    - For **h10 to h1** (reply): &nbsp; &nbsp; h10 &rarr;  sh10  &rarr;  s2_5  &rarr;  s1_3  &rarr;  s2_1  &rarr;  sh1 &rarr;  h1
    </br> Note that the path followed by packet for request and reply must go through the same set of switches.

2. Packet needs to be sent from h5 (11.0.0.0) to h6 (11.0.1.0). The path followed by the packet will be:
    - For **h5 to h6** (request): &nbsp; h5  &rarr;  sh5  &rarr;  s2_3  &rarr;  sh6  &rarr;  h6
    - For **h6 to h5** (reply): &nbsp; &nbsp; h6  &rarr;  sh6  &rarr;  s2_3  &rarr;  sh5  &rarr;  h5
    </br> Note that in this example the packet did not have to go till the spine layer at all (unlike in the previous example).
</br>

![flow-table-example-diagram](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/flow_table_example.png?raw=true)

---


# VNR Mapping

So far we have established the substrate (physical) network. Next, we shall look at how to *map* the virtual nodes of the VNR (Virtual Network Request) onto the substrate network nodes, and how the IP addressing of the virtual hosts is performed. We explored multiple options for mapping virtual nodes onto physical nodes such as encapsulation, VXLAN, VLAN, etc. but ultimately chose to go ahead with the VLAN approach.


## IP addressing of virtual hosts
Every virtual host is given the next available IP address in the subnet of the 'host layer switch' connected to the host that it is being mapped on. For example, if a virtual host 'vh1' has to be mapped onto the substrate host 'h3' ('10.1.0.0'), then it is given the IP address of '10.1.0.1'. And the next virtual host 'vh2' to be mapped on the same substrate host 'h3' is given the next available IP address of '10.1.0.2'. The next available IP address is obtained by incrementing the values of the fourth octet in the dot-decimal notation of the IP addresses provided.
Logically, it means that they all are under the host with IP subnet of '10.1.0 /24', which is basically the subnet of the corresponding '*host layer switch*', here 'sh3'. Hence, we are simplifying the process of IP addressing by assigning virtual hosts addresses *as if they belong to the substrate network*. (This saves us the hassle of doing additional mappings and encapsulation, simplying the implementation). 

![vnr-mapping-basic-diagram](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/vnr_mapping_basic.png?raw=true)


This was also the *reason to add the additional layer of host switches* (i.e. Modified spine-leaf topology) so that the host switches can represent every block of substrate network host, and every additional host under it would represent the virtual hosts mapped onto it.

### Example
Consider for the given substrate network (sl_factor = 3, ll_factor = 2, and hl_factor = 2), we get two Virtual Network Requests, such that:
- VNR1, having 2 virtual hosts (let's call them vnr1_vh1, vnr1_vh2). 
- VNR2, having 3 virtual hosts (let's call them vnr2_vh1, vnr2_vh2, vnr2_vh3).

In the example here, the 2 virtual hosts of VNR1 were mapped onto the substrate hosts h3 and h7. And the 3 virtual hosts of VNR2 were mapped onto the substrate hosts h3, h4 and h6. 

![vnr-mapping-example-diagram](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/vnr_mapping_example.png?raw=true)

Note that the IP addressing of these virtual hosts is done as per the logic explained above.

</br>

## VLAN Isolation
Once the IP addressing of virtual hosts was figured out, the connectivity amongst every pair of host (all substrate and virtual hosts) is inherently present because of how the flow table entries were initially populated. This meant that a host of one VNR is able to communicate with a host of another VNR; and this behavior is undesirable. This is why we added VLAN logic to provide isolation between VNRs, i.e. hosts of one VNR shall be able to communicate with each other, but not communicate with any other host on the network. 

Virtual LAN (VLAN) is used to logically partition a network. For implementing this, VLAN IDs have been used (where every VNR is given a new VLAN ID), and additional entries were added to the flow tables of the switches to confirm isolation between different VLANs.
Further implementation details can be found here: https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/00400218b6b6a36851f6ec02ecd18bf090155340/vne/vnr_mapping.py#L122

</br>

## Bandwidth Restriction
The bandwidth for every link in the network has a limit as defined by the substrate network links. When mapping a VNR's virtual links onto the substrate network links, the bandwidth for that link must be restricted to the requirement it had specified, and this is implemented using **traffic control**, by making use of ***HTB*** (Hierarchical Token Bucket) filtering qdiscs.

Traffic control filtering rules are attached based on the destination IP address of the packets, to decide which class of the qdisc that traffic belongs to. 
Further implementation details can be found here: https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/00400218b6b6a36851f6ec02ecd18bf090155340/vne/vnr_mapping.py#L139

</br>

## CPU Restriction
The CPU performance is modeled using CPU control groups (cgroups). We make use of mininet's API for this called **CPULimitedHost** (which internally makes use of cgroups to implement this in Linux).

</br>

---


# VNE Algorithm

The Virtual Network Embedding (VNE) algorithm is the actual logic for selecting the substrate network resources for mapping the Virtual Network Request. This involves mapping of the nodes/hosts and mapping of links onto substrate network's resources.

## Additional data structures
We maintain additional data structures to model the network/graph, and keep track of the remaining bandwidths between links after VNRs are being mapped. When a virtual link is mapped onto the substrate network's link, the bandwidth of the substrate network is not directly reduced. Instead, this information is tracked using these additional graph data structures (Reason: If you directly reduce the bandwidth of the actual links on the mininet network, then later when you test with iperf, you'd not get the expected bandwidth because you've subtracted from that).

The exact paths (deterministic) between every pair of hosts is initially populated. More information can be found here:
https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/835fd8e4556d0622054f2b6b4738af64d8e659b4/vne/substrate.py#L195

When the VNE algorithm runs to select set of substrate hosts (for mapping the virtual hosts of the VNR), it needs to check for CPU limits and bandwidth limits, and these data structures which we maintain are useful in doing all these checks.

</br>

## Random testing algorithm
As of now, we have implemented a random testing algorithm as the default VNE algorithm. It randomly does the mapping based on no specific logic (just by going over every host in order and performing the mapping greedily if its possible), but ensures to satisfy all the requirements (bandwidth & CPU) as given by VNR tenant.

---

# Expected Results

#### Shows how many VNRs were successfully mapped onto the substrate network (by using the selected VNE algorithm)
In this example, mapping was found for 3 out of the 4 VNRs.
![results](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/results.png?raw=true)

#### CPU tests passing
![results](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/results_cpu.png?raw=true)

#### Ping tests passing
![results](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/results_ping.png?raw=true)

#### Iperf tests passing
![results](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/results_iperf.png?raw=true)


---

# Additional Information

## Why RYU Controller?
Since the paths between every pair of host in our network is deterministic, the population of flow tables must be done at the beginning of network establishment itself. The logic for which is dependant on which type of switch it is (spine, leaf, or host layer switch), and is very specific to each switch, as can be seen in implementation here:

https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/5812f005daafef1e5eb86099ccd546e45c9a7c48/vne/substrate.py#L148

Hence, it made sense to write code for this 'not-so-generalizable' logic in python mininet code itself, instead of putting it in a separate RYU controller. The controller is good at adding flow table entries for more generalizable (i.e. common for all switches) such as ARP flooding.

The RYU controller can easily be eliminated if those ARP flooding logic is incorporated in the python mininet code itself. It just made logical sense to populate it via a controller since it's common for all switches, irrespective of which type of switchit is (spine, leaf, or host layer switch).
