import os
import csv
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.binary import BinaryValue

import debugpy

debugpy.listen(("0.0.0.0", 4000))
cocotb.log.info("Ready For Connections.")
debugpy.wait_for_client()

def clean_signal_name_and_get_index(signal_name):
    """清理信号名称，去除位宽信息，并且获得下标并返回"""
    # 例如 xx[3] -> xx, 3
    left_bracket_pos = signal_name.find('[')
    right_bracket_pos = signal_name.find(']')
    if left_bracket_pos != -1 and right_bracket_pos != -1:
        return signal_name[:left_bracket_pos], int(signal_name[left_bracket_pos+1:right_bracket_pos])
    return signal_name, -1

class SignalReplay:
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.signals = {}
        self.timestamps = []
        self.signal_names = []
        self._parse_csv()

    def _clean_signal_name(self, signal_name):
        """清理信号名称，去除位宽信息"""
        # 找到第一个左中括号的位置
        bracket_pos = signal_name.find('[')
        if bracket_pos != -1:
            # 只返回中括号之前的部分
            return signal_name[:bracket_pos]
        return signal_name

    def _parse_csv(self):
        """解析CSV文件"""
        with open(self.csv_file, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            # 清理信号名称，去除位宽信息
            self.signal_names = [self._clean_signal_name(header) for header in headers[1:]]
            
            # 初始化信号字典
            for signal in self.signal_names:
                self.signals[signal] = {}
            
            # 读取所有数据
            for row in reader:
                time = int(row[0])
                self.timestamps.append(time)
                for i, value in enumerate(row[1:], 0):
                    signal_name = self.signal_names[i]
                    self.signals[signal_name][time] = value

    def get_value_at_time(self, signal_name, time):
        """获取指定时间点的信号值"""
        clean_name = self._clean_signal_name(signal_name)
        return self.signals[clean_name].get(time, None)

class SignalComparator:
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.signals = {}
        self.timestamps = []
        self.signal_names = []
        self._parse_csv()

    def _clean_signal_name(self, signal_name):
        """清理信号名称，去除位宽信息"""
        # 找到第一个右中括号的位置
        bracket_pos = signal_name.rfind('[')
        if bracket_pos != -1:
            # 只返回中括号之前的部分
            return signal_name[:bracket_pos]
        return signal_name

    def _parse_csv(self):
        """解析CSV文件"""
        with open(self.csv_file, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            # 清理信号名称，去除位宽信息
            self.signal_names = [self._clean_signal_name(header) for header in headers[1:]]
            
            # 初始化信号字典
            for signal in self.signal_names:
                self.signals[signal] = {}
            
            # 读取所有数据
            for row in reader:
                time = int(row[0])
                self.timestamps.append(time)
                for i, value in enumerate(row[1:], 0):
                    signal_name = self.signal_names[i]
                    self.signals[signal_name][time] = value

    def get_value_at_time(self, signal_name, time):
        """获取指定时间点的信号值"""
        # clean_name = self._clean_signal_name(signal_name)
        return self.signals[signal_name].get(time, None)

@cocotb.test()
async def test_stimuli_replay(dut):
    """主测试函数"""
    # 获取CSV文件路径（从环境变量或使用默认值）
    csv_file = os.environ.get('CSV_FILE', 'input.csv')
    cmpcsv_file = os.environ.get('CMPCSV_FILE', None)
    reglist_file = os.environ.get('REGLIST_FILE', None)
    # get reglist from reglist_file path
    if reglist_file:
        with open(reglist_file, 'r') as f:
            reglist = [line.strip() for line in f if line.strip()]
    else:
        reglist = []


    # 初始化信号重放器
    replayer = SignalReplay(csv_file)
    if cmpcsv_file!=None:
        comparator = SignalComparator(cmpcsv_file)
    else:
        comparator = None


    # 遍历时间戳
    for time in replayer.timestamps:
        cocotb.log.info(f"[INFO] Time {time}ns: ")
        getattr(dut, 'clock').value = 0
        await Timer(1, units='ns')
        if hasattr(dut, 'coverage34'):
            cocotb.log.info(f"Time {time}ns: coverage34 = {str(dut.coverage34.value)}")
        
        # 为每个信号设置对应时间点的值
        for signal_name in replayer.signal_names:
            if hasattr(dut, signal_name) and signal_name != 'clock':
                value = replayer.get_value_at_time(signal_name, time)
                signal = getattr(dut, signal_name)
                
                # 设置信号值
                cocotb.log.info(f"Setting {signal_name} to {value}")
                signal.value = BinaryValue(value)

        
        if comparator:
            cocotb.log.info('[CHECKING REGLIST]')
            dict_mismtach_regs = {}
            dict_match_regs = {}
            # 检查每个寄存器的值
            for _signal_name in comparator.signal_names:
                signal_name, index = clean_signal_name_and_get_index(_signal_name)
                if hasattr(dut, signal_name) and signal_name != 'clock' and signal_name in reglist:
                    if index != -1:
                        expected_value = comparator.get_value_at_time(signal_name + f'[{str(index)}]', time)
                    else:
                        expected_value = comparator.get_value_at_time(signal_name, time)
                    signal = getattr(dut, signal_name)
                    if type(signal.value) == list and index != -1:
                        if signal.value[index] != BinaryValue(expected_value):
                            dict_mismtach_regs[f"{signal_name}[{index}]"] = (expected_value, signal.value[index])
                        else:
                            dict_match_regs[f"{signal_name}[{index}]"] = (expected_value, signal.value[index])
                    elif signal.value != BinaryValue(expected_value):
                        dict_mismtach_regs[signal_name] = (expected_value, signal.value)

        
            for _signal_name in comparator.signal_names:
                signal_name, index = clean_signal_name_and_get_index(_signal_name)
                if hasattr(dut, signal_name) and signal_name != 'clock' and signal_name in reglist:
                    if index != -1:
                        expected_value = comparator.get_value_at_time(signal_name + f'[{str(index)}]', time+5) # reg update after posedge
                    else:
                        expected_value = comparator.get_value_at_time(signal_name, time+5) # reg update after posedge
                    signal = getattr(dut, signal_name)
                    if type(signal.value) == list and index != -1: # checking a list
                        cocotb.log.info(f"[INFO] Signal {signal_name} is a list, We checking the value accroding to the index")
                        if signal.value[index] != BinaryValue(expected_value) and signal_name in dict_mismtach_regs:
                            cocotb.log.info(f"[ERROR] Signal {signal_name}[{index}] mismatch before the time {time}ns: expected {dict_mismtach_regs[f'{signal_name}[{index}]'][0]}, got {dict_mismtach_regs[f'{signal_name}[{index}]'][1]}")
                            cocotb.log.info(f"[ERROR] Signal {signal_name}[{index}] mismatch after time {time}ns: expected {expected_value}, got {signal.value[index]}")
                        else:
                            cocotb.log.info(f"[INFO] Signal {signal_name}[{index}] match before the time {time}ns")
                            cocotb.log.info(f"[INFO] Signal {signal_name}[{index}] match after time {time}ns")
                    elif signal.value != BinaryValue(expected_value) and signal_name in dict_mismtach_regs:
                        cocotb.log.info(f"[ERROR] Signal {signal_name} mismatch before the time {time}ns: expected {dict_mismtach_regs[signal_name][0]}, got {dict_mismtach_regs[signal_name][1]}")
                        cocotb.log.info(f"[ERROR] Signal {signal_name} mismatch after time {time}ns: expected {expected_value}, got {signal.value}")
                    elif signal.value == BinaryValue(expected_value) and signal_name in dict_match_regs:
                        cocotb.log.info(f"[INFO] Signal {signal_name} match before and after posedge of timer at time {time}ns: expected {expected_value}, got {signal.value}")
                    elif signal.value != BinaryValue(expected_value) and signal_name in dict_match_regs:
                        cocotb.log.info(f'[WARNING] Mismatch may happen, please check the signal {signal_name} carefully')
                        cocotb.log.info(f'[INFO] Signal {signal_name} before posedge of timer at time {time}ns: expected {dict_match_regs[signal_name][0]}, got {dict_match_regs[signal_name][1]}')
                        cocotb.log.info(f"[INFO] Signal {signal_name} after posedge of timer at time {time}ns: expected {expected_value}, got {signal.value}")
                    elif signal.value == BinaryValue(expected_value) and signal_name in dict_mismtach_regs:
                        cocotb.log.info(f"[Warning] mismatch may happen, please check the signal {signal_name} carefully")
                        cocotb.log.info(f"[INFO] Signal {signal_name} mismatch before the time {time}ns: expected {dict_mismtach_regs[signal_name][0]}, got {dict_mismtach_regs[signal_name][1]}")
                        cocotb.log.info(f"[INFO] Signal {signal_name} match after time {time}ns: expected {expected_value}, got {signal.value}")

            cocotb.log.info('[CHECKING WIRE & Port]')
            dict_mismtach_wires = {}
            dict_match_wires = {}
            for signal_name in comparator.signal_names:
                if hasattr(dut, signal_name) and signal_name != 'clock' and signal_name not in reglist:
                    expected_value = comparator.get_value_at_time(signal_name, time)
                    signal = getattr(dut, signal_name)
                    if signal.value != BinaryValue(expected_value):
                        dict_mismtach_wires[signal_name] = (expected_value, signal.value)
                        # cocotb.log.info(f"Signal {signal_name} mismatch at time {time}ns: expected {expected_value}, got {signal.value}")
                    else:
                        dict_match_wires[signal_name] = (expected_value, signal.value)

            

        # 等待1ns
        getattr(dut, 'clock').value = 1
        await Timer(1, units='ns')
        
        if comparator:
            for signal_name in comparator.signal_names:
                if hasattr(dut, signal_name) and signal_name != 'clock' and signal_name not in reglist:
                    expected_value = comparator.get_value_at_time(signal_name, time)
                    signal = getattr(dut, signal_name)
                    if signal.value != BinaryValue(expected_value) and signal_name in dict_mismtach_wires:
                        if type(dict_mismtach_wires[signal_name][0]) != list and type(dict_mismtach_wires[signal_name][1])!=list and type(signal.value) != list:
                            cocotb.log.info(f"[ERROR] Signal {signal_name} mismtach before the time {time}ns: expected {dict_mismtach_wires[signal_name][0]}, got {dict_mismtach_wires[signal_name][1]}")
                            cocotb.log.info(f"[ERROR] Signal {signal_name} mismatch after time {time}ns: expected {expected_value}, got {signal.value}")
                        else:
                            cocotb.log.info(f"[INFO] Signal {signal_name} mismtach before the time {time}ns")
                            cocotb.log.info(f"[INFO] Signal {signal_name} mismatch after time {time}ns")
                    elif signal.value == BinaryValue(expected_value) and signal_name in dict_match_wires:
                        cocotb.log.info(f'[INFO] Signal {signal_name} match before and after posedge of timer at time {time}ns: expected {dict_match_wires[signal_name][0]}, got {dict_match_wires[signal_name][1]}')
                    elif signal.value != BinaryValue(expected_value) and signal_name in dict_match_wires:
                        cocotb.log.info(f'[WARNING] Mismatch may happen, please check the signal {signal_name} carefully')
                        cocotb.log.info(f'[INFO] Signal {signal_name} before posedge of timer at time {time}ns: expected {dict_match_wires[signal_name][0]}, got {dict_match_wires[signal_name][1]}')
                        cocotb.log.info(f"[INFO] Signal {signal_name} after posedge of timer at time {time}ns: expected {expected_value}, got {signal.value}")
                    elif signal.value == BinaryValue(expected_value) and signal_name in dict_mismtach_wires:
                        cocotb.log.info(f"[Warning] mismatch may happen, please check the signal {signal_name} carefully")
                        cocotb.log.info(f"[INFO] Signal {signal_name} mismatch before the time {time}ns: expected {dict_mismtach_wires[signal_name][0]}, got {dict_mismtach_wires[signal_name][1]}")
                        cocotb.log.info(f"[INFO] Signal {signal_name} match after time {time}ns: expected {expected_value}, got {signal.value}")
                    # elif signal.value != BinaryValue(expected_value) and signal_name in dict_match_wires:
                    #     cocotb.log.info(f"[INFO] Signal {signal_name} mismatch after posedge of timer at time {time}ns: expected {expected_value}, got {signal.value}")
                    #     cocotb.log.info(f"[INFO] But match before posedge of timer at time {time}ns: expected {dict_match_wires[signal_name][0]}, got {dict_match_wires[signal_name][1]}")
        
        

    # 在时间戳结束后继续访问两次
    for _ in range(5):
        getattr(dut, 'clock').value = 0
        await Timer(1, units='ns')
        getattr(dut, 'clock').value = 1
        await Timer(1, units='ns')

    # 打印最终的 coverage34
    if hasattr(dut, 'coverage34'):
        cocotb.log.info(f"Final coverage34 = {str(dut.coverage34.value)}")