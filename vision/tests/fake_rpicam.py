"""Stand-in for `rpicam-vid --codec yuv420 -o -`: W H N [DELAY] → N I420 frames, then exit.

Frame i has luma 20*i (U = V = 128, gray), so a test can tell frames apart.
"""
import sys
import time

w, h, n = (int(a) for a in sys.argv[1:4])
delay = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
out = sys.stdout.buffer
for i in range(n):
    out.write(bytes([min(20 * i, 255)]) * (w * h) + bytes([128]) * (w * h // 2))
    out.flush()
    time.sleep(delay)
