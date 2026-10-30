#!/usr/bin/env python3
"""Make QDeviceInfo/QBatteryInfo/QNetworkInfo::disconnectNotify return at once.

usage: patch_qtsysteminfo.py libQt5SystemInfo.so.5.4.0 out.so

They call isSignalConnected(), which takes the object's signal/slot mutex.
QObject::~QObject() calls the sender's disconnectNotify() while holding the
receiver's mutex from the same pool, so when both hash to the same mutex the
GUI thread deadlocks on itself (apps freeze when a page with SystemInfo QML
items is destroyed). Skipping the cleanup only leaves a private->public
signal link alive until the object goes away.
"""
import struct
import subprocess
import sys

RET = 0xD65F03C0
src, dst = sys.argv[1], sys.argv[2]
d = bytearray(open(src, "rb").read())
phoff, = struct.unpack_from("<Q", d, 0x20)
phentsize, phnum = struct.unpack_from("<HH", d, 0x36)
segs = [struct.unpack_from("<IIQQQQQQ", d, phoff + i * phentsize) for i in range(phnum)]


def file_off(va):
    for typ, _, off, vaddr, _, filesz, _, _ in segs:
        if typ == 1 and vaddr <= va < vaddr + filesz:
            return va - vaddr + off
    sys.exit(f"vaddr {va:#x} not in a PT_LOAD segment")


nm = subprocess.run(["nm", "-D", "--defined-only", src], capture_output=True, text=True, check=True).stdout
done = 0
for line in nm.splitlines():
    addr, _, name = line.split(maxsplit=2)
    if name.split("@")[0] in ("_ZN11QDeviceInfo16disconnectNotifyERK11QMetaMethod",
                              "_ZN12QBatteryInfo16disconnectNotifyERK11QMetaMethod",
                              "_ZN12QNetworkInfo16disconnectNotifyERK11QMetaMethod"):
        struct.pack_into("<I", d, file_off(int(addr, 16)), RET)
        print(f"patched {name} at {addr}")
        done += 1
if done != 3:
    sys.exit(f"expected 3 functions, patched {done}")
open(dst, "wb").write(d)
