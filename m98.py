import enum
import struct

from pymodbus.client.sync import ModbusSerialClient
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

class Coil(enum.IntEnum):
    ISTATE = 0x0510

class Reg(enum.IntEnum):
    CMD = 0x0A00
    IFIX = 0x0A01
    UFIX = 0x0A03
    PFIX = 0x0A05
    RFIX = 0x0A07
    TMCCS = 0x0A09
    TMCVS = 0x0A0B
    UBATTEND = 0x0A2E
    BATT = 0xA30
    U = 0x0B00
    I = 0x0B02
    MODEL = 0x0B06

class Cmd(enum.IntEnum):
    CC = 1
    CV = 2
    CW = 3
    CR = 4
    CC_Soft = 20
    Battery_Test = 38
    ON = 42
    OFF = 43

class Model(enum.IntEnum):
    M9710 = 28


def _float(*values):
    b = BinaryPayloadBuilder(byteorder='>')
    for v in values:
        b.add_32bit_float(v)
    return b.build()

def _defloat(registers):
    d = BinaryPayloadDecoder.fromRegisters(registers, byteorder='>')
    return [d.decode_32bit_float() for r in range(0, len(registers)//2)]


class M98:
    def __init__(self, **kwargs):
        self.conn = ModbusSerialClient('rtu', **kwargs)
        self.conn.connect()
        model = self.conn.read_holding_registers(Reg.MODEL, unit=1).registers[0]
        try:
            self.model = Model(model)
        except ValueError:
            raise RuntimeError('unknown device model: %d' % model)

    def _cmd(self, cmd: Cmd):
        self.conn.write_registers(Reg.CMD, [cmd], unit=1)

    class EnableContext:
        def __init__(self, main, prev_state):
            self.main = main
            self.prev_state = prev_state

        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_value, traceback):
            self.main._cmd(Cmd.ON if self.prev_state else Cmd.OFF)

    def enable(self, state: bool):
        before_state = self.enabled()
        self._cmd(Cmd.ON if state else Cmd.OFF)
        return self.EnableContext(self, before_state)

    def enabled(self):
        return self.conn.read_coils(Coil.ISTATE, unit=1).getBit(0)

    def cc_mode(self, current, risetime=None):
        self.conn.write_registers(Reg.IFIX, _float(current), skip_encode=True, unit=1)
        if risetime:
            self.conn.write_registers(Reg.TMCCS, _float(risetime), skip_encode=True, unit=1)
            self._cmd(Cmd.CC_Soft)
        else:
            self._cmd(Cmd.CC)

    def battery_mode(self, current, end_voltage, start_capacity=0):
        self.conn.write_registers(Reg.IFIX, _float(current), skip_encode=True, unit=1)
        # set end voltage and reset start capacity
        self.conn.write_registers(Reg.UBATTEND, _float(end_voltage, start_capacity), skip_encode=True, unit=1)
        self._cmd(Cmd.Battery_Test)

    def voltage(self):
        return _defloat(self.conn.read_holding_registers(Reg.U, 2, unit=1).registers)[0]

    def current(self):
        return _defloat(self.conn.read_holding_registers(Reg.I, 2, unit=1).registers)[0]

    def capacity(self):
        return _defloat(self.conn.read_holding_registers(Reg.BATT, 2, unit=1).registers)[0]


if __name__ == '__main__':
    import logging
    import sys
    import os
    import time
    import log
    import csv

    logging.basicConfig(level=os.environ.get('LOGLEVEL', 'INFO'))

    m = M98(port=sys.argv[1], baudrate=int(sys.argv[2]))
    m.enable(False)
    m.battery_mode(0.1, 0.8)

    with m.enable(True):
        for data in log.log(m.voltage, m.current, m.capacity, interval=1, condition=m.enabled):
            print(data)
