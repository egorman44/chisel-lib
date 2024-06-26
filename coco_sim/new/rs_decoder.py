# All tests are lacoted here:
import os
import argparse
from config import RsConfig
import cocotb
from cocotb.runner import get_runner
from config import PRJ_DIR, N_LEN, K_LEN, T_LEN, REDUNDANCY, FCR
import random
from rs_packets_builder import RsPacketsBuilder
from rs_interface import RsIfBuilder
from rs_env import RsEnv

class IfContainer():

    def __init__(self):
        self.if_name = ''
        self.if_ptr = None
        self.if_packets = []        

def parse_command_line():
    
    args = argparse.ArgumentParser(add_help=True)
    
    args.add_argument("-l", "--hdl_toplevel",
                      dest="hdl_toplevel",
                      required=True,
                      help='Set hdl top level. For Example RsSynd, RsBm, RsChien, RsForney, RsDecTop.'
                      )
    
    args.add_argument("-t", "--testcase",
                      dest="testcase",
                      required=False,
                      default=None,
                      help='Set testcases you want to run. Check available test in rs_testcases.py.'
                      )

    args.add_argument("-s", "--seed",
                      dest="seed",
                      required=False,
                      default=None,
                      help='Set run seed.'
                      )
    
    return args.parse_args()    

def build_and_run():
    sim = os.getenv("SIM", "verilator")
    runner = get_runner(sim)
    sv_top = args.hdl_toplevel+".sv"
    runner.build(
        defines={},
        parameters={},
        verilog_sources=[PRJ_DIR / sv_top],
        includes={},
        hdl_toplevel=args.hdl_toplevel,
        build_args=[ '--timing', '--assert' , '--trace' , '--trace-structs', '--trace-max-array', '512', '--trace-max-width', '512'],
        always=True,
    )
    
    runner.test(hdl_toplevel=args.hdl_toplevel,
                test_module='rs_decoder',
                testcase=args.testcase,
                )
    
if __name__ == "__main__":    
    args = parse_command_line()
    if args.seed:
        os.environ["RANDOM_SEED"] = args.seed
    
    #positions = [0,1,2,3]
    #pkt_builder.corrupt_msg(positions)
    #for s_if in env_cfg['s_if']:
    #    print(f"s_if = {s_if}")
    #    env_cfg['s_if'][s_if] = pkt_builder.get_pkt(s_if)
    #for m_if in env_cfg['m_if']:
    #    print(f"m_if = {m_if}")
    #    env_cfg['m_if'][m_if] = pkt_builder.get_pkt(m_if)
    
    #for s_if in env_cfg['s_if']:
    #    gen_drv_pkt = pkt_builder.get_pkt(s_if)
    #drv_pkt = gen_pkt()
    #drv_pkt.print_pkt()
    build_and_run()

'''
TESTS:

'''
def get_if(top_level):
    if top_level == 'RsSynd':
        s_if = ['sAxisIf']
        m_if = ['syndIf'] 
    elif top_level == 'RsBm':
        s_if = ['syndIf'] 
        m_if = ['errLocIf'] 
    elif top_level == 'RsChien':
        s_if = ['errLocIf'] 
        m_if = ['errPosIf'] 
    elif top_level == 'RsForney':
        s_if = ['errPosIf', 'syndIf'] 
        m_if = ['errValIf'] 
    elif top_level == 'RsDecoder':
        s_if = ['sAxisIf'] 
        m_if = ['errValIf', 'errPosOutIf'] 
    else:
        raise ValueError(f"Not expected value for top_level = {top_level}")
    return s_if, m_if

@cocotb.test()
async def random_error(dut):
    pkt_num = 10
    s_if_containers = []
    m_if_containers = []
    
    if_builder = RsIfBuilder(dut)
    pkt_builder = RsPacketsBuilder(K_LEN, REDUNDANCY, FCR, 'increment')
    # Get interfaces
    s_if_list, m_if_list = get_if(dut._name)
    for if_name in s_if_list:
        if_container = IfContainer()
        if_container.if_name = if_name
        if_container.if_ptr = if_builder.get_if(if_name)
        s_if_containers.append(if_container)
    for if_name in m_if_list:
        if_container = IfContainer()
        if_container.if_name = if_name
        if_container.if_ptr = if_builder.get_if(if_name)
        m_if_containers.append(if_container)        
    # Generate packets
    for i in range(pkt_num):
        err_num = 3
        err_pos = random.sample(range(0, N_LEN-1), err_num)
        pkt_builder.generate_msg()
        pkt_builder.encode_msg()
        pkt_builder.corrupt_msg(err_pos)
        for i in range(len(s_if_containers)):
            s_if_containers[i].if_packets.append(pkt_builder.get_pkt(s_if_containers[i].if_name))
        for i in range (len(m_if_containers)):
            #m_if_containers[i].if_packets.append(pkt_builder.get_pkt(m_if_containers[i].if_name))
            mon_pkt = pkt_builder.get_pkt(m_if_containers[i].if_name)
            m_if_containers[i].if_packets.append(mon_pkt)
            
            
    # Build environment
    env = RsEnv(dut)
    env.build_env(s_if_containers, m_if_containers)
    await env.run()
    env.post_run()
    
