# Multi-Switch Flow Table Analyzer

## Problem Statement
The objective of this project is to implement an SDN-based solution using Mininet and the POX OpenFlow controller to demonstrate controller-switch interaction, OpenFlow flow rule design, and network behavior observation. Specifically, the project provides a dynamic Flow Table Analyzer that retrieves flow entries from multiple switches, identifies active versus unused flow rules, and continuously monitors network statistics. 

The custom Mininet topology includes three switches (s1, s2, s3) and four hosts (h1, h2, h3, h4). The controller logic provides L2 forwarding and implements a specific firewall policy to block traffic between `h3` and `h4`.

## Prerequisites
* Linux environment (Ubuntu recommended)
* Python 2.7 or Python 3.x
* Mininet network emulator
* POX controller

## Setup and Execution Steps

### 1. Preparing the POX Controller
The logic for the flow analyzer is contained in `flow_analyzer.py`. To run this module, it should be placed in the `ext/` directory of your POX installation, or you can specify the path to POX directly.

Assuming POX is cloned into your home directory (`~/pox`):
```bash
cp flow_analyzer.py ~/pox/ext/
```

### 2. Starting the Controller
Open a terminal and start the POX controller with our custom module:
```bash
cd ~/pox
./pox.py flow_analyzer
```
The controller will start listening on the default OpenFlow port (6633) and will periodically output flow table statistics to the console.

### 3. Starting the Mininet Topology
Open a second terminal and start the custom Mininet topology. This must be run with root privileges:
```bash
sudo python topology.py
```
This will create the network, connect to the running POX controller, and open the Mininet command-line interface (CLI).

## Expected Output and Testing Scenarios

### Scenario 1: Allowed vs Blocked (Firewall Behavior)
The controller is designed to allow standard communication (e.g., between `h1` and `h2`) but explicitly block traffic between `h3` and `h4`.

1. **Allowed Traffic:**
   In the Mininet CLI, test connectivity between `h1` and `h2`:
   ```text
   mininet> h1 ping -c 3 h2
   ```
   *Result:* The ping will succeed. The controller terminal will display newly installed forwarding rules, and their status will show as "Active".

2. **Blocked Traffic:**
   In the Mininet CLI, test connectivity between `h3` and `h4`:
   ```text
   mininet> h3 ping -c 3 h4
   ```
   *Result:* The ping will fail (100% packet loss). The controller installs explicit drop rules (empty actions) when it detects traffic between 10.0.0.3 and 10.0.0.4.

### Scenario 2: Normal vs Failure (Flow Table Dynamics)
This scenario demonstrates how the controller identifies rules that are actively being used versus those that have become stale.

1. Generate continuous traffic using `iperf`:
   ```text
   mininet> iperf h1 h2
   ```
2. Observe the POX controller terminal output. The flow entries matching the `h1` to `h2` traffic will show increasing `Packets` and `Bytes` counts. The analyzer will mark their status as **Active**.
3. Once the `iperf` test completes and traffic stops, wait a few seconds and observe the next output cycle from the POX controller. 
4. The packet count for those specific flow rules will stop increasing. The analyzer will detect this lack of change and mark the rule's status as **Unused**.
5. After the `idle_timeout` expires (15 seconds), the OpenFlow switch will remove the rule from its table, and it will disappear from the controller's dynamically printed table.

## Proof of Execution
*(Students must add their screenshots or logs below this section prior to final submission)*

### 1. Flow Tables
*Insert screenshot of the POX controller terminal showing the formatted Flow Table Analyzer output. The screenshot should clearly display Match Criteria, Actions, Packets, Bytes, and Active/Unused status.*

### 2. Ping/Iperf Results
*Insert screenshot of the Mininet CLI demonstrating the Allowed (h1 ping h2) and Blocked (h3 ping h4) scenarios, as well as the iperf throughput test.*

## References
* Mininet Python API Documentation: http://mininet.org/api/
* POX Controller Documentation: https://noxrepo.github.io/pox-doc/html/
* OpenFlow Switch Specification v1.0.0: https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf