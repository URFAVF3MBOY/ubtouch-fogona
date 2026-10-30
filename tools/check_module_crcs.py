#!/usr/bin/env python3
"""Check which prebuilt .ko files would load against a kernel build.

Reads each module's __versions table (symbol CRCs the module was built
against) and compares it with the kernel's Module.symvers. A module whose
CRCs all match (and whose symbols all exist) passes modversions checks.

usage: check_module_crcs.py Module.symvers modules_dir [modules.load]
"""
import os
import struct
import sys


def read_symvers(path):
    crcs = {}
    with open(path) as f:
        for line in f:
            parts = line.split("\t")
            if len(parts) >= 2:
                crcs[parts[1]] = int(parts[0], 16)
    return crcs


def module_versions(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"\x7fELF" or data[4] != 2:
        return None
    shoff, = struct.unpack_from("<Q", data, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from("<3H", data, 0x3A)
    sections = []
    for i in range(shnum):
        name, _type, _flags, _addr, off, size = struct.unpack_from("<IIQQQQ", data, shoff + i * shentsize)
        sections.append((name, off, size))
    stroff = sections[shstrndx][1]
    for name, off, size in sections:
        sname = data[stroff + name:data.index(b"\0", stroff + name)]
        if sname == b"__versions":
            out = {}
            for e in range(off, off + size, 64):
                crc, = struct.unpack_from("<Q", data, e)
                sym = data[e + 8:e + 64].split(b"\0")[0].decode()
                out[sym] = crc & 0xFFFFFFFF
            return out
    return {}


def main():
    symvers = read_symvers(sys.argv[1])
    mdir = sys.argv[2]
    order = None
    if len(sys.argv) > 3:
        with open(sys.argv[3]) as f:
            order = [l.strip() for l in f if l.strip()]

    # Symbols provided by the other modules in the same set don't need the kernel
    names = sorted(n for n in os.listdir(mdir) if n.endswith(".ko"))
    ok, bad = [], []
    bad_syms = {}
    for n in names:
        vers = module_versions(os.path.join(mdir, n))
        if vers is None:
            continue
        mism = [s for s, c in vers.items() if s in symvers and symvers[s] != c]
        if mism:
            bad.append((n, len(mism), len(vers)))
            for s in mism:
                bad_syms[s] = bad_syms.get(s, 0) + 1
        else:
            ok.append(n)

    print(f"{len(ok)}/{len(ok) + len(bad)} modules have no CRC mismatches against the kernel")
    if order:
        first_bad = [m for m in order if m in {b[0] for b in bad}]
        print(f"modules.load: {len(order) - len(first_bad)}/{len(order)} clean; first failing: {first_bad[:5]}")
    for n, m, t in sorted(bad, key=lambda b: -b[1])[:15]:
        print(f"  {n}: {m}/{t} imported symbols mismatch")
    print("most common mismatched symbols:")
    for s, c in sorted(bad_syms.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {s} (used by {c} modules)")


if __name__ == "__main__":
    main()
