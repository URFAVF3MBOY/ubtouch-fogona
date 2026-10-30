#!/usr/bin/env python3
"""Run shell commands on the Halium initrd's debug telnet (192.168.2.15:23).

usage: telnet_run.py "<commands>" [timeout_s]

Minimal telnet: refuses every option negotiation and strips IAC sequences,
which is enough for busybox telnetd.
"""
import socket
import sys
import time

HOST, PORT = "10.15.19.82", 23
IAC, DONT, DO, WONT, WILL, SB, SE = 255, 254, 253, 252, 251, 250, 240


def clean(data, sock):
    out, i = bytearray(), 0
    while i < len(data):
        b = data[i]
        if b == IAC and i + 1 < len(data):
            cmd = data[i + 1]
            if cmd in (DO, DONT, WILL, WONT) and i + 2 < len(data):
                opt = data[i + 2]
                sock.sendall(bytes([IAC, WONT if cmd in (DO, DONT) else DONT, opt]))
                i += 3
                continue
            if cmd == SB:
                end = data.find(bytes([IAC, SE]), i)
                i = len(data) if end < 0 else end + 2
                continue
            i += 2
            continue
        out.append(b)
        i += 1
    return bytes(out)


def main():
    cmds = sys.argv[1]
    if cmds.startswith("@"):  # @file: send the file's lines (for long input)
        cmds = open(cmds[1:], encoding="utf-8").read().rstrip("\n")
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 20
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.settimeout(1)
    marker = "__DONE_%d__" % int(time.time())
    time.sleep(1)
    s.sendall((cmds + "\necho " + marker + "\n").encode())
    buf, end = b"", time.time() + timeout
    while time.time() < end:
        try:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += clean(chunk, s)
            if buf.count(marker.encode()) >= 2:
                break
        except socket.timeout:
            pass
    sys.stdout.write(buf.decode("utf-8", "replace"))
    s.close()


if __name__ == "__main__":
    main()
