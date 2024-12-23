import os
import argparse
from cocotb_test.simulator import run

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--top', required=True, help='Top-level module name')
    parser.add_argument('--clock', required=True, help='clock name')
    parser.add_argument('--rtl', required=True, help='RTL file path')
    parser.add_argument('--csv', required=True, help='Stimuli CSV file')
    parser.add_argument('--id', required=True, help='Test ID: 0-0: coverage0[0]')
    parser.add_argument('--cmpcsv', required=False, help='Comparison CSV file')
    parser.add_argument('--reglist', required=False, help='Comparison reglist file')
    args = parser.parse_args()

    # 设置环境变量
    os.environ['CSV_FILE'] = args.csv
    os.environ['TEST_ID'] = args.id
    os.environ['CLOCK'] = args.clock
    os.environ['SIM'] = 'verilator'
    if hasattr(args, 'cmpcsv') and args.cmpcsv:
        os.environ['CMPCSV_FILE'] = args.cmpcsv
    if hasattr(args, 'reglist') and args.reglist:
        os.environ['REGLIST_FILE'] = args.reglist
        
    # current directory
    os.environ['PWD'] = os.getcwd()

    # 运行测试
    run(
        verilog_sources=[args.rtl],
        toplevel=args.top,
        module='test_stimuli',
        sim_build='sim_build',
        work_dir='run',
        compile_args=['-Wno-fatal'],
        gui=False
    )

if __name__ == "__main__":
    main()