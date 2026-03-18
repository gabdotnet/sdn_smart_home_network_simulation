from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Deque
import time
import random
from enum import Enum
import hashlib
import copy


# tx_id initialization
next_tx_id: int = 1000


# categorical device lists
lan_devs = ["Laptop", "Phone"]
iot_devs = ["Camera", "Thermostat", "SmartLight"]
home_devs = ["HomeHub"]
guest_devs = ["GuestPhone"]
wan_devs = ["Internet"]


# port map dictionary
port_map = {
    "Laptop": "p1",
    "Phone": "p2",
    "Camera": "p3",
    "Thermostat": "p4",
    "SmartLight": "p5",
    "HomeHub": "p6",
    "GuestPhone": "p7",
    "Internet": "wan",
}


# enum class for tag as there are a finite number of tags
class Tag(str, Enum):
    BESTEFFORT = "BESTEFFORT"
    VOICE = "VOICE"
    VIDEO = "VIDEO"
    IOT = "IOT"
    TELEMETRY = "TELEMETRY"
    ALARM = "ALARM"


# enum class for action as there are only 3 options
class Action(str, Enum):
    FORWARD = "FORWARD"
    DROP = "DROP"
    TO_CONTROLLER = "TO_CONTROLLER"


# policy class for different policy reason to plug in for log purposes
class Policy(str, Enum):
    IOT = "IoT Isolation"
    GUEST = "Guest Isolation"
    QOS = "QoS"
    RATELIMIT = "Rate Limit"


# data class for Packet including all necessary fields
@dataclass
class Packet:
    src: str
    dst: str
    proto: str
    dport: int 
    tag: Tag
    ts: float


@dataclass
class Match:
    src: Optional[str] = None
    dst: Optional[str] = None
    proto: Optional[str] = None
    dport: Optional[int] = None
    tag: Optional[Tag] = None

    # matches function to check the match with the current packet
    def matches(self, packet: Packet) -> bool:

        # create lists of the fields so that you can iterate through them
        ml = [self.src, self.dst, self.proto, self.dport, self.tag]
        pl = [packet.src, packet.dst, packet.proto, packet.dport, packet.tag]

        # simultaneous iteration and None/equality check
        for mi, pi in zip(ml, pl):
            if mi is None:
                continue
            elif mi != pi:
                return False
        return True


# data class for FlowRule
@dataclass
class FlowRule:
    match: Match
    action: Action
    priority: int
    hit_count: int = 1
    policy: Optional[Policy] = None


@dataclass(frozen=True)
class IoTMessage:
    device: str
    msg_type: str          # "TELEMETRY" or "ALARM"
    payload: dict
    ts: float


@dataclass
class QoSRecord:
    send_ts: Optional[float] = None
    forward_ts: Optional[float] = None


class TrustState(str, Enum):
    TRUSTED = "TRUSTED"
    WATCH = "WATCH"
    BLOCKED = "BLOCKED"


@dataclass
class PacketProcessor:
    packet: Packet
    action: Optional[Action] = None
    controller_called: Optional[bool] = False
    priority: Optional[int] = 0
    policy: Optional[Policy] = None
    ts: Optional[QoSRecord] = None


@dataclass
class AuditRecord:
    tx_id: Optional[int] = None
    timestamp: Optional[float] = None
    src: Optional[str] = None
    dst: Optional[str] = None
    msg_type: Optional[Tag] = None
    action: Optional[Action] = None
    policy: Optional[Policy] = None


@dataclass
class Block:
    index: int
    timestamp: float
    tx_list: list[AuditRecord]
    prev_hash: Optional[str] = None
    cur_hash: Optional[str] = None



# IoT gen funcs

# Periodic sensing: produce a message every interval_s seconds. Returns None if it is not time to send.
def generate_periodic_telemetry(device: str, interval_s: float, make_payload: Callable[[], dict], now: float, last_sent: Dict[str, float],) -> Optional[IoTMessage]:
    last = last_sent.get(device, 0.0)
    if (now - last) < interval_s:
        return None
    last_sent[device] = now
    return IoTMessage(device=device, msg_type=Tag.TELEMETRY, payload=make_payload(), ts=now)

# Event-based sensing: with probability event_prob at each time step, generate a burst of ALARM messages (e.g., motion detected).
def generate_event_alarm_burst(device: str, event_prob: float, burst_size: int, make_payload: Callable[[int], dict], now: float) -> List[IoTMessage]:
    msgs: List[IoTMessage] = []
    if random.random() > event_prob:
        return msgs

    for i in range(burst_size):
        msgs.append(IoTMessage(device=device, msg_type=Tag.ALARM, payload=make_payload(i), ts=now))
    return msgs

# Convert IoTMessage into an SDN Packet. Assumes telemetry and alarms are sent from device -> HomeHub.
def iot_message_to_packet(msg: IoTMessage) -> "Packet":
    # Map message type to SDN traffic class/tag:
    tag = Tag.IOT if msg.msg_type == Tag.TELEMETRY else Tag.ALARM

    # Choose protocol/port to represent messaging (e.g., MQTT-like):
    proto = "TCP"
    dport = 1883 if msg.msg_type == Tag.TELEMETRY else 8883  # pretend alarms use a different port

    return Packet(src=msg.device, dst="HomeHub", proto=proto, dport=dport, tag=tag, ts=msg.ts)

# func to start up IoT generation
def run_iot_generation_demo(sw: "Switch", bc: "Blockchain", duration_s: float = 20.0, step_s: float = 0.2) -> None:
    start = time.time()
    last_sent: Dict[str, float] = {}

    # Payload generators
    def thermostat_payload() -> dict:
        return {"temp_c": round(18 + random.random() * 6, 1), "battery": round(0.6 + random.random() * 0.4, 2)}

    def camera_heartbeat_payload() -> dict:
        return {"status": "ok", "rssi": random.randint(-70, -40)}

    def camera_alarm_payload(i: int) -> dict:
        return {"event": "motion", "seq": i, "confidence": round(0.7 + random.random() * 0.3, 2)}

    while True:
        now = time.time()
        if (now - start) > duration_s:
            break

        # 1) Periodic telemetry
        t_msg = generate_periodic_telemetry(device="Thermostat", interval_s=5.0, make_payload=thermostat_payload, now=now, last_sent=last_sent)
        if t_msg:
            p = iot_message_to_packet(t_msg)
            print("[GEN] Thermostat TELEMETRY:", t_msg.payload)
            pp = sw.process_packet(p, now)
            bc.add_record(record_converter(pp)) # adds packetprocessor obj instance to bc's pending list
            # print_packet(sw, p)

        # 2) Camera heartbeat (periodic)
        c_msg = generate_periodic_telemetry(device="Camera", interval_s=2.0, make_payload=camera_heartbeat_payload, now=now, last_sent=last_sent)
        if c_msg:
            p = iot_message_to_packet(c_msg)
            print("[GEN] Camera HEARTBEAT:", c_msg.payload)
            pp = sw.process_packet(p, now)
            bc.add_record(record_converter(pp))
            # print_packet(sw, p)

        # 3) Camera motion alarms (event-based burst)
        alarm_msgs = generate_event_alarm_burst(
            device="Camera",
            event_prob=0.03,      # adjust to see more/less alarms,                 stress test: 0.2
            burst_size=3,         # burst size shows congestion/rate-limit effects  stress test: 12
            make_payload=camera_alarm_payload,
            now=now
        )
        for a in alarm_msgs:
            p = iot_message_to_packet(a)
            print("[GEN] Camera ALARM:", a.payload)
            pp = sw.process_packet(p, now)
            bc.add_record(record_converter(pp))
            # print_packet(sw, p)

        time.sleep(step_s)


    # hasher func which uses block attributes to create hash value


# creates hash values for block objs
def hasher(block: Block) -> str:
    hasher_str = f"{block.index}{block.timestamp}{block.tx_list}{block.prev_hash}"
    encoded_str = hasher_str.encode("utf-8")
    hash_obj = hashlib.sha256(encoded_str)
    hasher_result = hash_obj.hexdigest()

    return hasher_result


# blockchain class
class Blockchain:
    def __init__(self) -> None:
        self.tx_index: int = 0
        self.block_index: int = 0
        self.chain_list = []
        self.pending_list = []
        self.batch_size: int = 3 # per-block tx threshold
        self.genesis_block: Block

    # adds records to blockchain, checking whether batch_size reached
    def add_record(self, record: AuditRecord):
        self.tx_index += 1
        self.pending_list.append(record)
        # if list threshold reached, block created and sealed
        if len(self.pending_list) == self.batch_size:
            self.seal_block()
            

    # creates new block with full pending list, checks chain list for existing blocks,
    # computes previous and current hash values for blocks in chain list
    def seal_block(self):
        new_block = Block(index=self.block_index, timestamp=time.time(), tx_list=copy.deepcopy(self.pending_list))

        if len(self.chain_list) == 0:
            new_block.prev_hash = "0"
            self.genesis_block = new_block
        else:
            new_block.prev_hash = hasher(self.chain_list[-1])
        
        new_block.cur_hash = hasher(new_block)
        self.chain_list.append(new_block)
        self.pending_list.clear()
        self.block_index +=1
        
    # validate chain hash values by recalculating then comparing previous and current hashes of each block
    def validate_chain(self) -> str:
        result: str = "PASS"

        for index, block in enumerate(self.chain_list):
            if index == 0:
                if block.prev_hash != "0":
                    result = "FAIL"
                    break
                else:
                    result = "PASS"
            else:
                prev_hash_test = hasher(self.chain_list[index-1])
                if prev_hash_test != self.chain_list[index].prev_hash:
                    result = "FAIL"
                    break
                else:
                    result = "PASS"
            cur_hash_test = hasher(block)
            if cur_hash_test != self.chain_list[index].cur_hash:
                result = "FAIL"
                break
            else:
                result = "PASS"

        return result


# converts PacketProcessor obj to AuditRecord obj by linking attributes
def record_converter(packet_processor: PacketProcessor) -> AuditRecord:
    audit_record = AuditRecord()
    global next_tx_id

    audit_record.tx_id = next_tx_id
    audit_record.timestamp = time.time()
    audit_record.src = packet_processor.packet.src
    audit_record.dst = packet_processor.packet.dst
    audit_record.msg_type = packet_processor.packet.tag
    audit_record.action = packet_processor.action
    audit_record.policy = packet_processor.policy

    next_tx_id +=1

    return audit_record



# switch class
class Switch:
    def __init__(self) -> None:
        self.flow_table = []
        self.controller_i: Controller
        # self.packet_q = Deque()
        self.start = time.time()
        self.qos_recorder = []
        self.drop_count: int = 0
        self.pp_list = []
    
    # iterates flow table for matching rules, sends to controller if none match 
    def process_packet(self, packet: Packet, arrival: float) -> PacketProcessor:
        
        # create QoSRecord instance, link packet arrival time to instance, append to qos_recorder list
        qos_record = QoSRecord()
        qos_record.send_ts = arrival
        self.qos_recorder.append(qos_record)

        # create packet_processor obj instance for packet
        packet_processor = PacketProcessor(packet, ts=qos_record)
        self.pp_list.append(packet_processor)

        # list for matching rules to packet initialized, flow table looped to search for matches, matches added to list
        matching_rules = []

        for r in self.flow_table:
            if r.match.matches(packet) is True:
                matching_rules.append(r)
        

        # if matching rules list is empty, send to controller for decision, else proceed with processing
        if len(matching_rules) == 0:
            new_rule = self.controller_i.on_packet_in(packet, self)

            # updating packet_processor attribute after controller call
            packet_processor.controller_called = True
            packet_processor.action = new_rule.action
            packet_processor.priority = new_rule.priority
            packet_processor.policy = new_rule.policy

            if new_rule.action == Action.FORWARD:
                qos_record.forward_ts = time.time()
            else:
                self.drop_count +=1

            return packet_processor
        else:
            # highest_prio is a flow rule obj
            highest_prio = max(matching_rules, key=lambda rule: rule.priority)
            # final_port = port_map.get(packet.dst)
            
            # updating packet_processor attributes
            packet_processor.action = highest_prio.action
            packet_processor.priority = highest_prio.priority
            packet_processor.policy = highest_prio.policy

            highest_prio.hit_count += 1

            if highest_prio.action == Action.FORWARD:
                qos_record.forward_ts = time.time()
                return packet_processor
            elif highest_prio.action == Action.DROP:
                self.drop_count +=1
                return packet_processor

    # flow mod func to install new flow rules
    def flow_mod(self, flow_rule: FlowRule):
        self.flow_table.append(flow_rule)
        # return "FLOWMOD: flow_rule added to flow_table."


# controller class
class Controller:
    def __init__(self):
        self.history = []
        self.threshold: int = 5

    # policy check to align with policy requirements (rate limit handled in switch & QoS completed in on_packet_in() for post-check prio assignment)
    def policy_check(self, packet: Packet, flow_rule: FlowRule):

        self.history.append(packet)

        # iot isolation
        if packet.src in iot_devs:
            if packet.dst in iot_devs:
                flow_rule.policy = Policy.IOT
                return Action.DROP
            elif packet.dst in home_devs or packet.dst in lan_devs or packet.dst in wan_devs:
                flow_rule.policy = Policy.IOT
                return Action.FORWARD
        elif packet.src in lan_devs:
            flow_rule.policy = Policy.IOT
            return Action.FORWARD

        # guest isolation
        if packet.src in guest_devs:
            if packet.dst in wan_devs:
                flow_rule.policy = Policy.GUEST
                return Action.FORWARD
            else:
                flow_rule.policy = Policy.GUEST
                return Action.DROP
        
    
    # func called from switch to assess packets with no matches, flow mod called and new rule returned (flow rule obj)
    def on_packet_in(self, packet: Packet, switch: Switch):
        # new flow rule initialization
        match = Match(packet.src, packet.dst, packet.proto, packet.dport, packet.tag)
        new_rule = FlowRule(match, Action.DROP, 1) # default DROP/lowest prio (security)

        # link action returned from policy check to the new_rule obj
        new_rule.action = self.policy_check(packet, new_rule)

        # qos: 1 - 8 priority rating, 1 = lowest; 8 = highest
        if packet.tag == Tag.ALARM:
            new_rule.priority = 7
            new_rule.policy = Policy.QOS
        elif packet.tag == Tag.VOICE:
            new_rule.priority = 6
            new_rule.policy = Policy.QOS
        elif packet.tag == Tag.VIDEO:
            new_rule.priority = 5
            new_rule.policy = Policy.QOS
        elif packet.tag == Tag.BESTEFFORT:
            new_rule.priority = 3
        elif packet.tag == Tag.IOT:
            new_rule.priority = 2
        else:
            new_rule.priority = 1

        switch.flow_mod(new_rule)

        return new_rule

        # return f"ONPACKETIN: {new_rule.match.src}->{new_rule.match.dst}, {new_rule.action.value}, {new_rule.priority}, {new_rule.policy.value}"


# func to print packet processor logs
def print_packet(switch: Switch, packet: Packet):
    now = time.time()
    pp = switch.process_packet(packet, now)
    if pp.controller_called is False:
        print(f"PROCESSPACKET: decision= {pp.action.value}; rule= None, prio= {pp.priority}; reason= {pp.policy.value}; st= {pp.ts.send_ts}, ft= {pp.ts.forward_ts}")
    elif pp.controller_called is True:
        print(f"PROCESSPACKET: decision= {Action.TO_CONTROLLER.value}; rule= {pp.action.value}, prio= {pp.priority}; reason= {pp.policy.value}; st= {pp.ts.send_ts}, ft= {pp.ts.forward_ts}")

# initialize controller and switch objects and their relationship + tests
def main():
    start = time.time()
    controller = Controller()
    sw = Switch()
    sw.controller_i = controller
    bc = Blockchain()


    # iot generation demo + post-demo flow table output
    run_iot_generation_demo(sw, bc, duration_s=10.0, step_s=0.2)
    
    # create final block for remaining records in pending_list
    if len(bc.pending_list) > 0:
        bc.seal_block()


    # alarm vs iot packet delay evaluation
    alarm_pp = [pp for pp in sw.pp_list if pp.packet.tag == Tag.ALARM]
    iot_pp = [pp for pp in sw.pp_list if pp.packet.tag == Tag.IOT]

    if alarm_pp:
        alarm_avg = sum(pp.ts.forward_ts - pp.ts.send_ts for pp in alarm_pp) / len(alarm_pp)
    else:
        alarm_avg = 0
        
    if iot_pp:
        iot_avg = sum(pp.ts.forward_ts - pp.ts.send_ts for pp in iot_pp) / len(iot_pp)
    else:
        iot_avg = 0

    print(f"[EVAL] ALARM: # of packets={len(alarm_pp)}; avg delay= {alarm_avg}")
    print(f"[EVAL] IOT: # of packets={len(iot_pp)}; avg delay= {iot_avg}")
    
    
    # original blockchain validation check
    
    for b in bc.chain_list: print(f"[TEST] Block #: {b.index}, Tx #: {len(b.tx_list)}, Prev Hash: {b.prev_hash}, Current Hash: {b.cur_hash}")
    print(f"[TEST] Chain Previous/Current Hash Validation Check: {bc.validate_chain()}")


    # tamper test blockchain validation check
    bc.chain_list[0].tx_list[0].src = "Toaster"
    for b in bc.chain_list: print(f"[TEST] Block #: {b.index}, Tx #: {len(b.tx_list)}, Prev Hash: {b.prev_hash}, Current Hash: {b.cur_hash}")
    print(f"[TEST] Chain Previous/Current Hash Validation Check: {bc.validate_chain()}")

    # flow table printout
    for r in sw.flow_table: print(r)



if __name__ == "__main__":
    main()
