"""
Platinum Tier AI Employee Main Application
Main entry point that coordinates health monitoring, self-healing, orchestrator, and dashboard
"""
import threading
import time
from datetime import datetime
from pathlib import Path
from health_monitor import HealthMonitor
from self_healing_manager import SelfHealingManager
from dashboard import app as dashboard_app
from orchestrator import ExecutiveOrchestrator


def start_dashboard():
    """
    Start the dashboard Flask application
    """
    print("Starting Platinum Tier Dashboard on http://localhost:5000")
    try:
        dashboard_app.run(host='localhost', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Error starting dashboard: {e}")


def start_orchestrator(vault_path="vault", is_cloud=False):
    """
    Start the executive orchestrator
    """
    print(f"Starting {'Cloud' if is_cloud else 'Local'} Executive Orchestrator...")
    try:
        orchestrator = ExecutiveOrchestrator(
            vault_path=vault_path,
            is_cloud_executive=is_cloud,
            remote_repo_url=None  # Can be configured if needed
        )

        # Start continuous synchronization
        orchestrator.start_continuous_sync(interval=30)

        # Start task scheduler
        orchestrator.start_task_scheduler(interval=60)

        print("Orchestrator started successfully")
    except Exception as e:
        print(f"Error starting orchestrator: {e}")


def main():
    """
    Main function to coordinate all Platinum Tier services
    """
    print("Starting Platinum Tier AI Employee System...")
    print("=" * 50)

    # Initialize health monitor
    print("Initializing Health Monitor...")
    health_monitor = HealthMonitor(check_interval=30)
    health_monitor.start_monitoring()

    # Initialize self-healing manager
    print("Initializing Self-Healing Manager...")
    healing_manager = SelfHealingManager(check_interval=15)
    healing_manager.start_monitoring()

    # Start orchestrator in a separate thread
    print("Starting Orchestrator...")
    vault_path = Path("vault")
    vault_path.mkdir(exist_ok=True)
    orchestrator_thread = threading.Thread(
        target=start_orchestrator,
        args=(str(vault_path), False),  # False = Local Executive
        daemon=True
    )
    orchestrator_thread.start()

    # Start dashboard in a separate thread
    print("Starting Dashboard...")
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()

    print("=" * 50)
    print("All Platinum Tier services started successfully!")
    print("Dashboard: http://localhost:5000")
    print("Health Monitor: Running")
    print("Self-Healing: Active")
    print("Orchestrator: Running (Task Scheduler Active)")
    print("=" * 50)

    # Main loop - keep the application running
    try:
        while True:
            time.sleep(10)  # Check every 10 seconds if services are still running

            # Update scheduler timestamp to indicate system is active
            health_monitor.update_scheduler_timestamp()

    except KeyboardInterrupt:
        print("\nShutting down Platinum Tier services...")

        # Stop monitoring and healing managers
        health_monitor.stop_monitoring()
        healing_manager.stop_monitoring()

        print("All services stopped. Goodbye!")


if __name__ == "__main__":
    main()