# VNE Package
 The Virtual Network Embedding (VNE) packge consisting of the following modules:
 
 ## main.py
 The main executable in the package.
 
 ## configurations.json
 User specified *configurations* are specified here. These configurations decide
 the number of nodes in substrate graph, number of VNRs, the cpu/bw requirements
 of those generated VNRs, etc.
 

 ## substrate.py
 Substrate module consists of methods concerning creation of the substrate (physical) network.
  - The construction of the spine-leaf topology in mininet
  - IP addressing of the mininet nodes
  - Populating flow table entries of OVSwitch
  - Populating the graph data structures (path between every pair of hosts) which is used by the VNE mapping algorithms.
  
 ## vnr_mapping.py
 The Virtual Network Request (VNR) mapping logic.
  - Map VNR's virtual hosts onto the substrate network hosts 
  - Add a virtual host onto selected substrate host
      - IP addressing of virtual host
      - Every VNR is associated with separate VLAN ID to ensure isolation
      - Traffic control using Hierarchical Token Bucket qdisc is done to restrict bandwidth limits of links

 ## vne_algorithms.py
 The Virtual Network Embedding algorithms which decide onto which substrate hosts the VNR's virtual hosts shall be mapped. The algorithm shall ensure to satisfy the cpu and bandwidth requirements of all the virtual hosts and links of the VNR.
 Currently, there is only the `random algorithm` implemented. More algorithms can easily be plugged in here.
 
 ## gbl.py
 Consisting of global variables which is used/modified by code across different modules.
 
 ## helpers.py
 Helper functions commonly used by other files/modules.
 
