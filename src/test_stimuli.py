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

@cocotb.test()
async def test_stimuli_replay(dut):
    """主测试函数"""
    # 获取CSV文件路径（从环境变量或使用默认值）
    csv_file = os.environ.get('CSV_FILE', 'input.csv')
    
    # 初始化信号重放器
    replayer = SignalReplay(csv_file)
    
    dut.reset = 1
    getattr(dut, 'clock').value = 1
    await Timer(5, units='ns')
    getattr(dut, 'clock').value = 0
    await Timer(5, units='ns')
    dut.reset = 0

    # 遍历时间戳
    for time in replayer.timestamps[2:]:
        # if time == 0 or time == 5:
        #     getattr(dut, 'reset').value = 1
        # else:
        #     getattr(dut, 'reset').value = 0
        getattr(dut, 'clock').value = 1
        await Timer(5, units='ns')
        if hasattr(dut, 'coverage34'):
            cocotb.log.info(f"Time {time}ns: core__div__reset = {str(dut.core__div__reset.value)}")
            cocotb.log.info(f"Time {time}ns: coverage33 = {str(dut.coverage33.value)}")
            cocotb.log.info(f"Time {time}ns: coverage34 = {str(dut.coverage34.value)}")
        
        # 为每个信号设置对应时间点的值
        for signal_name in replayer.signal_names:
            if hasattr(dut, signal_name) and signal_name != 'clock':
                value = replayer.get_value_at_time(signal_name, time)
                signal = getattr(dut, signal_name)
                
                # 设置信号值
                if value.startswith('b'):
                    signal.value = BinaryValue(value[1:])
                elif value.lower() in ['x', 'z']:
                    signal.value = 0
                else:
                    try:
                        cocotb.log.info(f"Setting {signal_name} to {value}")
                        signal.value = BinaryValue(value)
                    except ValueError:
                        cocotb.log.info(f"Invalid value '{value}' for signal '{signal_name}'")

        # 等待1ns
        getattr(dut, 'clock').value = 0
        await Timer(5, units='ns')
        if hasattr(dut, 'coverage34'):
            # print reset
            cocotb.log.info(f"Time {time}ns: core__div__reset = {str(dut.core__div__reset.value)}")
            cocotb.log.info(f"Time {time}ns: coverage33 = {str(dut.coverage33.value)}")
            cocotb.log.info(f"Time {time}ns: coverage34 = {str(dut.coverage34.value)}")

    # 在时间戳结束后继续访问两次
    for _ in range(2):
        getattr(dut, 'clock').value = 1
        await Timer(5, units='ns')
        getattr(dut, 'clock').value = 0
        await Timer(5, units='ns')

    # 打印最终的 coverage34
    if hasattr(dut, 'coverage34'):
        cocotb.log.info(f"Final coverage34 = {str(dut.coverage34.value)}")