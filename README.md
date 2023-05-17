# Virtual Network Embedding (VNE) emulation using Mininet


## Getting Started
- Install [Mininet](http://mininet.org/download/)

- Install dependency packages </br>
     ```
     $ sudo pip install networkx
     $ sudo apt-get install python3-openpyxl
     ```

- **Instructions to run**:
    - Clone the repo </br>
        ```
        $ git clone https://github.com/geegatomar/Official-VNE-SDN-Major-Project.git
        ```
        
    - Run the mininet code  </br>
        
        The 2 main executable files are `main.py` and `runner.py`. </br>
          - `main.py`: Used to run one experiment at a time. It reads configurations from the `configurations.json` file. </br>
          - `runner.py`: Used to run multiple experiments (over multiple iterations, for different number of VNRs, and for various VNE algorithms) at a time. It internally makes calls to the `main.py` depending on the configurations mentioned in `configurations.json`.
          </br>
        ``` 
        $ sudo python3 vne/runner.py 
        ```
        ``` 
        $ sudo python3 vne/main.py 
        ```
        ``` 
        $ sudo python3 vne/main.py -s 5 -a first-fit-algorithm -n 10
        ```

 - Optional installations: </br>
 If you wish to use RYU controller (instead of mininet's default ovs-controller), you will have to do additional installations.
     - Install [RYU controller](https://ryu.readthedocs.io/en/latest/getting_started.html)
     - Move/copy the ryu controller file `ryu_controller_vne.py` to the location where you installed RYU, into the directory `ryu/app/`
     - Start the ryu controller </br>
        ``` 
        $ ryu-manager ryu/app/ryu_controller_vne.py 
        ```
       You can modify this controller file to leverage RYU's features.


## Overview
The VNE emulator has the following main components:



- **Generate substrate network**: The substrate network is generated using *Mininet* which provides a virtual test bed and development environment for software-defined networks (SDN). It creates the substrate network following a spine-leaf topology, and does the IP addressing of all substrate hosts in the network. Flow table entries of all Openflow switches is also populated, thus establishing a deterministic path between every pair of hosts in the substrate network.

- **Generate VNRs**: Set/pool of VNRs is generated. The CPU and link bandwidth requirement limits can be specified in the configurations file, along with other parameters such as number of VNRs to generate. The list of VNRs can also be ranked/ordered before trying to serve/map them onto the substrate network.

- **VNE Algorithm**: Once the substrate network is ready, and you have the list of VNRs to serve, the VNE algorithms module loops over the list of VNRs trying to serve/map them one at a time. It currently supports multiple VNE algorithms such as first-fit, worst-fit, NORD, NRM, and AHP; and we have made it very easy to plug-in and integrate any other algorithm as well. The VNE algorithm *selects* the substrate resources (i.e. substrate hosts and links) for serving/mapping the given VNR, and passes the *selected substrate resources for mapping* to the next VNR mapping module.

- **VNR Mapping**: The actual mapping of VNR onto substrate network happens here. Internally this module handles IP addressing of the virtual hosts of VNR, flow table updations to support routing packets to virtual hosts, VLAN for isolation between VNRs, traffic control to restrict bandwidth of a virtual link mapped onto a substrate link, etc.

- **Tests**: For testing the emulator setup, and to test if each VNR is getting the allocated resource, we use network performance tools such as *iperf* for performing bandwidth tests. Reachability tests are performed using *ping*, where every virtual host shall be reachable to every other virtual host within the same VNR, but not reachable to any other host. CPU limit tests are also performed here to complete end-to-end testing of the VNE emulator.

</br>
</br>
<img src="https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/emulator_architecture_diagram.png?raw=true" width="85%">
</br>



## Project Modules
The project work is broadly divided into the following parts:
### Substrate topology generation
1. Spine leaf topology creation
2. IP addressing of nodes
3. Flow table entry population of OVSwitch
### Mapping VNRs on substrate network
1. VNE algorithm to *select* which substrate host to map the virtual host onto
2. The actual VNR *mapping* logic; IP addressing of virtual hosts, VLAN isolation, updating flow table entries, etc.
### Testing
1. Pings for connectivity within VNR hosts
2. Iperf for bandwidth links
3. Cpu limit tests

---

# Substrate Network

## Spine-Leaf Topology
Spine-Leaf Architecture is a two-layer, full-mesh topology composed of a leaf layer and a spine layer, with the leaf and spine switches. 

</br>
<img src="https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/spine-and-leaf-architecture-2.jpg?raw=true" width="75%">
</br>

The substrate network (i.e. physical network onto which Virtual Network Requests will be mapped) in our project follows a spine-leaf architecture, which is a common convention followed by modern day data centres. Although we have added an additional layer of switches, called the 'host switch layer' for each host. This is mainly for simplifying the implementation of virtual hosts' mapping; more on why we did this is in the sections below.

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
Since we want the path taken by any packet from one host to another host to be a *deterministic path*, we populate the flow table entries of every switch accordingly. The logic for population of flow entries for each set of switches (i.e. spine layer switches, leaf layer switches and host layer switches) is different because of the position of the switches in the network, and hence we discuss them separately as follows:

- **For spine layer switches**: For every packet that the spine switch gets, it sends it out downwards towards the leaf layer switch depending on the destination IP address of the packet. For example, if (in the above image), the switch s1_2 gets a packet destined for host h11 (having IP address '12.1.0.0'), then it will send the packet to switch s2_6 (having subnet '12.1.0.0/16') because the host h11 comes under the subnet of s2_6.

- **For leaf layer switches**: For every packet that the leaf switch gets, there could be 2 situations; either the packet shall travel upwards towards the spine layer switches, or downwards towards the host layer switches. 
    - ***Towards spine layer switches (upwards)***: We consider the larger of the src and dst subnets to find the spine layer switch to forward the packet. Reason for doing this (and not just basing the decision off of destination address) is because if we decide the spine layer switch only based on the destination address, then the request & reply packets will not follow the same route. For example, in the topology (sl=3, ll=2, hl=2), if h1 (10.0.0.0) wants to communicate with h6 (11.0.1.0), it will communicate via the switch s1_2 (because dst_ip is under 11 subnet). But when h6 sends reply to h1, then the dst_ip is considered of h1, which is under 10 subnet, and would now route via s1_1. Hence, to avoid this problem, we make the decision of selecting spine switch based on the larger of the two addresses. Hence, in this example packet between h1 (10.0.0.0) and h6 (11.0.1.0) will be travel via the spine switch s1_2 ('11 /8'), and not s1_1 ('10 /8'), because 11 > 10.
    - ***Towards host layer switches (downwards)***: This is a simple decision based on the destination address of the host, the packet is output on the respective output port of leaf switch accordingly. For example, if the spine switch s2_1 gets a packet for host h2 (10.0.1.0), it will send it out to the host switch sh2 (10.0.1/24).

- **For host layer switches**: For everypacket that the host layer switch gets, there could be 2 situations; either the packet is for that host under the subnet of that switch, or its not.
    - ***Towards host***: If the destination ip address corresponds to the address of the host attached to the host layer switch, then it is directly delivered to it (the only host attached to it).
    - ***Towards leaf layer switches***: If the destination ip address is anything but the above case, then it is sent upwards to the only leaf layer switch that the host is attached to.

### Example
1. Packet needs to be sent from h1 (10.0.0.0) to h10 (12.0.1.0). The path followed by the packet will be:
    - For **h1 to h10** (request): &nbsp; h1  &rarr;  sh1  &rarr;  s2_1  &rarr;  s1_3  &rarr;  s2_5  &rarr;  sh10  &rarr;  h10
    - For **h10 to h1** (reply): &nbsp; &nbsp; h10 &rarr;  sh10  &rarr;  s2_5  &rarr;  s1_3  &rarr;  s2_1  &rarr;  sh1 &rarr;  h1
    </br> Note that the path followed by packet for request and reply must go through the same set of switches (and hence the same set of substrate links).

2. Packet needs to be sent from h5 (11.0.0.0) to h6 (11.0.1.0). The path followed by the packet will be:
    - For **h5 to h6** (request): &nbsp; h5  &rarr;  sh5  &rarr;  s2_3  &rarr;  sh6  &rarr;  h6
    - For **h6 to h5** (reply): &nbsp; &nbsp; h6  &rarr;  sh6  &rarr;  s2_3  &rarr;  sh5  &rarr;  h5
    </br> Note that in this example the packet did not have to go till the spine layer at all (unlike in the previous example), because both hosts belong to same /16 subnet and hence were routed below the leaf-layer switches itself.
</br>

![flow-table-example-diagram](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/flow_table_example.png?raw=true)

---

# VNE Algorithm

- So far we have established the entire substrate (physical) network in mininet. The pool of VNRs (virtual network requests) is also generated in our VNE emulator, and VNRs can also be ranked/ordered to decide in which order to try mapping them onto the substrate network. The next task is hence to find mappings for each of the VNRs. 

- The ***VNE algorithm module*** does this *selection* of substrate resources for mapping of each VNR onto the substrate nework. Note that this module applies specified algorithm to select the substrate resources, but does not do the actual mapping yet. The actual mapping of VNR's virtual hosts onto the substrate network is handled in the next module (VNR mapping module).

- ***Additional data structures*** are maintained to model the network/graph, and keep track of the remaining bandwidths between links after VNRs are being mapped. When a virtual link is mapped onto the substrate network's link, the bandwidth of the substrate network is not directly reduced. Instead, this information is tracked using these additional graph data structures (Reason: If you directly reduce the bandwidth of the actual links on the mininet network, then later when you test with iperf, you'd not get the expected bandwidth because you've subtracted from that).
The exact paths (deterministic) between every pair of hosts is initially populated. More information can be found here:
https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/835fd8e4556d0622054f2b6b4738af64d8e659b4/vne/substrate.py#L195
When the VNE algorithm runs to select set of substrate hosts (for mapping the virtual hosts of the VNR), it needs to check for CPU limits and bandwidth limits, and these data structures which we maintain are useful in doing all these checks.
</br>

### Implemented algorithms in code
We have currently implemented 5 VNE algorithms as part of the emulator. The code is extremely modular and allows *easy plug-in and integration of any VNE algorithms* in the future. Each of the currently implemented VNE algorithm typically first *ranks* the substrate hosts (to decide the order in which mappings shall be tried) and similarly ranks the virtual hosts of the VNRs. Then it tries an *embedding strategy* for mapping virtual hosts onto substrate hosts (i.e. node embedding), for example greedy VNE embedding, based on the ranked/order list of substrate hosts and virtual hosts. Note that in our emulator since we have *deterministic paths* between every pair of hosts, there is essentially no separate link embedding (and mainly only node embedding that needs to be performed). The 5 VNE algorithms implemented in our code are as follows:
- **First Fit**: Ranks substrate hosts & virtual hosts in the order in which they are provided. Performs greedy vne embedding of virtual hosts onto substrate hosts.
- **Worst Fit**: Ranks substrate hosts in descending order of their remaining CPU capacity. Ranks virtual hosts in the order in which they are provided. Performs greedy vne embedding of virtual hosts onto substrate hosts.
- **NORD**: Handles ranking of substrate & virtual hosts using NORD algorithm which follows the TOPSIS ranking strategy. Performs greedy vne embedding of virtual hosts onto substrate hosts.
- **NRM**: Handles ranking of substrate & virtual hosts using NRM algorithm; followed by greedy vne embedding of virtual hosts onto substrate hosts.
- **AHP**: Handles ranking of substrate & virtual hosts using Rematch AHP algorithm; followed by greedy vne embedding of virtual hosts onto substrate hosts.
</br>
  
### To integrate your VNE algorithm in our emulator
This section explains how we integrated the [NORD algorithm](https://www.sciencedirect.com/science/article/abs/pii/S1389128623001068) in our emulator. The same set of steps can be followed to integrate any other VNE algorithm.
- The `vne_algorithm()` function in the module which selects which vne algorithm function to call based on the algorithm specified in the configuration file. https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/f79e856f7e53ee9d341541209b78d89866ed1b6b/vne/vne_algorithms.py#L176
- The `_nord_algorithm()` function which is called by the previous function. https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/f79e856f7e53ee9d341541209b78d89866ed1b6b/vne/vne_algorithms.py#L41
- A folder called `nord` is added in code which has all the NORD algorithm logic, and we add an additional `nord_support.py` file to handle conversion of data structures in our code convention to NORD's code convention. The main function in this file is `get_ranked_hosts()` which returns the ordered list of ranked substrate hosts, and ranked virtual hosts (in our code convention). https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/f79e856f7e53ee9d341541209b78d89866ed1b6b/vne/nord/nord_support.py#L129
- The `ranked_virtual_hosts` and `ranked_substrate_hosts` are then fed into the `_greedy_vne_embedding()` function which returns the final set of selected substrate resources for mapping this VNR. https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/f79e856f7e53ee9d341541209b78d89866ed1b6b/vne/vne_algorithms.py#L63
- The `vne_algorithm()` function is expected to return `cpu requirements for vnr mapping` and `bandwidth requirement for vnr mapping` in our code's convention, which will further be passed to the next module (VNR mapping) that will perform the actual mapping of VNR on substrate network. An example of values returned from the vne algorithm function is:
     ```
     cpu_reqs_for_vnr_mapping:  [('h15', 8), ('h28', 3), ('h6', 5), ('h11', 2), ('h42', 1)]
     bw_reqs_for_vnr_mapping:  [('h6', 'h42', 2), ('h6', 'h15', 4), ('h6', 'h11', 1), ('h42', 'h28', 4), ('h15', 'h28', 4), ('h28', 'h11', 4)]
     ```

---

# VNR Mapping
Once the 'VNE algorithms' module has selected the substrate resources (hosts and links) for mapping the VNR, the *actual mapping* of the VNR onto the substrate network is carried out by this module. We explored multiple options for mapping virtual nodes onto physical nodes such as encapsulation, VXLAN, VLAN, etc. but ultimately chose to go ahead with the VLAN approach to provide isolation between VNRs.


## IP addressing of virtual hosts
Every virtual host is given the next available IP address in the subnet of the 'host layer switch' connected to the host that it is being mapped on. For example, if a virtual host 'vh1' has to be mapped onto the substrate host 'h3' ('10.1.0.0'), then it is given the IP address of '10.1.0.1'. And the next virtual host 'vh2' to be mapped on the same substrate host 'h3' is given the next available IP address of '10.1.0.2'. The next available IP address is obtained by incrementing the values of the fourth octet in the dot-decimal notation of the IP addresses provided.
Logically, it means that they all are under the host with IP subnet of '10.1.0 /24', which is basically the subnet of the corresponding '*host layer switch*', here 'sh3'. Hence, we are simplifying the process of IP addressing by assigning virtual hosts addresses *as if they belong to the substrate network*. (This saves us the hassle of doing additional mappings and encapsulation, simplying the implementation of mapping virtual host onto substrate host). 

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
Once the IP addressing of virtual hosts was figured out, the connectivity amongst every pair of host (all substrate and virtual hosts) is inherently present because of how the flow table entries were initially populated. This meant that a host of one VNR is able to communicate with a host of another VNR; and this behavior is undesirable. This is why we added ***VLAN*** logic to provide ***isolation between VNRs***, i.e. hosts of one VNR shall be able to communicate with each other, but not communicate with any other host on the network. 

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
# Tests

### Iperf: Bandwidth limit tests
Iperf is a commonly used open-source network performance testing tool. It allows you to measure the maximum achievable bandwidth between two endpoints (usually a client and a server) by generating network traffic.
https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/1016618c958c00aba1cb7bca5c11d46dd133ce07/vne/tests.py#L38

We run iperf tests between every pair of host and compare the 'expected bandwidth' and 'obtained/actual bandwidth' and pass the iperf test if their difference is under a certain defined threshold; else fail the iperf test.


### Ping: Reachability tests
Ping is a utility used to test the reachability and round-trip time (RTT) of a network host or IP address. It is commonly used to troubleshoot network connectivity issues and measure the response time between two devices on a network.
https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/1016618c958c00aba1cb7bca5c11d46dd133ce07/vne/tests.py#L16
Every host in one VNR shall be reachable to every other host in the same VNR, and not reachable to any other VNR's hosts.


### CRB/CPU limit tests
We are making use of Mininet's runCpuLimitTest API to perform CPU tests; more info on which can be found here: http://mininet.org/api/classmininet_1_1net_1_1Mininet.html#acf267a82240ede837a66326b8d633fdf
Similar to how iperf tests were performed, this also compares the 'expected cpu capacity' with the 'actual/obtained cpu capacity', and if they are close by (within a certain threshold), then the tests passes.
https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/1016618c958c00aba1cb7bca5c11d46dd133ce07/vne/tests.py#L66

---



# Expected Results

Shows how many VNRs were successfully mapped onto the substrate network (by using the selected VNE algorithm)

![results](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/results.png?raw=true)
In this example, mapping was found for 3 out of the 4 VNRs.

### CPU tests passing
![results](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/results_cpu.png?raw=true)

### Iperf tests passing
<img src="https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/results_iperf.png?raw=true" width="70%">



### Ping tests passing
<img src="https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/results_ping.png?raw=true" width="90%">


### Additional ping tests
To demonstrate that VLANs are able to provide isolation between VNRs, we can run `pingall` between every pair of host in the network. 
- As expected, all the substrate hosts are able to reach every other substrate host (h1, h2, h3, ..., h18), and no other virtual hosts. 
- VNR1 has 4 virtual hosts (vnr1_vh1, vnr1_vh2, vnr1_vh3, vnr1_vh4); and as expected each virtual host of VNR1 is able to reach every other virtual host of VNR1, but not able to reach any other host (i.e. any substrate host or any host of VNR2 or VNR3).
- Similar results can be observed for VNR2 and VNR3. Hence, isolation is achieved using VLANs in our emulator's network.


<img src="https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/images/vlan_isolation_ping.png?raw=true" width="90%">
('X' denotes that there is no reachability and ping failed for that host pair)

---

# Additional Information

### configurations.json
All the configurations with respect to generation of substrate network (number of hosts in substrate network, CPU limits for hosts, bandwidth limits for links of substrate network, etc.), generation of VNRs (number of VNRs, cpu & bandwidth requirements of VNRs, etc.), which VNE algorithm to use, etc. can all be specified in this [configurations.json](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/vne/configurations.json) file. When you execute the command `sudo python3 main.py` file to run the code, it will read from this configuration file.

### runner.py
The [main.py](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/vne/main.py) allows us to run one experiment at a time (based on the specified configurations). We extended this functionality to run multiple experiments over multiple iterations, for different number of VNRs and using different VNE algorithms at a time using the [runner.py](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/vne/runner.py) file. 
Note that to run this file, you must make sure to specify all the configurations in the [configurations.json](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/vne/configurations.json) file; especially these 3 configurations which are specific to this file (which main.py doesn't look at):
```
Number of iterations to run for:   "iterations": 5,
List of VNE algorithms to run on:  "vne_algorithms": ["first-fit-algorithm", "worst-fit-algorithm", "nord-algorithm"],
List of number of VNRs to run for: "num_vnrs_list": [25, 50, 100]
```

### Results.xlsx
The results from multiple experiments run in [runner.py](https://github.com/geegatomar/Official-VNE-SDN-Major-Project/blob/master/vne/runner.py) are captured in this excel file. The major columns captured are as follows:
- **seed**: The seed value used for pseudo-random generation of the network topology and VNRs.
- **algorithm**: The algorithm used for virtual network embedding.
- **revenue**: Sum of all demanded resources (cpu & bw) of VNRs.
- **total_cost**: Sum of all spent resources (cpu & bw) for embedding VNRs.
- **revenuetocostratio**: Ratio of revenue / total_cost.
- **accepted**: Number of accepted VNR requests.
- **total_request**: Total number of VNR requests.
- **embeddingratio**: Ratio of accepted / total_request.
- **pre_resource**: Pre-resource is the sum of all resources (cpu & bw) before embedding.
- **post_resource**: Post-resource is the sum of all resources (cpu & bw) after embedding.
- **consumed**: Consumed resources = post_resource - pre_resource.
- **No_of_Links_used**: Number of substrate links onto which any vnr's links are mapped, i.e. number of substrate links used for any mapping.
- **No_of_Nodes_used**: Number of substrate nodes onto which any vnr's hosts are mapped, i.e. number of substrate nodes used for any mapping.
- **total_nodes**: Total number of hosts in the substrate network.
- **total_links**: Total number of links in the substrate network.
- **total_execution_time**: Total execution time (in seconds) to execute the entire VNE embedding code for this single experiment.
- **avg_bandwidth_utilization**: Average Bandwidth Utilization is defined as the average bandwidth utilization of the used links in the substrate network. It can be calculated by first calculating the bandwidth utilization of each link that is being used, and next taking the average of all these values.
- **avg_crb_utilization**: Similar to average bandwidth utilization, average CRB utilization is defined as the average CRB utilization of used nodes in the substrate network. This can be calculated by first calculating the CRB utilization of each node that is being used, and next taking the average of all these values.
- **avg_link_utilization**: Average link utilization is defined as the total number of substrate links utilized during the embedding of the VNRs divided by the total number of links in the substrate network.
- **avg_node_utilization**: Average node utilization is defined as the total number of substrate nodes utilized during the embedding of the VNRs divided by the total number of nodes in the substrate network.

### Why deterministic path is fixed at the beginning?
As mentioned previously, we have *deterministic* paths between every pair of hosts in the substrate network, and that's why the flow entries for these paths are populated in the flow tables of the OF switches at the beginning itself. This means that essentially we only need to solve the problem of 'node embedding', since 'link embedding' problem doesn't exist in our scenario (since the path is already fixed between every pair of hosts in the beginning itself).
The reason for making path between every host pair deterministic is that, if suppose we had not made the paths deterministic, then there would be multiple paths (say paths P1, P2, P3) between two hosts. And suppose that the link embedding selected a particular path P1 between the two substrate hosts h1 and h2, when it mapped vh1 and vh2 onto the respective substrate hosts. Resources were allocated for this VNR's virtual links on the substrate network on path P1. Later, when we would run iperf to test if the VNR is getting the bandwidth it requested, if the path is not determinisitc, then at that moment the router (which would run some dynamic routing protocol) might select a different path P2. This causes an issue because we had allocated/saved resources for this VNR on path P1, but while testing it chose path P2 and hence causing link bandwidth tests to fail. That's why we went ahead with static routing to establish single deterministic path between every pair of hosts, so that the path selected while mapping the VNR, and the path selected while finally testing the VNR's links' bandwidth performance shall remain the same.
