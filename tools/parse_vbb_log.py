#!/usr/bin/env python3
"""Extract the newest fogona debug log snapshots from a vendor_boot_b dump.

usage: parse_vbb_log.py vbb.bin initrd_out.txt ut_out.txt
Initrd logger: 100 rotating 256 KB slots at offset 0. UT logger: offset 32 MB.
"""
import re
import sys

SLOT = 256 * 1024

d = open(sys.argv[1], "rb").read()
best, count = None, 0
for i in range(100):
    blk = d[i * SLOT:(i + 1) * SLOT]
    m = re.match(rb"### FOGONA-INITRD-LOG n=(\d+) uptime=([\d.]*)", blk)
    if not m:
        continue
    count += 1
    n = int(m.group(1))
    if best is None or n > best[0]:
        end = blk.find(b"### END")
        best = (n, m.group(2).decode(), blk[:end + 8 if end >= 0 else len(blk)])
if best:
    open(sys.argv[2], "wb").write(best[2])
    print(f"initrd : {count} snapshots, newest n={best[0]} uptime={best[1]}s -> {sys.argv[2]}")
else:
    print("initrd : no log")

ut = d[32 << 20:]
if ut.startswith(b"### FOGONA-UT-LOG"):
    end = ut.find(b"### END")
    open(sys.argv[3], "wb").write(ut[:end + 8])
    print(f"ut : {ut[:60].decode(errors='replace').strip()} -> {sys.argv[3]}")
else:
    print("ut : no log")
