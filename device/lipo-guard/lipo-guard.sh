#!/system/bin/sh
# LiPo charge guard for a 4.20 V cell on stock Moto firmware (which targets 4.53 V).
# Charging is only allowed between OFF_UV and ON_UV, measured at the battery.
OFF_UV=4150000   # stop charging at/above this (reads high while charging)
ON_UV=4000000    # resume charging at/below this
# Lowest input caps (mW) the driver accepts per charger type
CAPS="dcp_pmax:5000 hvdcp_pmax:7500 pd_pmax:15000"
INTERVAL=10

D=/sys/devices/platform/soc/soc:mmi,discrete-charging
C=/sys/devices/platform/soc/soc:mmi,charger
V=/sys/class/power_supply/battery/voltage_now
LOG=/data/local/tmp/lipo-guard.log
HOLD=/data/adb/lipo-guard.hold   # touch to block charging entirely, rm to resume

log() { echo "$(date '+%F %T') $*" >> $LOG; }

# Only one instance
PIDF=/dev/lipo-guard.pid   # tmpfs, so a stale pid from an earlier boot can never match
if [ -f $PIDF ] && kill -0 "$(cat $PIDF)" 2>/dev/null; then exit 0; fi
echo $$ > $PIDF

while [ ! -e $D/force_charging_disable ]; do sleep 1; done
echo 1 > $D/force_charging_disable
charging=0
log "guard start: charging disabled, window $ON_UV-$OFF_UV uV, caps $CAPS"

while true; do
  for cap in $CAPS; do
    f=${cap%%:*}; w=${cap#*:}
    [ "$(cat $C/$f 2>/dev/null)" = "$w" ] || echo $w > $C/$f 2>/dev/null
  done

  uv=$(cat $V 2>/dev/null)
  case "$uv" in ''|*[!0-9]*) uv=0 ;; esac

  if [ -e $HOLD ]; then
    # Manual hold: never charge while this file exists
    if [ $charging -eq 1 ]; then echo 1 > $D/force_charging_disable; charging=0; log "hold file present: charging disabled"; fi
  elif [ "$uv" -eq 0 ]; then
    # Can't read the cell: fail safe
    if [ $charging -eq 1 ]; then echo 1 > $D/force_charging_disable; charging=0; log "voltage unreadable: charging disabled"; fi
  elif [ $charging -eq 1 ] && [ "$uv" -ge $OFF_UV ]; then
    echo 1 > $D/force_charging_disable; charging=0; log "$uv uV >= $OFF_UV: charging disabled"
  elif [ $charging -eq 0 ] && [ "$uv" -le $ON_UV ]; then
    echo 0 > $D/force_charging_disable; charging=1; log "$uv uV <= $ON_UV: charging enabled"
  fi

  echo "$(date '+%F %T') uv=$uv charging=$charging" > /data/local/tmp/lipo-guard.status
  sleep $INTERVAL
done
