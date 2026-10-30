#!/usr/bin/env python3
"""Split an Android vendor_boot (header v3/v4) image into its ramdisk(s) and dtb."""
import os
import struct
import sys


def align(x, page):
    return (x + page - 1) // page * page


def main(img, out):
    os.makedirs(out, exist_ok=True)
    with open(img, "rb") as f:
        data = f.read()
    if data[:8] != b"VNDRBOOT":
        sys.exit("not a vendor_boot image")
    version, page, _kaddr, _raddr, ramdisk_size = struct.unpack_from("<5I", data, 8)
    cmdline = data[28:28 + 2048].split(b"\0")[0].decode()
    off = 28 + 2048
    _tags, = struct.unpack_from("<I", data, off); off += 4
    name = data[off:off + 16].split(b"\0")[0].decode(); off += 16
    header_size, dtb_size = struct.unpack_from("<2I", data, off); off += 8
    off += 8  # dtb_addr
    table_size = entries = entry_size = bootconfig_size = 0
    if version >= 4:
        table_size, entries, entry_size, bootconfig_size = struct.unpack_from("<4I", data, off)

    print(f"header v{version} page={page} name={name!r} ramdisk={ramdisk_size} dtb={dtb_size}")
    print(f"cmdline: {cmdline}")
    with open(os.path.join(out, "cmdline.txt"), "w") as f:
        f.write(cmdline + "\n")

    rd_off = align(header_size, page)
    ramdisk = data[rd_off:rd_off + ramdisk_size]
    dtb_off = rd_off + align(ramdisk_size, page)
    with open(os.path.join(out, "dtb"), "wb") as f:
        f.write(data[dtb_off:dtb_off + dtb_size])

    if version >= 4 and entries:
        tbl_off = dtb_off + align(dtb_size, page)
        for i in range(entries):
            e = tbl_off + i * entry_size
            size, offset, rtype = struct.unpack_from("<3I", data, e)
            rname = data[e + 12:e + 12 + 32].split(b"\0")[0].decode() or f"ramdisk{i}"
            print(f"  ramdisk[{i}] {rname!r} type={rtype} size={size}")
            with open(os.path.join(out, f"ramdisk-{i}-{rname}.img"), "wb") as f:
                f.write(ramdisk[offset:offset + size])
    else:
        with open(os.path.join(out, "ramdisk-0.img"), "wb") as f:
            f.write(ramdisk)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
