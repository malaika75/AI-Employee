"""
Simple test for health monitoring system
"""
import time
from health_monitor import HealthMonitor

def test_basic_functionality():
    print("Testing basic health monitor functionality...")

    # Create health monitor with low thresholds for testing
    health_monitor = HealthMonitor(check_interval=5)
    # Temporarily set thresholds lower for testing
    health_monitor.cpu_threshold = 5  # Set very low threshold for testing
    health_monitor.memory_threshold = 5
    health_monitor.disk_threshold = 5

    health_monitor.start_monitoring()

    print("Getting initial system health...")
    health = health_monitor.get_system_health()
    print(f"CPU: {health['cpu_percent']}%")
    print(f"Memory: {health['memory_percent']}%")
    print(f"Disk: {health['disk_percent']}%")

    print("Getting health summary...")
    summary = health_monitor.get_health_summary()
    print(f"Is system healthy: {summary['is_system_healthy']}")
    print(f"Total alerts: {summary['total_alerts_count']}")

    # Check for existing alerts
    alerts = health_monitor.get_recent_alerts()
    print(f"Recent alerts: {len(alerts)}")
    for alert in alerts:
        print(f"  - {alert['type']}: {alert['message']} [{alert['severity']}]")

    health_monitor.stop_monitoring()
    print("Test completed.")

if __name__ == "__main__":
    test_basic_functionality()