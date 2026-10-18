"""FPS, inference time, CPU, RAM and SoC temperature, once a second.

cpu_proc is this process in % of one core (as in top: 4 cores = 400%);
cpu_sys is the whole system in % of all cores.
"""
import os
import time

CSV_FIELDS = ["time", "fps", "infer_ms", "cpu_proc", "cpu_sys", "rss_mb", "temp_c",
              "detected", "confidence", "dx", "dy"]
TEMP = "/sys/class/thermal/thermal_zone0/temp"
TICK = os.sysconf("SC_CLK_TCK")


def _proc_ticks():
    with open("/proc/self/stat") as f:
        fields = f.read().rsplit(")", 1)[1].split()
    return int(fields[11]) + int(fields[12])   # utime + stime


def _sys_ticks():
    with open("/proc/stat") as f:
        v = [int(x) for x in f.readline().split()[1:]]
    idle = v[3] + v[4]                          # idle + iowait
    return sum(v) - idle, sum(v)


def _rss_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    return 0.0


def _temp_c():
    try:
        with open(TEMP) as f:
            return int(f.read()) / 1000
    except (OSError, ValueError):
        return None


class PerfMeter:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self._reset()

    def _reset(self):
        self.t0, self.frames, self.infer = self.clock(), 0, 0.0
        self.proc0, (self.busy0, self.total0) = _proc_ticks(), _sys_ticks()

    def frame(self, infer_ms):
        self.frames += 1
        self.infer += infer_ms

    def sample(self):
        dt = self.clock() - self.t0
        if dt < 1.0:
            return None
        busy, total = _sys_ticks()
        s = {
            "fps": self.frames / dt,
            "infer_ms": self.infer / self.frames if self.frames else 0.0,
            "cpu_proc": (_proc_ticks() - self.proc0) / TICK / dt * 100,
            "cpu_sys": (busy - self.busy0) / (total - self.total0) * 100 if total > self.total0 else 0.0,
            "rss_mb": _rss_mb(),
            "temp_c": _temp_c(),
        }
        self._reset()
        return s


def format_line(s, target):
    temp = "-" if s["temp_c"] is None else f"{s['temp_c']:.0f}°C"
    line = (f"fps={s['fps']:.1f} infer={s['infer_ms']:.0f}ms cpu={s['cpu_proc']:.0f}% "
            f"sys={s['cpu_sys']:.0f}% rss={s['rss_mb']:.0f}MB temp={temp} det={int(target.detected)}")
    return line + (f" dx={target.dx:+.2f}".replace("+", "") if target.detected else "")


def csv_row(s, target):
    return [time.strftime("%H:%M:%S"), f"{s['fps']:.2f}", f"{s['infer_ms']:.1f}", f"{s['cpu_proc']:.0f}",
            f"{s['cpu_sys']:.0f}", f"{s['rss_mb']:.0f}", "" if s["temp_c"] is None else f"{s['temp_c']:.1f}",
            int(target.detected), f"{target.confidence:.2f}", f"{target.dx:.3f}", f"{target.dy:.3f}"]
