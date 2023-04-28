# VNE Package
 The Virtual Network Embedding (VNE) packge consisting of the following modules:
 
 ## main.py
 The main executable in the package. It runs one experiment at a time. 
  ``` 
  $ sudo python3 vne/main.py 
  ```
  Command line flags can also be specified to override the configurations in configurations.json.
  - `-s`: Seed value for the pseudo-random number generator.
  - `-a`: VNE Algorithm to select. Can be 'first-fit-algorithm', 'worst-fit-algorithm', or any other algorithm that you want to plug-in and provide support for.
  - `-n`: Number of VNRs to generate.
  ``` 
  $ sudo python3 vne/main.py -s 5 -a first-fit-algorithm -n 10
  ```
 
 ## runner.py
 The other executable in the package. It runs multiple experiments (over multiple iterations, for different number of VNRs, and for various VNE algorithms) at a time. You must specify the following in the configurations.json file to leverage this file's functionality:
 - Number of iterations
 - List of VNE algorithms
 - List of number of VNRs               
 Example:
 { "iterations": 3,
 "vne_algorithms": ["first-fit-algorithm", "worst-fit-algorithm"],
 "num_vnrs_list": [5, 10, 15] }
  ``` 
  $ sudo python3 vne/runner.py 
  ```
  The results/summary/output of all the run experiments will be obtained in the `Results.xlsx` excel sheet which is generated as a result of running this file.
  
 
 ## configurations.json
 User can specify all *configurations* here. These configurations decide the number of nodes in substrate graph, number of VNRs, the cpu/bw requirements
 of those generated VNRs will be in which range of randomly generated values (i.e. min and max values for range), etc.
 

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
 Currently, 'first-fit-algorith' and 'worst-fit-algorithm' are implemented in code. More algorithms can easily be plugged in here in this module.
 
 ## gbl.py
 Consisting of global variables which is used/modified by code across different modules.
 
 ## helpers.py
 Helper functions commonly used by other files/modules.
 
