"""
Platinum Tier Self-Healing Manager
Monitors and automatically restarts MCP services when they crash
"""
import subprocess
import time
import psutil
import threading
from pathlib import Path
from datetime import datetime
from health_monitor import HealthMonitor
from audit_logger import audit_logger


class SelfHealingManager:
    def __init__(self, check_interval=30):
        """
        Initialize the Self-Healing Manager

        Args:
            check_interval: Time in seconds between process health checks
        """
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread = None

        # MCP process tracking
        self.mcp_processes = {
            "odoo_mcp": {
                "name": "odoo_mcp",
                "command": ["python", "odoo_mcp.py", "--host", "localhost", "--port", "8080"],
                "process": None,
                "restart_count": 0,
                "last_restart": None,
                "healthy": False
            },
            "social_mcp": {
                "name": "social_mcp",
                "command": ["python", "social_mcp.py"],
                "process": None,
                "restart_count": 0,
                "last_restart": None,
                "healthy": False
            }
        }

        # Initialize health monitor
        self.health_monitor = HealthMonitor(check_interval=60)

    def start_monitoring(self):
        """
        Start the self-healing monitoring in a separate thread
        """
        if self.running:
            print("Self-healing manager is already running")
            return

        # Start the health monitor
        self.health_monitor.start_monitoring()

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("Self-healing manager started")

    def stop_monitoring(self):
        """
        Stop the self-healing monitoring
        """
        self.running = False
        if self.health_monitor:
            self.health_monitor.stop_monitoring()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("Self-healing manager stopped")

    def _monitor_loop(self):
        """
        Internal monitoring loop that runs continuously
        """
        print("Self-healing monitoring loop started...")
        while self.running:
            try:
                # Check MCP processes
                self._check_mcp_processes()

                # Wait for next check
                time.sleep(self.check_interval)

            except Exception as e:
                print(f"Error in self-healing monitor: {e}")
                time.sleep(self.check_interval)

    def _check_mcp_processes(self):
        """
        Check if MCP processes are running and restart if needed
        """
        for mcp_name, mcp_info in self.mcp_processes.items():
            try:
                # Check if process is running
                process = mcp_info["process"]

                if process and process.poll() is None:
                    # Process is running, update healthy status
                    mcp_info["healthy"] = True
                    continue
                else:
                    # Process is not running, restart it
                    print(f"⚠️  {mcp_name} is not running. Attempting restart...")

                    # Log the crash
                    crash_alert = {
                        "type": "mcp_crashed",
                        "message": f"MCP process {mcp_name} has crashed",
                        "severity": "critical",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.health_monitor.log_alert(crash_alert)

                    # Try to restart the process
                    restart_success = self._restart_mcp_process(mcp_name)

                    if restart_success:
                        restart_alert = {
                            "type": "mcp_restarted",
                            "message": f"Successfully restarted MCP process {mcp_name}",
                            "severity": "info",
                            "timestamp": datetime.now().isoformat()
                        }
                        self.health_monitor.log_alert(restart_alert)

                        # Update process info
                        self.mcp_processes[mcp_name]["restart_count"] += 1
                        self.mcp_processes[mcp_name]["last_restart"] = datetime.now()
                        self.mcp_processes[mcp_name]["healthy"] = True

                        print(f"✅ {mcp_name} restarted successfully")
                    else:
                        restart_alert = {
                            "type": "mcp_restart_failed",
                            "message": f"Failed to restart MCP process {mcp_name}",
                            "severity": "critical",
                            "timestamp": datetime.now().isoformat()
                        }
                        self.health_monitor.log_alert(restart_alert)

                        print(f"❌ Failed to restart {mcp_name}")

            except Exception as e:
                print(f"Error checking {mcp_name}: {e}")
                error_alert = {
                    "type": "mcp_check_error",
                    "message": f"Error checking {mcp_name}: {e}",
                    "severity": "error",
                    "timestamp": datetime.now().isoformat()
                }
                self.health_monitor.log_alert(error_alert)

    def _restart_mcp_process(self, mcp_name):
        """
        Restart a specific MCP process

        Args:
            mcp_name: Name of the MCP process to restart

        Returns:
            Boolean indicating success of restart
        """
        try:
            mcp_info = self.mcp_processes[mcp_name]
            command = mcp_info["command"]

            print(f"Attempting to restart {mcp_name} with command: {' '.join(command)}")

            # Start the process
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait a moment to see if it stays running
            time.sleep(2)

            # Check if the process is still running
            if process.poll() is None:
                # Process is running, update the process reference
                self.mcp_processes[mcp_name]["process"] = process
                return True
            else:
                # Process crashed immediately, get the error
                stderr, stdout = process.communicate()
                print(f"Process {mcp_name} crashed immediately: {stderr}")
                return False

        except Exception as e:
            print(f"Error restarting {mcp_name}: {e}")
            return False

    def get_status(self):
        """
        Get the current status of all monitored processes

        Returns:
            Dict containing status information for all processes
        """
        status = {}
        for mcp_name, mcp_info in self.mcp_processes.items():
            process = mcp_info["process"]
            is_running = process and process.poll() is None if process else False

            status[mcp_name] = {
                "name": mcp_info["name"],
                "running": is_running,
                "healthy": mcp_info["healthy"],
                "restart_count": mcp_info["restart_count"],
                "last_restart": mcp_info["last_restart"].isoformat() if mcp_info["last_restart"] else None
            }

        return status

    def force_restart(self, mcp_name):
        """
        Force restart a specific MCP process

        Args:
            mcp_name: Name of the MCP process to restart

        Returns:
            Boolean indicating success of restart
        """
        if mcp_name not in self.mcp_processes:
            print(f"Unknown MCP: {mcp_name}")
            return False

        # Kill the process if it's running
        process = self.mcp_processes[mcp_name]["process"]
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception:
                pass  # Process might already be dead

        # Restart the process
        return self._restart_mcp_process(mcp_name)


# Example usage and testing
if __name__ == "__main__":
    print("Starting Self-Healing Manager...")

    # Create self-healing manager instance
    healing_manager = SelfHealingManager(check_interval=10)  # Check every 10 seconds for testing

    # Start monitoring
    healing_manager.start_monitoring()

    print("Self-healing manager is now monitoring MCP processes.")
    print("Current status:", healing_manager.get_status())

    print("Manager will continue running. Press Ctrl+C to stop.")

    try:
        # Keep the manager running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Self-Healing Manager...")
        healing_manager.stop_monitoring()
        print("Self-Healing Manager stopped.")