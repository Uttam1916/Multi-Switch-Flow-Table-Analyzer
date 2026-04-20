"""
Flow Table Analyzer for POX
Analyzes flow tables dynamically, handles basic L2 learning, and enforces a firewall rule.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.recoco import Timer
from pox.lib.packet.ipv4 import ipv4

log = core.getLogger()

class FlowAnalyzer(object):
    """
    Handles L2 learning and Firewall capabilities
    """
    def __init__(self, connection):
        self.connection = connection
        connection.addListeners(self)
        self.mac_to_port = {}

    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            log.warning("Ignoring incomplete packet")
            return

        packet_in = event.ofp
        self.mac_to_port[packet.src] = event.port

        # Firewall Logic: Block ICMP or IP traffic between h3 (10.0.0.3) and h4 (10.0.0.4)
        if packet.type == packet.IP_TYPE:
            ip_packet = packet.payload
            if isinstance(ip_packet, ipv4):
                srcip = str(ip_packet.srcip)
                dstip = str(ip_packet.dstip)

                if (srcip == "10.0.0.3" and dstip == "10.0.0.4") or (srcip == "10.0.0.4" and dstip == "10.0.0.3"):
                    # Install drop rule (no actions = drop)
                    msg = of.ofp_flow_mod()
                    msg.match = of.ofp_match.from_packet(packet)
                    msg.idle_timeout = 30
                    msg.hard_timeout = 60
                    msg.buffer_id = packet_in.buffer_id
                    self.connection.send(msg)
                    log.info("Firewall: Dropped packet from %s to %s", srcip, dstip)
                    return

        # L2 Learning Logic
        if packet.dst in self.mac_to_port:
            port = self.mac_to_port[packet.dst]
            
            # Install flow rule
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet)
            msg.idle_timeout = 15
            msg.hard_timeout = 60
            msg.actions.append(of.ofp_action_output(port=port))
            msg.buffer_id = packet_in.buffer_id
            self.connection.send(msg)
            log.debug("Installed flow rule for %s -> %s", packet.src, packet.dst)
        else:
            # Flood the packet
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            msg.data = event.ofp
            msg.in_port = event.port
            self.connection.send(msg)

class FlowStatsAnalyzer(object):
    """
    Periodically polls switches for flow statistics and identifies active vs unused rules.
    """
    def __init__(self):
        core.openflow.addListeners(self)
        self.rule_packet_counts = {} # nested dict: {dpid: {match_str: packet_count}}
        Timer(5, self._request_stats, recurring=True)
        
    def _request_stats(self):
        for connection in core.openflow._connections.values():
            connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))
            
    def _handle_FlowStatsReceived(self, event):
        stats = event.stats
        dpid = event.connection.dpid
        
        if dpid not in self.rule_packet_counts:
            self.rule_packet_counts[dpid] = {}
            
        print("\n" + "="*110)
        print(" Switch DPID: %s " % dpid_to_str(dpid))
        print("="*110)
        
        # Header
        header_format = "{:<55} | {:<15} | {:<10} | {:<10} | {:<10}"
        print(header_format.format("Match Criteria", "Actions", "Packets", "Bytes", "Status"))
        print("-" * 110)
        
        current_rules = {}
        for f in stats:
            match_str = str(f.match)
            if len(match_str) > 52:
                match_str = match_str[:52] + "..."
                
            action_str = ",".join([str(a) for a in f.actions])
            if not action_str:
                action_str = "DROP"
            if len(action_str) > 13:
                action_str = action_str[:13] + ".."
                
            packet_count = f.packet_count
            byte_count = f.byte_count
            
            # Determine Active vs Unused
            status = "Active"
            full_match_key = str(f.match)
            if full_match_key in self.rule_packet_counts[dpid]:
                if self.rule_packet_counts[dpid][full_match_key] == packet_count:
                    status = "Unused"
            
            if packet_count == 0:
                status = "Unused"
                
            current_rules[full_match_key] = packet_count
            
            print(header_format.format(match_str, action_str, str(packet_count), str(byte_count), status))
            
        print("="*110 + "\n")
        
        # Update history for next polling interval
        self.rule_packet_counts[dpid] = current_rules

def launch():
    def start_switch(event):
        log.info("Starting Flow Analyzer on Switch %s", dpid_to_str(event.connection.dpid))
        FlowAnalyzer(event.connection)
        
    core.openflow.addListenerByName("ConnectionUp", start_switch)
    core.registerNew(FlowStatsAnalyzer)
    log.info("Flow Table Analyzer module loaded successfully.")
