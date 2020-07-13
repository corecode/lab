#!/usr/bin/env python

import argparse
import os
import tempfile
from msox3000 import MSOX3000

default_dest = os.path.expanduser("~/tmp")
if not os.path.isdir(default_dest) or not os.access(default_dest, os.W_OK|os.X_OK):
    default_dest = "."

parser = argparse.ArgumentParser()
parser.add_argument("--resource", type=str, default='USB0::2391::6050::MY51360463::0::INSTR')
parser.add_argument("--waveform", metavar='CHANNEL', type=str, help='capture waveform in csv')
parser.add_argument("dest", type=str, nargs='?', default=default_dest, help="destination filename or directory (default: %s)" % default_dest)
args = parser.parse_args()

if args.waveform:
    ext = '.csv'
else:
    ext = '.png'

if os.path.isdir(args.dest):
    destf = tempfile.mktemp(ext, "scope_", args.dest)
else:
    destf = args.dest

scope = MSOX3000(args.resource)

scope.open()
if args.waveform:
    scope.waveform(destf, args.waveform)
else:
    scope.hardcopy(destf)
scope.setLocal()
scope.close()

print(destf)
