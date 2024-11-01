import os
import argparse
from cocotb_test.simulator import run

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--top', required=True, help='Top-level module name')
    parser.add_argument('--rtl', required=True, help='RTL file path')
    parser.add_argument('--csv', required=True, help='Stimuli CSV file')
    args = parser.parse_args()

    # 设置环境变量
    os.environ['CSV_FILE'] = args.csv

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