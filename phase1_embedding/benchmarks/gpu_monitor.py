"""
GPU监控模块 - 实时监控GPU显存使用
"""

import time
import logging
import threading
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import json

try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False
    logging.warning("pynvml not available, GPU monitoring disabled")

logger = logging.getLogger(__name__)


@dataclass
class GPUSnapshot:
    """GPU状态快照"""
    timestamp: float
    gpu_id: int
    memory_used_mb: float
    memory_total_mb: float
    memory_percent: float
    gpu_util_percent: float
    temperature: float
    

class GPUMonitor:
    """GPU监控器"""
    
    def __init__(self, gpu_ids: Optional[List[int]] = None, interval: float = 1.0):
        """
        初始化GPU监控器
        
        Args:
            gpu_ids: 要监控的GPU ID列表，None表示监控所有GPU
            interval: 监控间隔（秒）
        """
        self.interval = interval
        self.monitoring = False
        self.snapshots: List[GPUSnapshot] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        
        if not NVML_AVAILABLE:
            logger.warning("NVML not available, GPU monitoring disabled")
            self.enabled = False
            return
        
        try:
            pynvml.nvmlInit()
            self.device_count = pynvml.nvmlDeviceGetCount()
            
            if gpu_ids is None:
                self.gpu_ids = list(range(self.device_count))
            else:
                self.gpu_ids = [gid for gid in gpu_ids if 0 <= gid < self.device_count]
            
            self.handles = []
            for gpu_id in self.gpu_ids:
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                self.handles.append((gpu_id, handle))
            
            self.enabled = True
            logger.info(f"GPU Monitor initialized for GPUs: {self.gpu_ids}")
        except Exception as e:
            logger.error(f"Failed to initialize GPU monitor: {e}")
            self.enabled = False
    
    def get_snapshot(self) -> List[GPUSnapshot]:
        """
        获取当前GPU状态快照
        
        Returns:
            GPU快照列表
        """
        if not self.enabled:
            return []
        
        snapshots = []
        current_time = time.time()
        
        try:
            for gpu_id, handle in self.handles:
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                util_rates = pynvml.nvmlDeviceGetUtilizationRates(handle)
                temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                
                snapshot = GPUSnapshot(
                    timestamp=current_time,
                    gpu_id=gpu_id,
                    memory_used_mb=mem_info.used / 1024**2,
                    memory_total_mb=mem_info.total / 1024**2,
                    memory_percent=(mem_info.used / mem_info.total) * 100,
                    gpu_util_percent=util_rates.gpu,
                    temperature=temperature
                )
                snapshots.append(snapshot)
        except Exception as e:
            logger.error(f"Failed to get GPU snapshot: {e}")
        
        return snapshots
    
    def _monitor_loop(self):
        """监控循环（在后台线程中运行）"""
        while self.monitoring:
            snapshots = self.get_snapshot()
            with self._lock:
                self.snapshots.extend(snapshots)
            time.sleep(self.interval)
    
    def start(self):
        """开始监控"""
        if not self.enabled:
            logger.warning("GPU monitoring not enabled")
            return
        
        if self.monitoring:
            logger.warning("GPU monitoring already running")
            return
        
        self.monitoring = True
        self.snapshots.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("GPU monitoring started")
    
    def stop(self):
        """停止监控"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("GPU monitoring stopped")
    
    def get_snapshots(self) -> List[GPUSnapshot]:
        """
        获取所有采集的快照
        
        Returns:
            快照列表
        """
        with self._lock:
            return self.snapshots.copy()
    
    def get_peak_memory(self) -> Dict[int, float]:
        """
        获取各GPU的峰值显存使用
        
        Returns:
            字典 {gpu_id: peak_memory_mb}
        """
        peak_memory = {}
        with self._lock:
            for snapshot in self.snapshots:
                gpu_id = snapshot.gpu_id
                if gpu_id not in peak_memory:
                    peak_memory[gpu_id] = snapshot.memory_used_mb
                else:
                    peak_memory[gpu_id] = max(peak_memory[gpu_id], snapshot.memory_used_mb)
        return peak_memory
    
    def get_average_memory(self) -> Dict[int, float]:
        """
        获取各GPU的平均显存使用
        
        Returns:
            字典 {gpu_id: avg_memory_mb}
        """
        memory_sum = {}
        memory_count = {}
        
        with self._lock:
            for snapshot in self.snapshots:
                gpu_id = snapshot.gpu_id
                if gpu_id not in memory_sum:
                    memory_sum[gpu_id] = 0
                    memory_count[gpu_id] = 0
                memory_sum[gpu_id] += snapshot.memory_used_mb
                memory_count[gpu_id] += 1
        
        return {
            gpu_id: memory_sum[gpu_id] / memory_count[gpu_id]
            for gpu_id in memory_sum
            if memory_count[gpu_id] > 0
        }
    
    def get_summary(self) -> Dict[str, any]:
        """
        获取监控摘要
        
        Returns:
            摘要字典
        """
        if not self.enabled:
            return {"enabled": False}
        
        peak_memory = self.get_peak_memory()
        avg_memory = self.get_average_memory()
        
        summary = {
            "enabled": True,
            "gpu_ids": self.gpu_ids,
            "num_snapshots": len(self.snapshots),
            "peak_memory_mb": peak_memory,
            "average_memory_mb": avg_memory,
        }
        
        return summary
    
    def export_to_json(self, output_file: str):
        """
        导出监控数据到JSON文件
        
        Args:
            output_file: 输出文件路径
        """
        data = {
            "summary": self.get_summary(),
            "snapshots": [asdict(s) for s in self.get_snapshots()]
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"GPU monitoring data exported to {output_file}")
    
    def __enter__(self):
        """上下文管理器：进入"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器：退出"""
        self.stop()
    
    def __del__(self):
        """析构函数：清理"""
        if hasattr(self, 'enabled') and self.enabled:
            try:
                pynvml.nvmlShutdown()
            except:
                pass


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    monitor = GPUMonitor()
    
    if monitor.enabled:
        print("✓ GPU Monitor initialized")
        print(f"  Monitoring GPUs: {monitor.gpu_ids}")
        
        # 测试快照
        snapshots = monitor.get_snapshot()
        for snapshot in snapshots:
            print(f"\nGPU {snapshot.gpu_id}:")
            print(f"  Memory: {snapshot.memory_used_mb:.0f}/{snapshot.memory_total_mb:.0f} MB ({snapshot.memory_percent:.1f}%)")
            print(f"  Utilization: {snapshot.gpu_util_percent}%")
            print(f"  Temperature: {snapshot.temperature}°C")
        
        # 测试后台监控
        print("\nStarting background monitoring for 5 seconds...")
        with monitor:
            time.sleep(5)
        
        summary = monitor.get_summary()
        print(f"\nMonitoring summary:")
        print(f"  Total snapshots: {summary['num_snapshots']}")
        print(f"  Peak memory: {summary['peak_memory_mb']}")
    else:
        print("✗ GPU Monitor not available")
