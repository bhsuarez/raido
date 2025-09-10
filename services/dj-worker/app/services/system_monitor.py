"""
System monitoring and health check service to prevent resource exhaustion.
"""

import psutil
import asyncio
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = structlog.get_logger()

@dataclass
class SystemHealth:
    cpu_percent: float
    memory_percent: float
    load_average: float
    is_healthy: bool
    warnings: list[str]

class SystemMonitor:
    """Monitor system resources and prevent resource exhaustion"""
    
    def __init__(self):
        # Thresholds for health checks
        self.cpu_warning_threshold = 80.0  # %
        self.cpu_critical_threshold = 95.0  # %
        self.memory_warning_threshold = 80.0  # %
        self.memory_critical_threshold = 95.0  # %
        # Load thresholds are evaluated per CPU core to avoid false positives
        # in containerized environments where raw loadavg can be misleading.
        self.load_per_core_warning_threshold = 1.0   # warning when > 1 runnable per core
        self.load_per_core_critical_threshold = 1.5  # critical when sustained > 1.5/core
        
        # Circuit breaker for system protection
        self._consecutive_unhealthy_checks = 0
        self._max_consecutive_unhealthy = 5
        self._system_protection_active = False
        self._protection_end_time = None
        self._protection_duration = 300  # 5 minutes
        
    async def check_system_health(self) -> SystemHealth:
        """Check current system health status"""
        try:
            # Get CPU usage (1 second average)
            cpu_percent = psutil.cpu_percent(interval=1.0)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Get load average (1-minute) and normalize per core
            raw_load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            cpu_count = psutil.cpu_count() or 1
            load_avg_per_core = raw_load_avg / max(1, cpu_count)
            
            # Evaluate health
            warnings = []
            is_healthy = True
            
            if cpu_percent > self.cpu_critical_threshold:
                warnings.append(f"CRITICAL: CPU usage at {cpu_percent:.1f}%")
                is_healthy = False
            elif cpu_percent > self.cpu_warning_threshold:
                warnings.append(f"WARNING: CPU usage at {cpu_percent:.1f}%")
            
            if memory_percent > self.memory_critical_threshold:
                warnings.append(f"CRITICAL: Memory usage at {memory_percent:.1f}%")
                is_healthy = False
            elif memory_percent > self.memory_warning_threshold:
                warnings.append(f"WARNING: Memory usage at {memory_percent:.1f}%")
            
            # Load-based gating: only consider load as CRITICAL if it's high per core
            # AND we also see pressure on CPU or memory. This avoids tripping purely
            # on inflated load in some LXC/docker environments where CPU is idle.
            if load_avg_per_core > self.load_per_core_critical_threshold and (
                cpu_percent > self.cpu_warning_threshold or memory_percent > self.memory_warning_threshold
            ):
                warnings.append(
                    f"CRITICAL: Load/core {load_avg_per_core:.2f} (raw {raw_load_avg:.2f} on {cpu_count} cores)"
                )
                is_healthy = False
            elif load_avg_per_core > self.load_per_core_warning_threshold:
                warnings.append(
                    f"WARNING: Load/core {load_avg_per_core:.2f} (raw {raw_load_avg:.2f} on {cpu_count} cores)"
                )
            
            # Update protection state
            if not is_healthy:
                self._consecutive_unhealthy_checks += 1
                if self._consecutive_unhealthy_checks >= self._max_consecutive_unhealthy:
                    self._activate_system_protection()
            else:
                self._consecutive_unhealthy_checks = 0
                self._deactivate_system_protection()
            
            health = SystemHealth(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                load_average=raw_load_avg,
                is_healthy=is_healthy and not self.is_protection_active(),
                warnings=warnings
            )
            
            if warnings:
                logger.warning(
                    "System health warnings",
                    cpu=cpu_percent,
                    memory=memory_percent,
                    load_raw=raw_load_avg,
                    load_per_core=load_avg_per_core,
                    warnings=warnings,
                )
            
            return health
            
        except Exception as e:
            logger.error("Failed to check system health", error=str(e))
            return SystemHealth(
                cpu_percent=0.0,
                memory_percent=0.0,
                load_average=0.0,
                is_healthy=False,
                warnings=[f"Health check failed: {str(e)}"]
            )
    
    def _activate_system_protection(self):
        """Activate system protection mode"""
        if not self._system_protection_active:
            self._system_protection_active = True
            self._protection_end_time = datetime.now() + timedelta(seconds=self._protection_duration)
            logger.error("SYSTEM PROTECTION ACTIVATED - High resource usage detected",
                        duration_minutes=self._protection_duration // 60,
                        consecutive_failures=self._consecutive_unhealthy_checks)
    
    def _deactivate_system_protection(self):
        """Deactivate system protection if timeout reached"""
        if self._system_protection_active:
            if self._protection_end_time and datetime.now() >= self._protection_end_time:
                self._system_protection_active = False
                self._protection_end_time = None
                logger.info("System protection deactivated - system health restored")
    
    def is_protection_active(self) -> bool:
        """Check if system protection is currently active"""
        if self._system_protection_active:
            self._deactivate_system_protection()  # Check if we should deactivate
        return self._system_protection_active
    
    def is_safe_for_intensive_operations(self) -> bool:
        """Check if system can handle intensive operations like TTS generation"""
        if self.is_protection_active():
            return False
        
        # Quick health check without the full monitoring overhead
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            
            return (cpu_percent < self.cpu_warning_threshold and 
                   memory_percent < self.memory_warning_threshold)
        except Exception:
            return False
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu': {
                    'count': cpu_count,
                    'percent': psutil.cpu_percent(interval=1.0),
                    'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
                },
                'memory': {
                    'total_gb': memory.total / (1024**3),
                    'available_gb': memory.available / (1024**3),
                    'percent': memory.percent
                },
                'disk': {
                    'total_gb': disk.total / (1024**3),
                    'free_gb': disk.free / (1024**3),
                    'percent': (disk.used / disk.total) * 100
                },
                'protection_active': self.is_protection_active()
            }
        except Exception as e:
            logger.error("Failed to get system info", error=str(e))
            return {'error': str(e)}

# Global system monitor instance
system_monitor = SystemMonitor()
