#!/usr/bin/env python3
"""Unpack / repack an Android DTBO image (DT table, magic 0xd7b7ab1e).

usage: dtbo.py unpack dtbo.img outdir
       dtbo.py pack   outdir dtbo.img     (uses outdir/table.txt written by unpack)
"""
import os
import struct
import sys

MAGIC = 0xD7B7AB1E
HDR = ">8I"     # magic, total_size, header_size, dt_entry_size, dt_entry_count, dt_entries_offset, page_size, version
ENTRY = ">8I"   # dt_size, dt_offset, id, rev, custom[4]


def unpack(img, out):
    os.makedirs(out, exist_ok=True)
    with open(img, "rb") as f:
        data = f.read()
    magic, total, hsize, esize, count, eoff, page, version = struct.unpack_from(HDR, data, 0)
    if magic != MAGIC:
        sys.exit("not a DTBO image")
    lines = [f"header {hsize} {esize} {page} {version}"]
    for i in range(count):
        size, off, id_, rev, c0, c1, c2, c3 = struct.unpack_from(ENTRY, data, eoff + i * esize)
        name = f"entry{i:02d}.dtb"
        with open(os.path.join(out, name), "wb") as f:
            f.write(data[off:off + size])
        lines.append(f"{name} {id_:#x} {rev:#x} {c0:#x} {c1:#x} {c2:#x} {c3:#x}")
        print(f"{name}: size={size} id={id_:#x} rev={rev:#x}")
    with open(os.path.join(out, "table.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


def pack(src, img):
    with open(os.path.join(src, "table.txt")) as f:
        rows = [l.split() for l in f if l.strip()]
    _, hsize, esize, page, version = rows[0]
    hsize, esize, page, version = int(hsize), int(esize), int(page), int(version)
    entries = rows[1:]
    blobs = []
    for r in entries:
        with open(os.path.join(src, r[0]), "rb") as f:
            blobs.append(f.read())
    off = hsize + esize * len(entries)
    table = b""
    payload = b""
    for r, blob in zip(entries, blobs):
        vals = [int(x, 16) for x in r[1:]]
        table += struct.pack(ENTRY, len(blob), off + len(payload), *vals)
        payload += blob
    total = off + len(payload)
    header = struct.pack(HDR, MAGIC, total, hsize, esize, len(entries), hsize, page, version)
    with open(img, "wb") as f:
        f.write(header + table + payload)
    print(f"packed {len(entries)} entries, {total} bytes")


if __name__ == "__main__":
    {"unpack": unpack, "pack": pack}[sys.argv[1]](sys.argv[2], sys.argv[3])
