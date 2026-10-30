#!/bin/bash
# Build a list of out-of-tree module dirs against an already built kernel.
#
# usage: build_ext_modules.sh <kernel src> <kernel out> <repo root> <list file> <dist dir>
#
# Pass 1 builds everything with undefined symbols allowed, so modules that
# depend on each other don't need a hand-written order. Pass 2 relinks with
# every pass-1 Module.symvers as KBUILD_EXTRA_SYMBOLS, giving correct CRCs.
# Failures are collected rather than stopping the run.
set -u
KSRC=$(realpath "$1"); KOUT=$(realpath "$2"); ROOT=$(realpath "$3"); LIST=$4; DIST=$(realpath -m "$5")
mkdir -p "$DIST"
MAKEARGS=(-C "$KSRC" O="$KOUT" ARCH=arm64 LLVM=1 LLVM_IAS=1 CC="ccache clang" -j"$(nproc)")

mapfile -t ENTRIES < <(grep -vE '^\s*(#|$)' "$LIST")

build() {  # pass extra_symbols
  local pass=$1 extra=$2 failed=()
  for e in "${ENTRIES[@]}"; do
    e=${e//@KSRC@/$KSRC}; e=${e//@TOP@/${ANDROID_BUILD_TOP:-}}
    read -r dir opts <<< "$e"
    local log="$DIST/logs/${dir//\//_}.pass$pass.log"
    mkdir -p "$DIST/logs"
    # A module's own pass-1 Module.symvers as an extra symbol file makes kbuild
    # see a circular dependency and silently skip the build.
    local own="$ROOT/$dir/Module.symvers" syms=""
    for f in $extra; do [ "$f" = "$own" ] || syms+="$f "; done
    # shellcheck disable=SC2086
    if make "${MAKEARGS[@]}" M="$ROOT/$dir" modules KBUILD_MODPOST_WARN=$([ "$pass" = 1 ] && echo 1) \
         KBUILD_EXTRA_SYMBOLS="$syms" $opts > "$log" 2>&1; then
      echo "ok    $dir"
    else
      echo "FAIL  $dir"; failed+=("$dir")
      grep -E 'error:|Error [0-9]|undefined!' "$log" | head -8 | sed 's/^/        /'
    fi
  done
  FAILED=("${failed[@]+"${failed[@]}"}")
}

echo "== pass 1"
build 1 ""
SYMVERS=$(find "$ROOT" -name Module.symvers -printf '%p ' 2>/dev/null)
echo "== pass 2"
build 2 "$SYMVERS"

find "$ROOT" -name '*.ko' -exec cp {} "$DIST/" \;
echo "built $(ls "$DIST"/*.ko 2>/dev/null | wc -l) modules; ${#FAILED[@]} dirs failed: ${FAILED[*]-}"
printf '%s\n' "${FAILED[@]+"${FAILED[@]}"}" > "$DIST/failed.txt"
