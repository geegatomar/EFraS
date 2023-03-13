# Virtual Network Embedding (VNE) emulation using mininet


## Getting Started
- Install [Mininet](http://mininet.org/download/)
- Install [RYU controller](https://ryu.readthedocs.io/en/latest/getting_started.html)
- Instructions to run:
    - Clone the repo </br>
        ```git clone https://github.com/geegatomar/Official-VNE-SDN-Major-Project.git```
    - Move/copy the ryu controller file `ryu_controller_vne.py` to the location where you installed RYU, into the directory `ryu/app/`
    - Start the ryu controller </br>
      ``` ryu-manager ryu/app/ryu_controller_vne.py ```
    - Run the mininet code </br>
      ` sudo python3 vne/main.py `
  

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

## IP addressing of virtual hosts
TODO: Explain why we have added an additional layer of host switches (i.e. *Modified spine-leaf topology*. Add draw io diagrams for this.

## VLAN isolation
TODO

## Traffic control (bandwidth restriction)
TODO

## CPU restriction
TODO

---


# VNE Algorithm

## Additional data structures maintained
TODO: Explain the populate_path_between_hosts function here, and why we need to maintain a 'graph' data structure and all.

## Random testing algorithm
TODO
