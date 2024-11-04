import os
import csv
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.binary import BinaryValue

import debugpy

# debugpy.listen(("0.0.0.0", 4000))
# cocotb.log.info("Ready For Connections.")
# debugpy.wait_for_client()

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
    comparator = SignalComparator(cmpcsv_file)


    # dut.reset.value = 1
    # getattr(dut, 'clock').value = 1
    # await Timer(5, units='ns')
    # getattr(dut, 'clock').value = 0
    # await Timer(5, units='ns')
    # getattr(dut, 'clock').value = 1
    # await Timer(5, units='ns')
    # getattr(dut, 'clock').value = 0
    # await Timer(5, units='ns')
    # getattr(dut, 'clock').value = 1
    # await Timer(5, units='ns')
    # getattr(dut, 'clock').value = 0
    # await Timer(5, units='ns')
    # getattr(dut, 'clock').value = 1
    # await Timer(5, units='ns')
    # dut.reset.value = 0

    # 遍历时间戳
    for time in replayer.timestamps[0:2]:
        getattr(dut, 'clock').value = 0
        await Timer(1, units='ns')
        if hasattr(dut, 'coverage34'):
            cocotb.log.info(f"Time {time}ns: coverage0 = {str(dut.coverage0.value)}")
            cocotb.log.info(f"Time {time}ns: coverage34 = {str(dut.coverage34.value)}")
        
        # 为每个信号设置对应时间点的值
        for signal_name in replayer.signal_names:
            if hasattr(dut, signal_name) and signal_name != 'clock':
                value = replayer.get_value_at_time(signal_name, time)
                signal = getattr(dut, signal_name)
                
                # 设置信号值
                cocotb.log.info(f"Setting {signal_name} to {value}")
                signal.value = BinaryValue(value)

        
        cocotb.log.info('[CHECKING REGLIST]')
        # 检查每个信号的值
        for signal_name in comparator.signal_names:
            if hasattr(dut, signal_name) and signal_name != 'clock' and signal_name in reglist:
                expected_value = comparator.get_value_at_time(signal_name, time)
                signal = getattr(dut, signal_name)
                if signal.value != BinaryValue(expected_value):
                    cocotb.log.info(f"Signal {signal_name} mismatch at time {time}ns: expected {expected_value}, got {signal.value}")
                # cocotb.log.info(f"We are checking {signal_name} at time {time}ns: expected {expected_value}, got {signal.value}")
                # 检查信号值
                # assert signal.value == BinaryValue(expected_value), f"Signal {signal_name} mismatch at time {time}ns: expected {expected_value}, got {signal.value}"

        # 等待1ns
        getattr(dut, 'clock').value = 1
        await Timer(1, units='ns')

        cocotb.log.info('[CHECKING WIRE]')
        for signal_name in comparator.signal_names:
            if hasattr(dut, signal_name) and signal_name != 'clock' and signal_name not in reglist:
                expected_value = comparator.get_value_at_time(signal_name, time)
                signal = getattr(dut, signal_name)
                if signal.value != BinaryValue(expected_value):
                    cocotb.log.info(f"Signal {signal_name} mismatch at time {time}ns: expected {expected_value}, got {signal.value}")

        

    # 在时间戳结束后继续访问两次
    for _ in range(2):
        getattr(dut, 'clock').value = 0
        await Timer(5, units='ns')
        getattr(dut, 'clock').value = 1
        await Timer(5, units='ns')

    # 打印最终的 coverage34
    if hasattr(dut, 'coverage34'):
        cocotb.log.info(f"Final coverage34 = {str(dut.coverage34.value)}")