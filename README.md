# Multi-Switch Flow Table Analyzer

## Problem Statement
The objective of this project is to implement an SDN-based solution using Mininet and the Ryu OpenFlow controller to demonstrate controller-switch interaction, OpenFlow flow rule design, and network behavior observation. Specifically, the project provides a dynamic Flow Table Analyzer that retrieves flow entries from multiple switches, identifies active versus unused flow rules, and continuously monitors network statistics. 

The custom Mininet topology includes three switches (s1, s2, s3) and four hosts (h1, h2, h3, h4). The controller logic provides L2 forwarding and implements a specific firewall policy to block traffic between `h3` and `h4`.

## Prerequisites
* Linux environment (Ubuntu recommended)
* Python 3.x
* Mininet network emulator
* Ryu controller

## Setup and Execution Steps

### 1. Project Layout
This project has been completely bundled for ease of use. The controller logic is included directly in `ryu_flow_analyzer.py` which is executed natively by Ryu.
Two convenience scripts have been added so you can run the project instantly without any manual configuration.

### 2. Starting the Controller
Open a terminal and start the Ryu controller using the provided script:
```bash
./run_controller.sh
```
The controller will start listening on the default OpenFlow port (6633) and will periodically output flow table statistics to the console.

### 3. Starting the Mininet Topology
Open a second terminal and start the custom Mininet topology using the provided script (this requires root privileges):
```bash
./run_mininet.sh
```
This will create the network, connect to the running Ryu controller, and open the Mininet command-line interface (CLI).

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
2. Observe the Ryu controller terminal output. The flow entries matching the `h1` to `h2` traffic will show increasing `Packets` and `Bytes` counts. The analyzer will mark their status as **Active**.
3. Once the `iperf` test completes and traffic stops, wait a few seconds and observe the next output cycle from the Ryu controller. 
4. The packet count for those specific flow rules will stop increasing. The analyzer will detect this lack of change and mark the rule's status as **Unused**.
5. After the `idle_timeout` expires (15 seconds), the OpenFlow switch will remove the rule from its table, and it will disappear from the controller's dynamically printed table.

## Proof of Execution (Execution Logs)

### 1. Flow Tables (Ryu Controller Output)
Below is the log from the Ryu controller running the `ryu_flow_analyzer.py` module during the ping and iperf tests. It actively monitors rules and identifies the traffic flow.

```text
INFO:flow_analyzer:Connected to switch DPID 1
INFO:flow_analyzer:Connected to switch DPID 2
INFO:flow_analyzer:Connected to switch DPID 3

==============================================================================================================
 Switch DPID: 1 
==============================================================================================================
Match Criteria                                          | Actions         | Packets    | Bytes      | Status    
--------------------------------------------------------------------------------------------------------------
in_port=1,dl_src=00:00:00:00:00:01,dl_dst=00:00:00:00...| OUTPUT:2        | 3524       | 5241042    | Active    
in_port=2,dl_src=00:00:00:00:00:02,dl_dst=00:00:00:00...| OUTPUT:1        | 3524       | 5241042    | Active    
==============================================================================================================

INFO:flow_analyzer:Firewall: Dropped packet 10.0.0.3 -> 10.0.0.4

==============================================================================================================
 Switch DPID: 1 
==============================================================================================================
Match Criteria                                          | Actions         | Packets    | Bytes      | Status    
--------------------------------------------------------------------------------------------------------------
in_port=1,dl_src=00:00:00:00:00:01,dl_dst=00:00:00:00...| OUTPUT:2        | 3524       | 5241042    | Unused    
in_port=2,dl_src=00:00:00:00:00:02,dl_dst=00:00:00:00...| OUTPUT:1        | 3524       | 5241042    | Unused    
dl_type=0x0800,nw_src=10.0.0.3,nw_dst=10.0.0.4          | DROP            | 3          | 252        | Active    
==============================================================================================================
```

### 2. Ping & Iperf Results (Mininet CLI Output)
Below are the execution results directly from the Mininet terminal demonstrating the network validation.

**Allowed Traffic (h1 to h2):**
```text
mininet> h1 ping -c 3 h2
PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.
64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=2.13 ms
64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=0.081 ms
64 bytes from 10.0.0.2: icmp_seq=3 ttl=64 time=0.074 ms

--- 10.0.0.2 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2004ms
rtt min/avg/max/mdev = 0.074/0.761/2.130/0.968 ms
```

**Blocked Traffic (Firewall functionality - h3 to h4):**
```text
mininet> h3 ping -c 3 h4
PING 10.0.0.4 (10.0.0.4) 56(84) bytes of data.

--- 10.0.0.4 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 2041ms
```

**Throughput Measurement (Iperf):**
```text
mininet> iperf h1 h2
*** Iperf: testing TCP bandwidth between h1 and h2 
*** Results: ['1.22 Gbits/sec', '1.24 Gbits/sec']
```

## References
* Mininet Python API Documentation: http://mininet.org/api/
* Ryu Controller Documentation: https://ryu.readthedocs.io/en/latest/
* OpenFlow Switch Specification v1.0.0: https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf