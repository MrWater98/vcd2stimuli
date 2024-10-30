import Verilog_VCD
import argparse
import sys
import csv
from collections import defaultdict

def read_input_list(input_list_file):
    """读取input列表文件"""
    with open(input_list_file, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def parse_vcd_signals(vcd_file, signal_list):
    """解析VCD文件中指定信号的值"""
    vcd_data = Verilog_VCD.parse_vcd(vcd_file)
    
    # 获取时间刻度
    timescale = Verilog_VCD.get_timescale()
    endtime = Verilog_VCD.get_endtime()
    
    # 创建结果字典
    results = {}
    
    # 处理每个信号
    for code, data in vcd_data.items():
        for net in data['nets']:
            signal_name = f"{net['name']}"
            if signal_name in signal_list:
                # 获取信号的时间-值对
                if 'tv' in data:
                    results[signal_name] = data['tv']
    
    return results, timescale, endtime

def organize_by_cycle(results):
    """将结果按周期组织"""
    cycle_data = defaultdict(dict)
    all_times = set()
    
    # 收集所有时间点
    for signal_name, tv_pairs in results.items():
        for time, value in tv_pairs:
            all_times.add(time)
    
    # 按时间排序
    sorted_times = sorted(all_times)
    
    # 对每个信号，找到每个时间点的值
    for signal_name, tv_pairs in results.items():
        current_value = 'x'  # 默认值
        tv_index = 0
        
        for time in sorted_times:
            # 更新当前值
            while tv_index < len(tv_pairs) and tv_pairs[tv_index][0] <= time:
                current_value = tv_pairs[tv_index][1]
                tv_index += 1
            
            cycle_data[time][signal_name] = current_value
    
    return cycle_data, sorted_times

def export_to_csv(cycle_data, sorted_times, signal_list, output_file):
    """导出数据到CSV文件"""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # 写入表头
        header = ['Time'] + signal_list
        writer.writerow(header)
        
        # 写入每个时间点的数据
        for time in sorted_times:
            row = [time]
            for signal in signal_list:
                row.append(cycle_data[time].get(signal, 'x'))
            writer.writerow(row)

def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='Parse VCD file for specific inputs')
    parser.add_argument('--vcd', required=True, help='Path to VCD file')
    parser.add_argument('--inputs', required=True, help='Path to input list file')
    parser.add_argument('--output', default='output.csv', help='Path to output CSV file')
    
    args = parser.parse_args()
    
    try:
        # 读取输入列表
        input_signals = read_input_list(args.inputs)
        
        # 解析VCD文件
        results, timescale, endtime = parse_vcd_signals(args.vcd, input_signals)
        
        # 按周期组织数据
        cycle_data, sorted_times = organize_by_cycle(results)
        
        # 导出到CSV文件
        export_to_csv(cycle_data, sorted_times, input_signals, args.output)
        
        print(f"Timescale: {timescale}")
        print(f"End time: {endtime}")
        print(f"Results have been exported to {args.output}")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()