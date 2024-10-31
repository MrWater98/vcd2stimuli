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

class SignalMonitor:
    def __init__(self, dut):
        self.dut = dut
        self.value_changes = {}
        
    async def monitor_signal(self, signal_name):
        """监控信号变化"""
        signal = getattr(self.dut, signal_name)
        self.value_changes[signal_name] = []
        
        while True:
            await FallingEdge(self.dut.clock)
            self.value_changes[signal_name].append({
                'time': cocotb.utils.get_sim_time('ns'),
                'value': signal.value.binstr
            })

async def setup_dut(dut, clock_period=10):
    """设置DUT的时钟和复位"""
    # 创建时钟
    clock = Clock(dut.clock, clock_period, units="ns")
    cocotb.start_soon(clock.start())
    
    # 复位
    dut.reset.value = 1
    await Timer(20, units="ns")
    await FallingEdge(dut.clock)
    dut.reset.value = 0
    await FallingEdge(dut.clock)

async def drive_signals(dut, replayer):
    """驱动信号"""
    prev_time = 0
    
    for time in replayer.timestamps:
        await Timer(time - prev_time, units="ns")
        
        for signal_name in replayer.signal_names:
            if hasattr(dut, signal_name):
                value = replayer.get_value_at_time(signal_name, time)
                signal = getattr(dut, signal_name)
                
                # 处理不同类型的值
                if value.startswith('b'):
                    signal.value = BinaryValue(value[1:])
                elif value.lower() in ['x', 'z']:
                    signal.value = value.lower()
                else:
                    try:
                        signal.value = int(value)
                    except ValueError:
                        signal.value = value
        
        prev_time = time

@cocotb.test()
async def test_stimuli_replay(dut):
    """主测试函数"""
    # 获取CSV文件路径（从环境变量或使用默认值）
    csv_file = os.environ.get('CSV_FILE', 'input.csv')
    
    # 初始化信号重放器
    replayer = SignalReplay(csv_file)
    
    # 遍历时间戳
    for time in replayer.timestamps:
        getattr(dut,'clock').value = 0
        await Timer(1, units='ns')
        # 为每个信号设置对应时间点的值
        for signal_name in replayer.signal_names:
            if hasattr(dut, signal_name) and signal_name != 'clock':
                value = replayer.get_value_at_time(signal_name, time)
                signal = getattr(dut, signal_name)
                
                # 设置信号值
                if value.startswith('b'):
                    signal.value = BinaryValue(value[1:])
                elif value.lower() in ['x', 'z']:
                    signal.value = value.lower()
                else:
                    try:
                        cocotb.log.info(f"Setting {signal_name} to {value}")
                        signal.value = BinaryValue(value)
                    except ValueError:
                        cocotb.log.info(f"Invalid value '{value}' for signal '{signal_name}'")

        if hasattr(dut, 'coverage2'):
            cocotb.log.info(f"Time {time}ns: coverage2[188] = {dut.coverage2.value[188]}")
        
        # 等待1ns
        getattr(dut,'clock').value = 1
        await Timer(1, units='ns')