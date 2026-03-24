"""
Test script for Platinum Tier health monitoring system
This script tests the CPU monitoring, alerting, and dashboard integration
"""
import time
import threading
import json
from datetime import datetime, timedelta
from health_monitor import HealthMonitor


def test_cpu_monitoring():
    """
    Test the CPU monitoring and alerting functionality
    """
    print("Testing CPU Monitoring Functionality...")
    print("-" * 40)

    # Create health monitor with short check interval for testing
    health_monitor = HealthMonitor(check_interval=5)
    health_monitor.start_monitoring()

    print("Health monitor started with 5-second check intervals")
    print("Current system health:")

    # Get initial health
    initial_health = health_monitor.get_system_health()
    print(f"  CPU: {initial_health['cpu_percent']}%")
    print(f"  Memory: {initial_health['memory_percent']}%")
    print(f"  Disk: {initial_health['disk_percent']}%")

    print("\nSimulating high CPU usage for 20 seconds...")

    # Start high CPU simulation
    cpu_thread = health_monitor.simulate_high_cpu(duration=20)

    print("Waiting for alerts to be generated...")

    # Wait for high CPU to trigger alerts
    cpu_thread.join()

    print("High CPU simulation completed.")

    # Wait a moment for health checks to process
    time.sleep(10)

    # Get recent alerts
    alerts = health_monitor.get_recent_alerts()
    print(f"\nFound {len(alerts)} recent alerts:")

    for alert in alerts:
        print(f"  - {alert['type']}: {alert['message']} [{alert['severity']}] at {alert['timestamp']}")

    # Check if CPU alert was generated
    cpu_alerts = [a for a in alerts if 'cpu' in a['type'].lower()]
    if cpu_alerts:
        print(f"\n[SUCCESS] {len(cpu_alerts)} CPU alert(s) were generated as expected")
    else:
        print(f"\n[WARNING] No CPU alerts were generated during high CPU usage")

    health_monitor.stop_monitoring()
    print("\nCPU monitoring test completed.")


def test_scheduler_monitoring():
    """
    Test the scheduler monitoring functionality
    """
    print("\nTesting Scheduler Monitoring Functionality...")
    print("-" * 40)

    # Create health monitor
    health_monitor = HealthMonitor(check_interval=2)
    health_monitor.start_monitoring()

    # Set scheduler timestamp to a long time ago to trigger alert
    health_monitor.last_scheduler_run = datetime.now() - health_monitor.scheduler_timeout - timedelta(seconds=60)

    print("Scheduler timestamp set to trigger inactive alert...")

    # Wait for health check to run and detect the issue
    time.sleep(5)

    # Check for scheduler alerts
    alerts = health_monitor.get_recent_alerts()
    scheduler_alerts = [a for a in alerts if 'scheduler' in a['type'].lower()]

    if scheduler_alerts:
        print(f"[SUCCESS] {len(scheduler_alerts)} scheduler alert(s) were generated")
        for alert in scheduler_alerts:
            print(f"  - {alert['message']}")
    else:
        print("[WARNING] No scheduler alerts were generated")

    health_monitor.stop_monitoring()
    print("Scheduler monitoring test completed.")


def test_memory_disk_monitoring():
    """
    Test memory and disk monitoring (will show current status, no actual alerting without high usage)
    """
    print("\nTesting Memory and Disk Monitoring...")
    print("-" * 40)

    health_monitor = HealthMonitor(check_interval=3)
    health_monitor.start_monitoring()

    # Get current memory and disk usage
    health = health_monitor.get_system_health()
    print(f"Current Memory Usage: {health['memory_percent']}%")
    print(f"Current Disk Usage: {health['disk_percent']}%")

    print(f"Memory Threshold: {health_monitor.memory_threshold}%")
    print(f"Disk Threshold: {health_monitor.disk_threshold}%")

    if health['memory_percent'] < health_monitor.memory_threshold:
        print("✅ Memory usage is within normal limits")
    else:
        print("⚠️ Memory usage is above threshold")

    if health['disk_percent'] < health_monitor.disk_threshold:
        print("✅ Disk usage is within normal limits")
    else:
        print("⚠️ Disk usage is above threshold")

    health_monitor.stop_monitoring()
    print("Memory and disk monitoring test completed.")


def test_integration_with_dashboard():
    """
    Test integration with dashboard
    """
    print("\nTesting Dashboard Integration...")
    print("-" * 40)

    from dashboard import get_system_health
    import json

    print("Getting system health through dashboard function...")
    health_data = get_system_health()

    print("Dashboard health data:")
    print(f"  CPU: {health_data.get('cpu_percent', 'N/A')}%")
    print(f"  Memory: {health_data.get('memory_percent', 'N/A')}%")
    print(f"  Disk: {health_data.get('disk_usage', 'N/A')}%")

    if 'health_monitor_status' in health_data:
        print("  Health Monitor Status: Available")
        health_status = health_data['health_monitor_status']
        print(f"  Total Alerts: {health_status.get('total_alerts_count', 0)}")
        print(f"  System Healthy: {health_status.get('is_system_healthy', 'N/A')}")
    else:
        print("  Health Monitor Status: Not available")

    print("Dashboard integration test completed.")


def main():
    """
    Run all tests
    """
    print("Platinum Tier Health Monitoring System - Test Suite")
    print("=" * 60)

    # Import required modules
    from datetime import timedelta

    # Run tests
    test_cpu_monitoring()
    test_memory_disk_monitoring()
    test_scheduler_monitoring()
    test_integration_with_dashboard()

    print("\n" + "=" * 60)
    print("Test suite completed!")
    print("Check vault/Logs/health_alerts.json for stored alerts.")


if __name__ == "__main__":
    main()