# Virtual Network Embedding (VNE) emulation using mininet


## Getting started
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


## Project modules
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

