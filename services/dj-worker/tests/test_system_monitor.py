import asyncio

import types

from app.services.system_monitor import SystemMonitor


class FakePsutil:
    def __init__(self, cpu=10.0, mem=10.0, load=0.0):
        self._cpu = cpu
        self._mem = mem
        self._load = load

    def cpu_percent(self, interval=0.0):  # noqa: ARG002
        return self._cpu

    class _Mem:
        def __init__(self, percent):
            self.percent = percent

    def virtual_memory(self):
        return self._Mem(self._mem)

    def getloadavg(self):
        return (self._load, self._load, self._load)


async def _run_checks(mon: SystemMonitor, n: int):
    for _ in range(n):
        await mon.check_system_health()


def test_health_ok(monkeypatch):
    mon = SystemMonitor()
    fake = FakePsutil(cpu=10.0, mem=20.0, load=0.1)
    monkeypatch.setitem(SystemMonitor.__dict__, "psutil", fake)  # type: ignore[attr-defined]
    # Monkeypatch module attribute resolution
    import app.services.system_monitor as sm
    monkeypatch.setattr(sm, "psutil", fake, raising=True)

    health = asyncio.run(mon.check_system_health())
    assert health.is_healthy is True
    assert mon.is_protection_active() is False


def test_health_trips_protection(monkeypatch):
    mon = SystemMonitor()
    # Make thresholds low to trip quickly
    mon.cpu_critical_threshold = 50.0
    mon.memory_critical_threshold = 50.0
    mon.load_critical_threshold = 1.0
    mon._max_consecutive_unhealthy = 2

    fake = FakePsutil(cpu=99.0, mem=99.0, load=10.0)
    import app.services.system_monitor as sm
    monkeypatch.setattr(sm, "psutil", fake, raising=True)

    # Two unhealthy checks should activate protection
    asyncio.run(_run_checks(mon, 2))
    assert mon.is_protection_active() is True

