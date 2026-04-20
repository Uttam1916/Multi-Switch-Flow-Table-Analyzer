#!/usr/bin/env python

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

def create_topology():
    """Create a custom multi-switch topology for Flow Table Analyzer"""
    
    net = Mininet(controller=RemoteController, switch=OVSSwitch, link=TCLink)
    
    info('*** Adding Controller ***\n')
    # Use default port 6633 which POX typically uses
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    info('*** Adding Switches ***\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow10')
    s2 = net.addSwitch('s2', protocols='OpenFlow10')
    s3 = net.addSwitch('s3', protocols='OpenFlow10')
    
    info('*** Adding Hosts ***\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')
    
    info('*** Creating Links ***\n')
    # Switch to Switch links
    net.addLink(s1, s2, bw=100)
    net.addLink(s2, s3, bw=100)
    
    # Host to Switch links
    net.addLink(h1, s1, bw=100)
    net.addLink(h3, s1, bw=100)
    net.addLink(h4, s3, bw=100)
    net.addLink(h2, s3, bw=100)
    
    info('*** Starting Network ***\n')
    net.start()
    
    info('*** Running CLI ***\n')
    CLI(net)
    
    info('*** Stopping Network ***\n')
    net.stop()

if __name__ == '__main__':
    # Set log level to info to see mininet output
    setLogLevel('info')
    create_topology()
