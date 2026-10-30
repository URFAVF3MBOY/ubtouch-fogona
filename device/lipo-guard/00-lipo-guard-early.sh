#!/system/bin/sh
# Runs at post-fs-data: turn charging off as early as possible after boot,
# before the service.d guard loop takes over. Backgrounded so boot isn't held.
(
  N=/sys/devices/platform/soc/soc:mmi,discrete-charging/force_charging_disable
  i=0
  while [ ! -e $N ] && [ $i -lt 120 ]; do sleep 0.5; i=$((i+1)); done
  echo 1 > $N
  echo "$(date '+%F %T') early: charging disabled" >> /data/local/tmp/lipo-guard.log
) &
