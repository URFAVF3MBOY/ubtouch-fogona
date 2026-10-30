#!/usr/bin/env python3
"""Add files to the ramdisk of a ramdisk-only boot image (init_boot, header v4).

usage: ramdisk_boot.py in.img out.img MODE:PATH_IN_RAMDISK:LOCAL_FILE ...
  e.g. ramdisk_boot.py init_boot.img new.img 0644:overlay.d/x.rc:x.rc

Edits the newc cpio directly (keeps owners/modes of existing entries, which
plain cpio can't repack for root-only files) and recompresses as lz4 legacy.
Existing entries with the same path are replaced.
"""
import struct
import subprocess
import sys

PAGE = 4096


def pad4(n):
    return (4 - n % 4) % 4


def parse_cpio(data):
    entries, off = [], 0
    while True:
        hdr = data[off:off + 110]
        if hdr[:6] not in (b"070701", b"070702"):
            sys.exit(f"bad cpio magic at {off}")
        fields = [int(hdr[6 + i * 8:14 + i * 8], 16) for i in range(13)]
        namesize, filesize = fields[11], fields[6]
        name_end = off + 110 + namesize
        name = data[off + 110:name_end - 1].decode()
        body = name_end + pad4(110 + namesize)
        content = data[body:body + filesize]
        off = body + filesize + pad4(filesize)
        if name == "TRAILER!!!":
            return entries
        entries.append((name, fields, content))


def build_entry(name, fields, content):
    raw = name.encode() + b"\0"
    fields = list(fields)
    fields[6], fields[11] = len(content), len(raw)
    hdr = b"070701" + b"".join(b"%08X" % f for f in fields)
    out = hdr + raw + b"\0" * pad4(110 + len(raw)) + content
    return out + b"\0" * pad4(len(content))


def main(src, dst, adds):
    with open(src, "rb") as f:
        img = f.read()
    if img[:8] != b"ANDROID!":
        sys.exit("not a boot image")
    kernel_size, ramdisk_size, _osv, header_size = struct.unpack_from("<4I", img, 8)
    if kernel_size:
        sys.exit("expected a ramdisk-only image (init_boot)")
    rd = img[PAGE:PAGE + ramdisk_size]
    cpio = subprocess.run(["lz4", "-dc"], input=rd, capture_output=True, check=True).stdout
    entries = parse_cpio(cpio)

    ino = max(e[1][0] for e in entries) + 1
    for spec in adds:
        mode, path, local = spec.split(":", 2)
        with open(local, "rb") as f:
            content = f.read()
        entries = [e for e in entries if e[0] != path]
        dirs = path.split("/")[:-1]
        for i in range(len(dirs)):
            d = "/".join(dirs[:i + 1])
            if not any(e[0] == d for e in entries):
                entries.append((d, [ino, 0o40755, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0], b""))
                ino += 1
        entries.append((path, [ino, 0o100000 | int(mode, 8), 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0], content))
        ino += 1

    out = b"".join(build_entry(*e) for e in entries)
    out += build_entry("TRAILER!!!", [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0], b"")
    newrd = subprocess.run(["lz4", "-l", "-12", "-c"], input=out, capture_output=True, check=True).stdout

    header = bytearray(img[:header_size])
    struct.pack_into("<I", header, 12, len(newrd))
    if struct.unpack_from("<I", img, 40)[0] == 4:
        struct.pack_into("<I", header, 44 + 1536, 0)  # drop boot signature
    with open(dst, "wb") as f:
        f.write(bytes(header) + b"\0" * (-len(header) % PAGE))
        f.write(newrd + b"\0" * (-len(newrd) % PAGE))
    print(f"{len(entries)} entries, ramdisk {ramdisk_size} -> {len(newrd)} bytes")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
