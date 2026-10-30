#!/usr/bin/env python3
"""Replace the (single) vendor ramdisk in a vendor_boot v4 image.

usage: repack_vendor_boot.py stock_vendor_boot.img new_ramdisk.img out.img

Keeps the header, cmdline, dtb and bootconfig from the stock image. Only
images with one vendor ramdisk table entry are supported (fogona has one).
"""
import struct
import sys


def align(x, page):
    return (x + page - 1) // page * page


def pad(b, page):
    return b + b"\0" * (-len(b) % page)


def main(stock, ramdisk_path, out):
    with open(stock, "rb") as f:
        data = f.read()
    if data[:8] != b"VNDRBOOT":
        sys.exit("not a vendor_boot image")
    version, page, _k, _r, ramdisk_size = struct.unpack_from("<5I", data, 8)
    off = 28 + 2048 + 4 + 16
    header_size, dtb_size = struct.unpack_from("<2I", data, off)
    if version != 4:
        sys.exit("only header v4 supported")
    table_off_in_hdr = off + 16
    table_size, entries, entry_size, bootconfig_size = struct.unpack_from("<4I", data, table_off_in_hdr)
    if entries != 1:
        sys.exit(f"expected 1 vendor ramdisk entry, got {entries}")

    rd_off = align(header_size, page)
    dtb_off = rd_off + align(ramdisk_size, page)
    tbl_off = dtb_off + align(dtb_size, page)
    bc_off = tbl_off + align(table_size, page)
    dtb = data[dtb_off:dtb_off + dtb_size]
    table = bytearray(data[tbl_off:tbl_off + table_size])
    bootconfig = data[bc_off:bc_off + bootconfig_size]

    with open(ramdisk_path, "rb") as f:
        ramdisk = f.read()

    header = bytearray(data[:header_size])
    struct.pack_into("<I", header, 8 + 16, len(ramdisk))   # vendor_ramdisk_size
    struct.pack_into("<2I", table, 0, len(ramdisk), 0)     # entry: size, offset

    with open(out, "wb") as f:
        f.write(pad(bytes(header), page))
        f.write(pad(ramdisk, page))
        f.write(pad(dtb, page))
        f.write(pad(bytes(table), page))
        f.write(pad(bootconfig, page))
    print(f"vendor ramdisk {ramdisk_size} -> {len(ramdisk)} bytes")


if __name__ == "__main__":
    main(*sys.argv[1:4])
