"""
Platinum Tier Health Monitor & Self-Healing System
Monitors system health and automatically restarts MCP services when needed
"""
import psutil
import time
import json
import threading
import subprocess
import os
import signal
from datetime import datetime, timedelta
from pathlib import Path
from audit_logger import audit_logger


class HealthMonitor:
    def __init__(self, check_interval=60, log_dir="vault/Logs"):
        """
        Initialize the Health Monitor

        Args:
            check_interval: Time in seconds between health checks
            log_dir: Directory to store health logs
        """
        self.check_interval = check_interval
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.running = False
        self.monitor_thread = None

        # MCP process tracking
        self.mcp_processes = {}
        self.last_scheduler_run = datetime.now()
        self.alerts = []

        # Health thresholds
        self.cpu_threshold = 90
        self.memory_threshold = 90
        self.disk_threshold = 90
        self.scheduler_timeout = timedelta(minutes=15)  # 15 minutes

    def get_system_health(self):
        """
        Get current system health metrics

        Returns:
            Dict containing system health metrics
        """
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else psutil.disk_usage('.').percent,
            "timestamp": datetime.now().isoformat(),
            "processes_count": len(psutil.pids()),
            "load_average": [x for x in os.getloadavg()] if hasattr(os, 'getloadavg') else [0, 0, 0]
        }

    def check_system_health(self):
        """
        Check system health and log warnings if thresholds are exceeded

        Returns:
            List of health issues detected
        """
        issues = []
        health_data = self.get_system_health()

        # Check CPU usage
        if health_data["cpu_percent"] > self.cpu_threshold:
            issue = {
                "type": "cpu_high",
                "message": f"High CPU usage: {health_data['cpu_percent']}%",
                "severity": "warning",
                "timestamp": health_data["timestamp"]
            }
            issues.append(issue)
            print(f"[WARNING] High CPU usage: {issue['message']}")

        # Check memory usage
        if health_data["memory_percent"] > self.memory_threshold:
            issue = {
                "type": "memory_high",
                "message": f"High memory usage: {health_data['memory_percent']}%",
                "severity": "warning",
                "timestamp": health_data["timestamp"]
            }
            issues.append(issue)
            print(f"[WARNING] High memory usage: {issue['message']}")

        # Check disk usage
        if health_data["disk_percent"] > self.disk_threshold:
            issue = {
                "type": "disk_high",
                "message": f"High disk usage: {health_data['disk_percent']}%",
                "severity": "warning",
                "timestamp": health_data["timestamp"]
            }
            issues.append(issue)
            print(f"[WARNING] High disk usage: {issue['message']}")

        # Check scheduler status and avoid duplicate alerts
        time_since_last_run = datetime.now() - self.last_scheduler_run
        if time_since_last_run > self.scheduler_timeout:
            # Check if we've already logged this specific scheduler issue recently to avoid spam
            recent_alerts = self.get_recent_alerts()
            scheduler_inactive_recently_logged = False

            # Check if a similar scheduler inactive alert was logged in the last 5 minutes
            for alert in recent_alerts[-5:]:  # Check last 5 alerts
                if (alert.get('type') == 'scheduler_inactive' and
                    datetime.fromisoformat(alert.get('timestamp')) > datetime.now() - timedelta(minutes=5)):
                    scheduler_inactive_recently_logged = True
                    break

            if not scheduler_inactive_recently_logged:
                issue = {
                    "type": "scheduler_inactive",
                    "message": f"Scheduler has been inactive for {(time_since_last_run).seconds // 60} minutes",
                    "severity": "alert",
                    "timestamp": health_data["timestamp"]
                }
                issues.append(issue)
                print(f"[ALERT] {issue['message']}")

        # Log issues
        for issue in issues:
            self.log_alert(issue)

        return issues

    def log_alert(self, alert):
        """
        Log an alert to the health log file
        """
        health_log_file = self.log_dir / "health_alerts.json"

        # Read existing alerts or create new list
        if health_log_file.exists():
            with open(health_log_file, 'r') as f:
                try:
                    alerts = json.load(f)
                except json.JSONDecodeError:
                    alerts = []
        else:
            alerts = []

        # Add new alert
        alerts.append(alert)

        # Keep only last 100 alerts
        alerts = alerts[-100:]

        # Write back to file
        with open(health_log_file, 'w') as f:
            json.dump(alerts, f, indent=2)

        # Also log to comprehensive audit log
        audit_logger.log_error(
            action_type=f"system_{alert['type']}",
            error=alert['message'],
            details=alert
        )

    def get_recent_alerts(self):
        """
        Get recent alerts from the health log
        """
        health_log_file = self.log_dir / "health_alerts.json"

        if health_log_file.exists():
            with open(health_log_file, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def check_mcp_processes(self):
        """
        Check if MCP processes are running and restart if needed
        """
        # This is a simplified version - in a real implementation you'd track actual processes
        # For now, we'll simulate checking for odoo_mcp.py and social_mcp.py
        issues = []

        # Check if processes exist in tracking (in a real system, this would check actual PIDs)
        for mcp_name, proc_info in self.mcp_processes.items():
            if not proc_info.get('running', True):
                issue = {
                    "type": "mcp_crashed",
                    "message": f"MCP process {mcp_name} has crashed",
                    "severity": "critical",
                    "timestamp": datetime.now().isoformat()
                }
                issues.append(issue)
                print(f"[CRITICAL] {issue['message']}")

                # Trigger self-healing by restarting the process
                self.restart_mcp_process(mcp_name)

        return issues

    def restart_mcp_process(self, mcp_name):
        """
        Restart a crashed MCP process
        """
        print(f"Attempting to restart {mcp_name}...")

        try:
            if mcp_name == "odoo_mcp":
                # Restart odoo_mcp process
                cmd = ["python", "odoo_mcp.py", "--host", "localhost", "--port", "8080"]
                proc = subprocess.Popen(cmd)
                self.mcp_processes[mcp_name] = {
                    "process": proc,
                    "running": True,
                    "restart_count": self.mcp_processes.get(mcp_name, {}).get("restart_count", 0) + 1
                }
                print(f"✅ Successfully restarted {mcp_name}")

            elif mcp_name == "social_mcp":
                # Restart social_mcp process
                cmd = ["python", "social_mcp.py"]
                proc = subprocess.Popen(cmd)
                self.mcp_processes[mcp_name] = {
                    "process": proc,
                    "running": True,
                    "restart_count": self.mcp_processes.get(mcp_name, {}).get("restart_count", 0) + 1
                }
                print(f"✅ Successfully restarted {mcp_name}")

        except Exception as e:
            print(f"❌ Failed to restart {mcp_name}: {e}")
            self.log_alert({
                "type": "restart_failed",
                "message": f"Failed to restart {mcp_name}: {e}",
                "severity": "critical",
                "timestamp": datetime.now().isoformat()
            })

    def start_monitoring(self):
        """
        Start the health monitoring loop in a separate thread
        """
        if self.running:
            print("Health monitor is already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("Health monitor started")

    def stop_monitoring(self):
        """
        Stop the health monitoring
        """
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("Health monitor stopped")

    def _monitor_loop(self):
        """
        Internal monitoring loop that runs continuously
        """
        print("Health monitoring loop started...")
        while self.running:
            try:
                # Perform health checks
                health_issues = self.check_system_health()

                # Check MCP processes
                mcp_issues = self.check_mcp_processes()

                # Combine issues
                all_issues = health_issues + mcp_issues

                # Update alerts list
                self.alerts = self.get_recent_alerts()

                # Wait for next check
                time.sleep(self.check_interval)

            except Exception as e:
                print(f"Error in health monitor: {e}")
                time.sleep(self.check_interval)

    def simulate_high_cpu(self, duration=30):
        """
        Simulate high CPU usage for testing purposes
        """
        print(f"Simulating high CPU usage for {duration} seconds...")

        def cpu_intensive_task():
            start_time = time.time()
            while time.time() - start_time < duration:
                # Perform CPU-intensive calculations
                _ = [x**2 for x in range(10000)]

        cpu_thread = threading.Thread(target=cpu_intensive_task)
        cpu_thread.start()
        return cpu_thread

    def update_scheduler_timestamp(self):
        """
        Update the timestamp of the last scheduler run
        """
        self.last_scheduler_run = datetime.now()

    def get_health_summary(self):
        """
        Get a summary of the current health status
        """
        health_data = self.get_system_health()
        recent_alerts = self.get_recent_alerts()

        return {
            "current_health": health_data,
            "recent_alerts": recent_alerts[-10:],  # Last 10 alerts
            "total_alerts_count": len(recent_alerts),
            "is_system_healthy": len([a for a in recent_alerts if a.get('severity') in ['alert', 'critical']]) == 0
        }


# Example usage and testing
if __name__ == "__main__":
    print("Starting Health Monitor...")

    # Create health monitor instance
    health_monitor = HealthMonitor(check_interval=10)  # Check every 10 seconds for testing

    # Start monitoring
    health_monitor.start_monitoring()

    # Wait and then simulate high CPU
    print("Waiting 10 seconds before simulating high CPU...")
    time.sleep(10)

    print("Starting CPU simulation...")
    cpu_thread = health_monitor.simulate_high_cpu(duration=20)

    # Wait for simulation to complete
    cpu_thread.join()

    print("CPU simulation completed.")
    print("Health monitor will continue running. Press Ctrl+C to stop.")

    try:
        # Keep the monitor running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping health monitor...")
        health_monitor.stop_monitoring()
        print("Health monitor stopped.")