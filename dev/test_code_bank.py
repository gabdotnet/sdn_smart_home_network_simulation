# initial flow_table len log
    # print(f"original flow table len= {len(sw.flow_table)}")

    # # test packet
    # p = Packet("Phone", "Internet", "TCP", 80, Tag.BESTEFFORT, now)
    # # print(f"packet created @ {p}")
    
    # # # test match
    # m = Match(src="Phone", dst="Internet", tag=Tag.BESTEFFORT)
    # print(f"match created @ {m}")

    # # flow mod dummy entry
    # flowRule1 = FlowRule(m, Action.FORWARD, 3, 0)
    # print(f"{sw.flow_mod(flowRule, now)}")


    # test for higher prio winning flow table assessment (1 = lowest, 7 = highest)
    # flowRule1 = FlowRule(m, Action.FORWARD, 3, 0)
    # flowRule2 = FlowRule(m, Action.DROP, 7, 0)
    
    # sw.flow_mod(flowRule1, now)
    # print_packet(sw, p, now, 1)
    # sw.flow_mod(flowRule2, now)
    # print_packet(sw, p, now, 1)

    # # process packet test
    # pp = sw.process_packet(p, now)
    # print(f"pp: {pp} || flow_table len= {len(sw.flow_table)}")

    # # hit count test
    # print_packet(sw, p, now, 5)

    # # flow table field retrieval test
    # print(f"{len(sw.flow_table)} || {sw.flow_table[0].priority}")


    # print(f"{sw.flow_table}")





    # rate limit check
    # FIXME:
    # self.packet_q.append(packet)
    # print(len(self.packet_q))
    # window = [p for p in self.packet_q if p.ts <= arrival]
    # print(len(window))

    # remove idle timeout packets from queue before rate limit check
    # count number of packets from same src (threshold 5 same-src packets in a row, drop for 5 seconds if threshold crossed
    # for p in self.packet_q:
    #     if p.ts > now - 1.0:
    #         self.packet_q.popleft()
    #     elif p.src:
    #         continue



    # test cases

    # # IoT → HomeHub | Camera → HomeHub | Allowed (forwarded)
    # t1 = Packet("Camera", "HomeHub", "UDP", 80, Tag.VIDEO, start)
    # # sw.process_packet(t1, start)
    # print("Test 1: IoT → HomeHub | Camera → HomeHub | Allowed (forwarded)")
    # print_packet(sw, t1)
    # # print("\n")

    # # IoT → IoT	| Camera → SmartLight | Blocked (dropped)
    # t2 = Packet("Camera", "SmartLight", "UDP", 80, Tag.VIDEO, start)
    # # sw.process_packet(t2, start)
    # print("Test 2: IoT → IoT | Camera → SmartLight | Blocked (dropped)")
    # print_packet(sw, t2)
    # print_packet(sw, t2)
    # print("\n")

    # # Guest → Internet | GuestPhone → Internet | Allowed (forwarded)
    # t3 = Packet("GuestPhone", "Internet", "TCP", 80, Tag.BESTEFFORT, start)
    # # sw.process_packet(t3, start)
    # print("Test 3: Guest → Internet | GuestPhone → Internet | Allowed (forwarded)")
    # print_packet(sw, t3)
    # print_packet(sw, t3)
    # # print("\n")

    # # Guest → LAN | GuestPhone → Laptop | Blocked (dropped)
    # t4 = Packet("GuestPhone", "Laptop", "TCP", 80, Tag.BESTEFFORT, start)
    # sw.process_packet(t4)
    # print("Test 4: Guest → LAN | GuestPhone → Laptop | Blocked (dropped)")
    # print_packet(sw, t4)
    # print("\n")

    # # VOICE traffic | Phone → Internet (VOICE tag) | Installed with a higher priority flow
    # t5 = Packet("Phone", "Internet", "TCP", 80, Tag.VOICE, start)
    # sw.process_packet(t5)
    # print("Test 5: VOICE traffic | Phone → Internet (VOICE tag) | Installed with a higher priority flow")
    # print_packet(sw, t5)
    # print("\n")
    
    # Rate limit trigger | Camera sends burst traffic | Temporary drop rule installed
    # t6 = Packet("Camera", "Laptop", "UDP", 80, Tag.VIDEO, start)
    # print("Test 6: Rate limit trigger | Camera sends burst traffic | Temporary drop rule installed")
    # print_packet(sw, t6)
    # print("\n")

