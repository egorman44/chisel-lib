import cocotb
from cocotb.triggers import Timer
from cocotb.triggers import Join
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import with_timeout

from tb_utils import reset_dut
from tb_utils import custom_clock
from tb_utils import watchdog_set

from scoreboard import Comparator
from axis import AxisDriver
from axis import AxisResponder
from axis import AxisMonitor

from config import ENCODE_MSG_DURATION

class RsEnv():
    
    def __init__(self, dut):        
        self.s_drivers = []
        self.m_monitors = []
        self.comparators = []
        self.dut = dut
    
    def build_env(self, s_if_containers, m_if_containers):
        self.s_if_containers = s_if_containers
        self.m_if_containers = m_if_containers
        for i in range (len(self.s_if_containers)):
            self.s_drivers.append(AxisDriver(name=f's_drv{i}',
                                             axis_if=self.s_if_containers[i].if_ptr))
        for i in range (len(self.m_if_containers)):
            self.comparators.append(Comparator(name=f'comp_{self.m_if_containers[i].if_name}'))
            
            self.m_monitors.append(AxisMonitor(name=f'm_mon_{self.m_if_containers[i].if_name}',
                                               axis_if=self.m_if_containers[i].if_ptr,
                                               aport=self.comparators[i].port_out))
            
            self.comparators[i].port_prd = self.m_if_containers[i].if_packets.copy()
                    
    
    async def run(self):
        await cocotb.start(reset_dut(self.dut.reset,200,1))
        await Timer(50, units = "ns")
        
        await cocotb.start(custom_clock(self.dut.clock, 10))
        for m_mon in self.m_monitors:
            await cocotb.start(m_mon.mon_if())
        
        await FallingEdge(self.dut.reset)
        for i in range(10):
            await RisingEdge(self.dut.clock)
        
        # Send packets
        s_coroutings = []
        for pkt_num in range(len(self.s_if_containers[0].if_packets)):
            for i in range(len(self.s_drivers)):            
                s_coroutings.append(cocotb.start_soon(with_timeout(self.s_drivers[i].send_pkt(self.s_if_containers[i].if_packets[pkt_num]), 10_000, 'us')))
            for corouting in s_coroutings:
                await Join(corouting)
            for i in range(ENCODE_MSG_DURATION):
                await RisingEdge(self.dut.clock)
                
        for i in range(ENCODE_MSG_DURATION+100):
            await RisingEdge(self.dut.clock)
            
        #await watchdog_set(self.dut.clock, self.comparators)
        
    def post_run(self):
        print("post_run()")
        for comp in self.comparators:
            print(type(comp))
            comp.compare()
