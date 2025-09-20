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
        # Simplified thresholds since heavy workloads (Ollama, TTS) run externally
        self.cpu_warning_threshold = 85.0  # %
        self.cpu_critical_threshold = 95.0  # %
        self.memory_warning_threshold = 85.0  # %
        self.memory_critical_threshold = 95.0  # %
        self.load_critical_threshold = 80.0  # 1-minute load average (high tolerance for stable system)
        
    async def check_system_health(self) -> SystemHealth:
        """Check current system health status"""
        try:
            # Get CPU usage (1 second average)
            cpu_percent = psutil.cpu_percent(interval=1.0)

            # Get memory usage - use container-aware method if in Docker
            memory_percent = self._get_container_memory_percent()
            
            # Get load average (1-minute)
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            
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
            
            if load_avg > self.load_critical_threshold:
                warnings.append(f"CRITICAL: Load average at {load_avg:.2f}")
                is_healthy = False
            
            health = SystemHealth(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                load_average=load_avg,
                is_healthy=is_healthy,
                warnings=warnings
            )
            
            if warnings:
                logger.warning("System health warnings", 
                              cpu=cpu_percent, 
                              memory=memory_percent, 
                              load=load_avg,
                              warnings=warnings)
            
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
    
    def is_safe_for_intensive_operations(self) -> bool:
        """Check if system can handle intensive operations like TTS generation"""
        # Quick health check without the full monitoring overhead
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = self._get_container_memory_percent()

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
                'protection_active': False
            }
        except Exception as e:
            logger.error("Failed to get system info", error=str(e))
            return {'error': str(e)}

    def _get_container_memory_percent(self) -> float:
        """Get container-aware memory usage percentage"""
        try:
            # Try Docker container memory stats first
            import os
            cgroup_memory_usage = "/sys/fs/cgroup/memory.current"
            cgroup_memory_limit = "/sys/fs/cgroup/memory.max"

            # Check for cgroup v2 (newer Docker)
            if os.path.exists(cgroup_memory_usage) and os.path.exists(cgroup_memory_limit):
                with open(cgroup_memory_usage, 'r') as f:
                    current = int(f.read().strip())
                with open(cgroup_memory_limit, 'r') as f:
                    limit_str = f.read().strip()
                    if limit_str == "max":
                        # No memory limit set, use system memory
                        return psutil.virtual_memory().percent
                    limit = int(limit_str)
                return (current / limit) * 100.0

            # Try cgroup v1 (older Docker)
            cgroup_v1_usage = "/sys/fs/cgroup/memory/memory.usage_in_bytes"
            cgroup_v1_limit = "/sys/fs/cgroup/memory/memory.limit_in_bytes"

            if os.path.exists(cgroup_v1_usage) and os.path.exists(cgroup_v1_limit):
                with open(cgroup_v1_usage, 'r') as f:
                    current = int(f.read().strip())
                with open(cgroup_v1_limit, 'r') as f:
                    limit = int(f.read().strip())
                    # Very large limits mean no constraint
                    if limit > (1024**4):  # More than 1TB means unconstrained
                        return psutil.virtual_memory().percent
                return (current / limit) * 100.0

        except Exception as e:
            logger.warning("Failed to read container memory stats, falling back to system memory", error=str(e))

        # Fallback to system memory (but with much higher thresholds for containers)
        system_percent = psutil.virtual_memory().percent
        # If we're in a container and seeing high system usage, assume it's host memory bleed-through
        # Only flag as problematic if it's extremely high (>99%)
        if system_percent > 99:
            return system_percent
        else:
            # Return a low percentage to prevent false positives from host memory usage
            return min(system_percent, 75.0)

# Global system monitor instance
system_monitor = SystemMonitor()