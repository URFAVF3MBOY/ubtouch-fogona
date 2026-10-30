#!/usr/bin/env python3
"""Replace the kernel in an Android boot image (header v3/v4, kernel-only GKI boot).

usage: repack_boot.py stock_boot.img Image out_boot.img [cmdline]

Keeps the stock header fields (os_version, cmdline, header version) and any
ramdisk; drops the boot signature and AVB footer, which an unlocked
bootloader does not enforce.
"""
import struct
import sys

PAGE = 4096  # fixed for header v3/v4


def pad(b):
    return b + b"\0" * (-len(b) % PAGE)


def main(stock, kernel_path, out, cmdline=None):
    with open(stock, "rb") as f:
        data = f.read()
    if data[:8] != b"ANDROID!":
        sys.exit("not a boot image")
    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from("<4I", data, 8)
    header_version, = struct.unpack_from("<I", data, 40)
    if header_version not in (3, 4):
        sys.exit(f"unsupported header version {header_version}")
    ramdisk_off = PAGE + len(pad(b"\0" * kernel_size))
    ramdisk = data[ramdisk_off:ramdisk_off + ramdisk_size]

    with open(kernel_path, "rb") as f:
        kernel = f.read()

    header = bytearray(data[:header_size])
    struct.pack_into("<2I", header, 8, len(kernel), len(ramdisk))
    if cmdline is not None:
        raw = cmdline.encode()
        if len(raw) >= 1536:
            sys.exit("cmdline too long")
        header[44:44 + 1536] = raw + b"\0" * (1536 - len(raw))
    if header_version == 4:
        struct.pack_into("<I", header, 44 + 1536, 0)  # boot signature size

    with open(out, "wb") as f:
        f.write(pad(bytes(header)))
        f.write(pad(kernel))
        if ramdisk:
            f.write(pad(ramdisk))
    print(f"header v{header_version}: kernel {kernel_size} -> {len(kernel)} bytes, ramdisk {len(ramdisk)}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
