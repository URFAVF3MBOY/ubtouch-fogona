#!/bin/bash
# Flash the Ubuntu Touch images to slot A of a moto g play 2024 (fogona).
#
# usage: flash-ut.sh <dir with boot.img init_boot.img system.img>
#
# Touches boot_a, init_boot_a, system_a (and deletes product_a/system_ext_a to
# make room in super), and FORMATS userdata. vendor*, vendor_boot, dtbo stay.
# Prints "STEP ..." / "PCT nn" lines for progress.
set -u
D=$1
step() { echo "STEP $*"; }
die() { echo "ABORT $*"; exit 1; }

for f in boot.img init_boot.img system.img; do [ -f "$D/$f" ] || die "missing $D/$f"; done

wait_fastboot() {
  for _ in $(seq 1 150); do fastboot devices 2>/dev/null | grep -q fastboot && return 0; sleep 2; done
  die "no fastboot device"
}
userspace() { fastboot getvar is-userspace 2>&1 | grep -q "is-userspace: yes"; }

step "waiting for phone (adb or fastboot)"
for _ in $(seq 1 300); do
  fastboot devices 2>/dev/null | grep -q fastboot && break
  adb devices 2>/dev/null | grep -qw "device$" && { adb reboot bootloader; sleep 8; }
  sleep 2
done
wait_fastboot
userspace && { fastboot reboot bootloader >/dev/null 2>&1; sleep 5; wait_fastboot; }

prod=$(fastboot getvar product 2>&1 | awk '/product:/{print $2}')
slot=$(fastboot getvar current-slot 2>&1 | awk '/current-slot:/{print $2}')
[ "$prod" = fogona ] || die "unexpected product '$prod'"
[ "$slot" = a ] || die "current slot is '$slot', expected a"
step "bootloader: fogona, slot a"

step "flashing boot_a (Halium kernel)"
fastboot flash boot_a "$D/boot.img" 2>&1 | grep -E "OKAY|FAILED|error" || true
step "flashing init_boot_a (Halium ramdisk)"
fastboot flash init_boot_a "$D/init_boot.img" 2>&1 | grep -E "OKAY|FAILED|error" || true

step "rebooting to fastbootd"
fastboot reboot fastboot >/dev/null 2>&1
sleep 10; wait_fastboot
for _ in $(seq 1 30); do userspace && break; sleep 2; done
userspace || die "phone did not enter fastbootd"
step "in fastbootd"

for p in product_a system_ext_a; do
  step "deleting $p"
  fastboot delete-logical-partition "$p" 2>&1 | grep -E "OKAY|FAILED" || true
done
for p in $(fastboot getvar all 2>&1 | grep -oE "partition-size:[a-z_]+_a-cow" | cut -d: -f2); do
  step "deleting snapshot $p"; fastboot delete-logical-partition "$p" 2>&1 | grep -E "OKAY|FAILED" || true
done

step "flashing system_a (Ubuntu Touch, ~3.5 GB)"
fastboot flash system_a "$D/system.img" 2>&1 | while IFS= read -r line; do
  if [[ $line =~ Sending\ sparse\ \'system_a\'\ ([0-9]+)/([0-9]+) ]]; then
    echo "PCT $(( 100 * ${BASH_REMATCH[1]} / ${BASH_REMATCH[2]} )) (${BASH_REMATCH[1]}/${BASH_REMATCH[2]} chunks)"
  elif [[ $line =~ FAILED|error|Invalid ]]; then
    echo "ERROR $line"
  elif [[ $line =~ Resizing|Finished ]]; then
    echo "STEP $line"
  fi
done

step "formatting userdata (ext4) and erasing metadata"
fastboot format:ext4 userdata 2>&1 | grep -E "OKAY|FAILED|error" || true
fastboot erase metadata 2>&1 | grep -E "OKAY|FAILED|error" || true

step "rebooting into Ubuntu Touch"
fastboot reboot >/dev/null 2>&1
echo "DONE"
