# ryu_flow_analyzer.py
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4
from ryu.lib import hub

class FlowAnalyzer(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FlowAnalyzer, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.rule_packet_counts = {}  # {dpid: {match_str: count}}
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.datapaths[datapath.id] = datapath
        self.mac_to_port.setdefault(datapath.id, {})

        # Default miss rule (flood)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions, idle_timeout=0, hard_timeout=0)
        self.logger.info("Connected to switch DPID %s", datapath.id)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=15, hard_timeout=60):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst, idle_timeout=idle_timeout,
                                    hard_timeout=hard_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst,
                                    idle_timeout=idle_timeout, hard_timeout=hard_timeout)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        # Firewall Policy: Drop traffic between h3 (10.0.0.3) and h4 (10.0.0.4)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            srcip = ip_pkt.src
            dstip = ip_pkt.dst
            if (srcip == "10.0.0.3" and dstip == "10.0.0.4") or (srcip == "10.0.0.4" and dstip == "10.0.0.3"):
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=srcip, ipv4_dst=dstip)
                # Empty actions = DROP
                self.add_flow(datapath, 10, match, [], idle_timeout=30, hard_timeout=60)
                self.logger.info("Firewall: Dropped packet %s -> %s", srcip, dstip)
                return

        # L2 Learning
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(5)

    def _request_stats(self, datapath):
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        
        if dpid not in self.rule_packet_counts:
            self.rule_packet_counts[dpid] = {}
            
        print("\n" + "="*110)
        print(" Switch DPID: %s " % dpid)
        print("="*110)
        
        header_format = "{:<55} | {:<15} | {:<10} | {:<10} | {:<10}"
        print(header_format.format("Match Criteria", "Actions", "Packets", "Bytes", "Status"))
        print("-" * 110)
        
        current_rules = {}
        for stat in sorted([flow for flow in body if flow.priority > 0], key=lambda flow: flow.priority):
            match_str = str(stat.match)
            if len(match_str) > 52:
                match_str = match_str[:52] + "..."
                
            actions = stat.instructions[0].actions if stat.instructions else []
            action_str = ",".join([str(a.type) + ":" + str(getattr(a, 'port', '')) for a in actions])
            if not action_str:
                action_str = "DROP"
            if len(action_str) > 13:
                action_str = action_str[:13] + ".."
                
            packet_count = stat.packet_count
            byte_count = stat.byte_count
            
            status = "Active"
            full_match_key = str(stat.match)
            if full_match_key in self.rule_packet_counts[dpid]:
                if self.rule_packet_counts[dpid][full_match_key] == packet_count:
                    status = "Unused"
            
            if packet_count == 0:
                status = "Unused"
                
            current_rules[full_match_key] = packet_count
            
            print(header_format.format(match_str, action_str, str(packet_count), str(byte_count), status))
            
        print("="*110 + "\n")
        self.rule_packet_counts[dpid] = current_rules
