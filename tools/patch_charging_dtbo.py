#!/usr/bin/env python3
"""Cap every charge-voltage setting in the fogona DTBO overlays at CAP_MV.

The phone runs on a 4.20 V-max LiPo instead of the stock 4.45 V+ pack. Stock
values target 4.50-4.53 V. Edits each overlay .dtb in place with fdtput.

usage: patch_charging_dtbo.py dir_with_entryNN.dtb [cap_mv]
"""
import glob
import os
import subprocess
import sys

CAP_MV = int(sys.argv[2]) if len(sys.argv) > 2 else 4200


def fdt(*args):
    return subprocess.run(["fdt" + args[0], *args[1:]], check=True,
                          capture_output=True, text=True).stdout.split()


def find_node(dtb, name):
    for frag in fdt("get", "-l", dtb, "/"):
        path = f"/{frag}/__overlay__"
        try:
            if name in fdt("get", "-l", dtb, path):
                return f"{path}/{name}"
        except subprocess.CalledProcessError:
            pass
    sys.exit(f"{dtb}: node {name} not found")


def get_u32(dtb, node, prop):
    return [int(x) for x in fdt("get", "-tu", dtb, node, prop)]


def set_u32(dtb, node, prop, vals):
    fdt("put", "-tu", dtb, node, prop, *map(str, vals))


def cap(dtb, node, prop, scale=1, stride=None, index=None):
    vals = get_u32(dtb, node, prop)
    new = list(vals)
    for i, v in enumerate(vals):
        if stride is not None and i % stride != index:
            continue
        if v > CAP_MV * scale:
            new[i] = CAP_MV * scale
    if new != vals:
        set_u32(dtb, node, prop, new)
    print(f"  {prop}: {vals} -> {new}")


def patch(dtb):
    print(dtb)
    dc = find_node(dtb, "mmi,discrete-charging")
    for p in ("mmi,max-fv-mv", "mmi,batt-profile-fv-mv", "mmi,dcp-noneffc-cv"):
        cap(dtb, dc, p)
    # zones are <temp_c fv_mv fcc_max fcc_norm> tuples; cap the fv column
    cap(dtb, dc, "mmi,mmi-temp-zones", stride=4, index=1)
    cap(dtb, dc, "mmi,mmi-ffc-zones", stride=4, index=1)
    try:
        fdt("put", "-d", dtb, dc, "mmi,enable-10w-ffc")
        print("  removed mmi,enable-10w-ffc")
    except subprocess.CalledProcessError:
        pass

    bq = find_node(dtb, "bq25890@6A")
    cap(dtb, bq, "ti,bq2589x,charge-voltage")

    sgm = find_node(dtb, "sgm4154x@3B")  # values in uV
    for p in ("jeita_temp_t3_to_t4_cv", "jeita_temp_t2_to_t3_cv", "jeita_temp_t1_to_t2_cv"):
        cap(dtb, sgm, p, scale=1000)


if __name__ == "__main__":
    for f in sorted(glob.glob(os.path.join(sys.argv[1], "entry*.dtb"))):
        patch(f)
