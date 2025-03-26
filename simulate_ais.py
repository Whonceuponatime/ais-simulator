#!/usr/bin/env python
import socket
import time
import ais_simulation
import threading
import signal
import sys

def signal_handler(sig, frame):
    print("\nStopping simulation...")
    if simulation:
        simulation.stopBoats(None)
        simulation.wrapup()
    sys.exit(0)

# Register signal handler for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)

DEFAULT_FILENAME = "ais_simulation.gpx"

# Create simulation instance
simulation = ais_simulation.Simulation()

def print_status():
    """Print simulation status periodically"""
    while True:
        try:
            print("\nActive vessels and their positions:")
            for boat in simulation.boats:
                print(f"{boat.name}: Lat={boat.lat:.6f}, Lon={boat.lon:.6f}, Heading={boat.heading:.1f}°, Speed={boat.speed:.1f}kts")
            time.sleep(5)
        except Exception as e:
            print(f"Error in status thread: {str(e)}")
            break

def main():
    try:
        print("Starting AIS Simulator...")
        print(f"Loading vessels from: {DEFAULT_FILENAME}")
        
        # Load and start simulation
        if simulation.loadBoats(DEFAULT_FILENAME):
            print("Vessels loaded successfully")
            print("Broadcasting NMEA messages on UDP port 10110")
            print("Press Ctrl+C to stop the simulation")
            
            # Start status printing thread
            status_thread = threading.Thread(target=print_status, daemon=True)
            status_thread.start()
            
            # Start simulation
            simulation.processBoats()
            
            # Keep main thread alive
            while True:
                time.sleep(1)
        else:
            print("Failed to load vessels. Please check if the GPX file exists and is valid.")
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, shutting down...")
        simulation.stopBoats(None)
        simulation.wrapup()
    except Exception as e:
        print(f"Error in main: {str(e)}")
        simulation.stopBoats(None)
        simulation.wrapup()

if __name__ == "__main__":
    main()

