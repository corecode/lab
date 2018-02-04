import enum
import struct
import time
import os
import csv

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
            self.conn.write_registers(Reg.TMCCS, _float(risetime*1000), skip_encode=True, unit=1)
            self._cmd(Cmd.CC_Soft)
        else:
            self._cmd(Cmd.CC)
        return (self.voltage, self.current)

    def battery_mode(self, current, end_voltage, start_capacity=0):
        self.conn.write_registers(Reg.IFIX, _float(current), skip_encode=True, unit=1)
        # set end voltage and reset start capacity
        self.conn.write_registers(Reg.UBATTEND, _float(end_voltage, start_capacity), skip_encode=True, unit=1)
        self._cmd(Cmd.Battery_Test)
        return (self.voltage, self.current, self.capacity)

    def cw_mode(self, power):
        self.conn.write_registers(Reg.PFIX, _float(power), skip_encode=True, unit=1)
        self._cmd(Cmd.CW)
        return (self.voltage, self.current)

    def voltage(self):
        return _defloat(self.conn.read_holding_registers(Reg.U, 2, unit=1).registers)[0]

    def current(self):
        return _defloat(self.conn.read_holding_registers(Reg.I, 2, unit=1).registers)[0]

    def capacity(self):
        return _defloat(self.conn.read_holding_registers(Reg.BATT, 2, unit=1).registers)[0]


class Command:
    @classmethod
    def _run(cls, args):
        m = M98(port=args.port, baudrate=args.baudrate)
        fields = args.mode(m, args)
        l = log.Log(*fields)

        if not args.out:
            args.out = open(os.devnull, 'w')
            args.verbose = True

        if not args.condition:
            args.condition = lambda m, args: m.enabled()

        with m.enable(True):
            csvout = csv.writer(args.out)
            csvout.writerow(l.names)
            for data in l.run(interval=args.interval, condition=lambda: args.condition(m, args)):
                if args.verbose:
                    print(l.pretty_record(data))
                csvout.writerow(data)
                args.out.flush()

    @classmethod
    def _generic_parser(cls, p, mode, condition=None):
        p.add_argument('--interval', type=float, default=1.0)
        p.add_argument('--out', '-o', type=argparse.FileType('w'))
        p.add_argument('--verbose', action='store_const', const=True, default=False)
        p.set_defaults(func=cls._run, mode=mode, condition=condition)

    @classmethod
    def add_parsers(cls, parser):
        parser.add_argument('--port', type=str, required=True)
        parser.add_argument('--baudrate', type=int, default=9600)
        subp = parser.add_subparsers()
        batp = subp.add_parser('battery', help='Battery constant current test')
        batp.add_argument('--current', '-i', type=float, required=True)
        batp.add_argument('--end-voltage', '-v', type=float, required=True)
        cls._generic_parser(batp, lambda m, args: m.battery_mode(current=args.current, end_voltage=args.end_voltage))

        ccp = subp.add_parser('cc', aliases=['constant-current'], help='Constant current test')
        ccp.add_argument('--current', '-i', type=float, required=True)
        ccp.add_argument('--risetime', type=float, default=None)
        cls._generic_parser(ccp, lambda m, args: m.cc_mode(current=args.current, risetime=args.risetime))

        cwp = subp.add_parser('cw', aliases=['constant-power'], help='Constant power test')
        cwp.add_argument('--power', type=float, required=True)
        cwp.add_argument('--end-voltage', '-v', type=float, required=False)
        cls._generic_parser(cwp, lambda m, args: m.cw_mode(power=args.power),
                            condition=lambda m, args: m.enabled() and (not args.end_voltage or m.voltage() > args.end_voltage))


if __name__ == '__main__':
    import logging
    import sys
    import os
    import csv
    import argparse

    import log

    logging.basicConfig(level=os.environ.get('LOGLEVEL', 'INFO'))

    parser = argparse.ArgumentParser(description='M98 Electronic Load Remote Control')
    Command.add_parsers(parser)
    args = parser.parse_args()

    args.func(args)
