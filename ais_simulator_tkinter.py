import socket
import sys
import math
import time
import threading
from datetime import datetime
from random import random
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os


# UDP broadcasting setup
sendsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sendsocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sendsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sendsocket.bind(('0.0.0.0', 0))
    print("--- UDP socket bound successfully")
except Exception as e:
    print(f"Warning: Could not bind socket: {str(e)}")
    print("--- Broadcasting NMEA messages to UDP:10110")

listensocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listensocket.bind(("", 20220))
listensocket.listen(1)
print("--- Listening to NMEA messages at TCP:20220")


def nmeaChecksum(s):
    """Calculate NMEA checksum"""
    chkSum = 0
    subStr = s[1:len(s)]
    for e in range(len(subStr)):
        chkSum ^= ord((subStr[e]))
    hexstr = str(hex(chkSum))[2:4].upper()
    if len(hexstr) == 2:
        return hexstr
    else:
        return '0'+hexstr


def joinNMEAstrs(payloadstr):
    """Join NMEA strings with checksum"""
    tempstr = '!AIVDM,1,1,,A,' + payloadstr + ',0'
    result = tempstr + '*' + nmeaChecksum(tempstr) + "\r\n"
    return result


def num2bin(num, bitWidth):
    """Convert number to binary string"""
    num = int(num)
    num &= (2 << bitWidth-1)-1
    formatStr = '{:0'+str(bitWidth)+'b}'
    return formatStr.format(int(num))


def string2bin(myString, i_width):
    """Convert string to binary"""
    enc = ''
    for i in range(len(myString)):
        enc += num2bin(ord(myString[i].upper()), 6)
    return enc.ljust(i_width, '0')[:i_width]


mapping = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVW`abcdefghijklmnopqrstuvw"


def ais_message1(i_mtype, i_repeat, i_mmsi, i_status, i_turn, i_speed, i_accuracy, i_lat, i_lon, i_course, 
                 i_heading, i_second, i_maneuver, i_spare, i_raim, i_radio):
    """Generate AIS message type 1"""
    bits = num2bin(i_mtype,6) + num2bin(i_repeat,2) + num2bin(i_mmsi, 30) + num2bin(i_status, 4) + \
        num2bin(int(4.733*math.sqrt(float(i_turn))), 8) + num2bin(i_speed*10, 10) + num2bin(i_accuracy, 1) + num2bin(int(600000*float(i_lon)), 28) + \
        num2bin(int(600000*float(i_lat)), 27) + num2bin(i_course*10, 12) + num2bin(i_heading, 9) + num2bin(i_second, 6) + \
        num2bin(i_maneuver, 2) + num2bin(i_spare, 3) + num2bin(i_raim, 1) + num2bin(i_radio, 19)
    
    enc = ''
    while bits:
        n = int(bits[:6],2)
        enc = enc + mapping[n:n+1]
        bits = bits[6:]
    return '' + joinNMEAstrs(enc)


def ais_message5(i_mtype, i_repeat, i_mmsi, i_version, i_imo, i_callsign, i_name, i_shiptype, i_to_bow, i_to_stern, i_to_port, i_to_stbd, 
                 i_fixtype, i_eta_month, i_eta_day, i_eta_hour, i_eta_minute, i_draught, i_destination, i_dte, i_spare, i_filler):
    """Generate AIS message type 5"""
    bits = num2bin(i_mtype, 6) + num2bin(i_repeat, 2) + num2bin(i_mmsi, 30) + num2bin(i_version, 2) + \
        num2bin(i_imo, 30) + string2bin(i_callsign, 42) + string2bin(i_name, 120) + num2bin(i_shiptype, 8) + \
        num2bin(i_to_bow, 9) + num2bin(i_to_stern, 9) + num2bin(i_to_port, 6) + num2bin(i_to_stbd, 6) + \
        num2bin(i_fixtype, 4) + num2bin(i_eta_month, 4) + num2bin(i_eta_day, 5) + num2bin(i_eta_hour, 5) + \
        num2bin(i_eta_minute, 6) + num2bin(i_draught, 8) + string2bin(i_destination, 120) + num2bin(i_dte, 1) + \
        num2bin(i_spare, 1) + num2bin(i_filler, 2)
    
    enc = ''
    while bits:
        n = int(bits[:6],2)
        enc = enc + mapping[n:n+1]
        bits = bits[6:]
        
    tempstr1 = '!AIVDM,2,1,3,A,' + enc[:59] + ',0'
    tempstr2 = '!AIVDM,2,2,3,A,' + enc[59:] + ',0'
    return tempstr1 + '*' + nmeaChecksum(tempstr1) + "\r\n" + tempstr2 + '*' + nmeaChecksum(tempstr2) + "\r\n"


def send_nmea(message):
    """Send NMEA message via UDP to OpenCPN"""
    try:
        # Print message to console (only first line to avoid spam)
        first_line = message.split('\r\n')[0] if '\r\n' in message else message.strip()
        print(f"Sending: {first_line}")
        
        # Send to OpenCPN server (192.168.10.100)
        try:
            sendsocket.sendto(message.encode(), ('192.168.10.100', 10110))
            print("Sent to OpenCPN server (192.168.10.100:10110)")
        except Exception as e:
            print(f"Failed to send to OpenCPN server: {str(e)}")
            
        # Also try localhost for local testing
        try:
            sendsocket.sendto(message.encode(), ('127.0.0.1', 10110))
            print("Sent to localhost")
        except Exception as e:
            print(f"Failed to send to localhost: {str(e)}")
            
    except Exception as e:
        print(f"Error in send_nmea: {str(e)}")


class Ship:
    """Ship class for AIS simulation"""
    def __init__(self, mmsi, name, lat, lon, heading, speed, status=0, own=False):
        self.mmsi = mmsi
        self.name = name
        self.lat = float(lat)
        self.lon = float(lon)
        self.speed = float(speed)
        self.heading = float(heading)
        self.status = status
        self.own = own
        self.last_move = time.time()
        self.twd = 0
        self.tws = 0
        self.twv = 0
        self.curs = 0
        self.curd = 0
        
        # Initialize circular route waypoints
        self.waypoints = self.get_route_waypoints()
        self.current_waypoint = 0

    def get_route_waypoints(self):
        """Generate circular route waypoints around starting position"""
        center_lat = self.lat
        center_lon = self.lon
        radius = 0.03  # Radius in degrees (approximately 1.8 nautical miles)
        waypoints = []
        
        for i in range(16):
            angle = (i * 22.5) * math.pi / 180  # 22.5 degrees apart for smoother circle
            lat = center_lat + radius * math.cos(angle)
            lon = center_lon + radius * math.sin(angle) / math.cos(math.radians(center_lat))
            waypoints.append((lat, lon))
        
        return waypoints

    def calculate_new_heading(self, target_lat, target_lon):
        """Calculate heading to next waypoint"""
        dlat = target_lat - self.lat
        dlon = target_lon - self.lon
        heading = math.degrees(math.atan2(dlon * math.cos(math.radians(self.lat)), dlat))
        return (heading + 360) % 360

    def distance_to_waypoint(self, target_lat, target_lon):
        """Calculate distance to waypoint in nautical miles"""
        dlat = target_lat - self.lat
        dlon = target_lon - self.lon
        a = math.sin(math.radians(dlat/2)) * math.sin(math.radians(dlat/2)) + \
            math.cos(math.radians(self.lat)) * math.cos(math.radians(target_lat)) * \
            math.sin(math.radians(dlon/2)) * math.sin(math.radians(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return 3440 * c  # Earth radius in NM * central angle

    def move(self, speedup):
        """Move ship along circular route"""
        # Get current target waypoint
        target_lat, target_lon = self.waypoints[self.current_waypoint]
        
        # Calculate distance to waypoint
        distance = self.distance_to_waypoint(target_lat, target_lon)
        
        # If close to waypoint, move to next one (circular)
        if distance < 0.02:  # Within 0.02 NM for tighter circle following
            self.current_waypoint = (self.current_waypoint + 1) % len(self.waypoints)
            target_lat, target_lon = self.waypoints[self.current_waypoint]
        
        # Update heading towards waypoint
        target_heading = self.calculate_new_heading(target_lat, target_lon)
        
        # Gradually adjust heading (max 3 degrees per update for smoother circular motion)
        heading_diff = (target_heading - self.heading + 180) % 360 - 180
        if abs(heading_diff) > 3:
            self.heading += 3 if heading_diff > 0 else -3
        else:
            self.heading = target_heading
        self.heading = self.heading % 360

        elapsed = time.time() - self.last_move
        
        # Move based on current heading and speed
        self.lat = self.lat + elapsed * self.speed/3600/60 * speedup * math.cos(math.radians(self.heading))
        self.lon = self.lon + elapsed * self.speed/3600/60 * speedup * math.sin(math.radians(self.heading)) / math.cos(math.radians(self.lat))
        
        if self.own:  # apply current only to own boat
            self.lat = self.lat + elapsed * self.curs/3600/60 * speedup * math.cos(math.radians(self.curd))
            self.lon = self.lon + elapsed * self.curs/3600/60 * speedup * math.sin(math.radians(self.curd)) / math.cos(math.radians(self.lat))

        self.last_move = time.time()

    def show(self):
        """Send AIS messages for this ship"""
        if not self.own:
            my_message = ais_message1(1, 0, self.mmsi, self.status, 0, self.speed, 1, self.lat, self.lon, 
                                     self.heading, self.heading, 0, 0, 0, 0, 0) + \
                         ais_message5(i_mtype=5, i_repeat=1, i_mmsi=self.mmsi, i_version=0, i_imo=0, i_callsign="PB1234", i_name=self.name, \
                                     i_shiptype=79, i_to_bow=100, i_to_stern=50, i_to_port=15, i_to_stbd=15, i_fixtype=3, i_eta_month=0, i_eta_day=0, \
                                     i_eta_hour=24, i_eta_minute=60, i_draught=50, i_destination="Timbuktu", i_dte=1, i_spare=0, i_filler=0)
        else:
            # Own boat messages (simplified)
            my_message = f"$GPRMC,{datetime.utcnow().strftime('%H%M%S')},A,{self.lat:.6f},N,{self.lon:.6f},E,{self.speed:.1f},{self.heading:.1f},{datetime.utcnow().strftime('%d%m%y')},,A*00\r\n"
        
        send_nmea(my_message)


class AISSimulator:
    """Main simulation class"""
    def __init__(self):
        self.ships = []
        self.paused = False
        self.speedup = 60
        self.timer = None

    def add_ship(self, mmsi, name, lat, lon, heading, speed, status=0, own=False):
        """Add a ship to the simulation"""
        ship = Ship(mmsi, name, lat, lon, heading, speed, status, own)
        self.ships.append(ship)
        return ship

    def remove_ship(self, index):
        """Remove a ship from the simulation"""
        if 0 <= index < len(self.ships):
            del self.ships[index]

    def clear_ships(self):
        """Clear all ships"""
        self.ships = []

    def start_simulation(self):
        """Start the simulation"""
        if not self.paused:
            self.move_ships()
        self.timer = threading.Timer(1, self.start_simulation)
        self.timer.daemon = True
        self.timer.start()

    def stop_simulation(self):
        """Stop the simulation"""
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def move_ships(self):
        """Move all ships"""
        for ship in self.ships:
            ship.move(self.speedup)
            ship.show()

    def set_speedup(self, speedup):
        """Set simulation speed multiplier"""
        self.speedup = speedup


class AISSimulatorGUI:
    """Tkinter GUI for AIS Simulator"""
    def __init__(self, root):
        self.root = root
        self.root.title("AIS Simulator - Circular Routes (Tkinter)")
        self.root.geometry("900x700")
        
        self.simulator = AISSimulator()
        self.ships_data = []
        
        self.setup_ui()
        self.load_ships_data()

    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="AIS Simulator - Circular Route Generator", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Ship management frame
        ship_frame = ttk.LabelFrame(main_frame, text="Ship Management", padding="10")
        ship_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        ship_frame.columnconfigure(0, weight=1)
        ship_frame.rowconfigure(1, weight=1)
        
        # Ship management buttons
        button_frame = ttk.Frame(ship_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(button_frame, text="Add Ship", command=self.add_ship_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Edit Selected", command=self.edit_ship_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_ship).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear All", command=self.clear_all_ships).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Add Sample Ships", command=self.add_sample_ships).pack(side=tk.LEFT, padx=(0, 5))
        
        # Ship list
        self.ship_tree = ttk.Treeview(ship_frame, columns=('MMSI', 'Name', 'Latitude', 'Longitude', 'Heading', 'Speed'), 
                                     show='headings', height=8)
        
        # Configure columns
        self.ship_tree.heading('MMSI', text='MMSI')
        self.ship_tree.heading('Name', text='Name')
        self.ship_tree.heading('Latitude', text='Latitude')
        self.ship_tree.heading('Longitude', text='Longitude')
        self.ship_tree.heading('Heading', text='Heading')
        self.ship_tree.heading('Speed', text='Speed (kts)')
        
        self.ship_tree.column('MMSI', width=100)
        self.ship_tree.column('Name', width=150)
        self.ship_tree.column('Latitude', width=120)
        self.ship_tree.column('Longitude', width=120)
        self.ship_tree.column('Heading', width=80)
        self.ship_tree.column('Speed', width=100)
        
        # Scrollbar for ship list
        ship_scrollbar = ttk.Scrollbar(ship_frame, orient=tk.VERTICAL, command=self.ship_tree.yview)
        self.ship_tree.configure(yscrollcommand=ship_scrollbar.set)
        
        self.ship_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        ship_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Control frame
        control_frame = ttk.LabelFrame(main_frame, text="Simulation Control", padding="10")
        control_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Speed control
        speed_frame = ttk.Frame(control_frame)
        speed_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(speed_frame, text="Speed Multiplier:").pack(side=tk.LEFT)
        self.speed_var = tk.IntVar(value=60)
        speed_spinbox = ttk.Spinbox(speed_frame, from_=1, to=3600, textvariable=self.speed_var, width=10)
        speed_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Control buttons
        control_buttons = ttk.Frame(control_frame)
        control_buttons.pack(fill=tk.X)
        
        self.start_button = ttk.Button(control_buttons, text="Start Simulation", command=self.start_simulation)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.pause_button = ttk.Button(control_buttons, text="Pause", command=self.pause_simulation, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.resume_button = ttk.Button(control_buttons, text="Resume", command=self.resume_simulation, state=tk.DISABLED)
        self.resume_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(control_buttons, text="Stop", command=self.stop_simulation, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=8, state=tk.DISABLED)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Initial status message
        self.update_status("Ready to start simulation.\nAdd ships and click 'Start Simulation'.\nShips will follow circular routes around their starting positions.\nNMEA messages will be sent to OpenCPN at 192.168.10.100:10110.")

    def add_ship_dialog(self):
        """Open dialog to add a new ship"""
        dialog = ShipDialog(self.root, "Add Ship")
        if dialog.result:
            self.add_ship_to_list(dialog.result)
            self.update_status(f"Added ship: {dialog.result['name']}")

    def edit_ship_dialog(self):
        """Open dialog to edit selected ship"""
        selection = self.ship_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a ship to edit.")
            return
        
        item = self.ship_tree.item(selection[0])
        ship_data = {
            'mmsi': item['values'][0],
            'name': item['values'][1],
            'lat': item['values'][2],
            'lon': item['values'][3],
            'heading': item['values'][4],
            'speed': item['values'][5]
        }
        
        dialog = ShipDialog(self.root, "Edit Ship", ship_data)
        if dialog.result:
            self.ship_tree.item(selection[0], values=(
                dialog.result['mmsi'],
                dialog.result['name'],
                dialog.result['lat'],
                dialog.result['lon'],
                dialog.result['heading'],
                dialog.result['speed']
            ))
            self.update_status(f"Updated ship: {dialog.result['name']}")

    def delete_ship(self):
        """Delete selected ship"""
        selection = self.ship_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a ship to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected ship?"):
            self.ship_tree.delete(selection[0])
            self.update_status("Ship deleted.")

    def clear_all_ships(self):
        """Clear all ships"""
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all ships?"):
            self.ship_tree.delete(*self.ship_tree.get_children())
            self.update_status("All ships cleared.")

    def add_sample_ships(self):
        """Add sample ships"""
        sample_ships = [
            {"mmsi": "123456001", "name": "CONTAINER_SHIP", "lat": "35.104722", "lon": "129.087778", "heading": "45", "speed": "15"},
            {"mmsi": "123456002", "name": "CARGO_VESSEL", "lat": "35.200000", "lon": "129.200000", "heading": "90", "speed": "12"},
            {"mmsi": "123456003", "name": "TANKER", "lat": "35.000000", "lon": "129.000000", "heading": "180", "speed": "18"},
            {"mmsi": "123456004", "name": "FISHING_BOAT", "lat": "35.150000", "lon": "129.150000", "heading": "270", "speed": "8"},
            {"mmsi": "123456005", "name": "PASSENGER_FERRY", "lat": "35.250000", "lon": "129.250000", "heading": "0", "speed": "20"},
        ]
        
        for ship in sample_ships:
            self.add_ship_to_list(ship)
        
        self.update_status("Added 5 sample ships with realistic coordinates.")

    def add_ship_to_list(self, ship_data):
        """Add ship to the tree view"""
        self.ship_tree.insert('', 'end', values=(
            ship_data['mmsi'],
            ship_data['name'],
            ship_data['lat'],
            ship_data['lon'],
            ship_data['heading'],
            ship_data['speed']
        ))

    def start_simulation(self):
        """Start the simulation"""
        # Get ships from tree view
        ships = []
        for item in self.ship_tree.get_children():
            values = self.ship_tree.item(item)['values']
            try:
                ships.append({
                    'mmsi': int(values[0]),
                    'name': values[1],
                    'lat': float(values[2]),
                    'lon': float(values[3]),
                    'heading': float(values[4]),
                    'speed': float(values[5])
                })
            except (ValueError, IndexError):
                continue
        
        if not ships:
            messagebox.showwarning("No Ships", "Please add at least one ship before starting the simulation.")
            return
        
        # Clear existing ships and add new ones
        self.simulator.clear_ships()
        for ship_data in ships:
            self.simulator.add_ship(**ship_data)
        
        # Set speed multiplier
        self.simulator.set_speedup(self.speed_var.get())
        
        # Start simulation
        self.simulator.start_simulation()
        
        # Update UI
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
        
        self.update_status(f"Simulation started with {len(ships)} ships.\nShips are following circular routes.\nNMEA messages are being broadcast to OpenCPN at 192.168.10.100:10110.")

    def pause_simulation(self):
        """Pause the simulation"""
        self.simulator.paused = True
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.NORMAL)
        self.update_status("Simulation paused. NMEA messages continue to be sent.")

    def resume_simulation(self):
        """Resume the simulation"""
        self.simulator.paused = False
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
        self.update_status("Simulation resumed.")

    def stop_simulation(self):
        """Stop the simulation"""
        self.simulator.stop_simulation()
        self.simulator.clear_ships()
        
        # Update UI
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        
        self.update_status("Simulation stopped.")

    def update_status(self, message):
        """Update the status text"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"\n[{timestamp}] {message}")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)

    def load_ships_data(self):
        """Load ships data from file if exists"""
        try:
            if os.path.exists('ships_data.json'):
                with open('ships_data.json', 'r') as f:
                    self.ships_data = json.load(f)
                for ship in self.ships_data:
                    self.add_ship_to_list(ship)
        except Exception as e:
            print(f"Error loading ships data: {e}")

    def save_ships_data(self):
        """Save ships data to file"""
        try:
            ships = []
            for item in self.ship_tree.get_children():
                values = self.ship_tree.item(item)['values']
                ships.append({
                    'mmsi': values[0],
                    'name': values[1],
                    'lat': values[2],
                    'lon': values[3],
                    'heading': values[4],
                    'speed': values[5]
                })
            
            with open('ships_data.json', 'w') as f:
                json.dump(ships, f, indent=2)
        except Exception as e:
            print(f"Error saving ships data: {e}")

    def on_closing(self):
        """Handle window closing"""
        self.save_ships_data()
        self.simulator.stop_simulation()
        sendsocket.close()
        self.root.destroy()


class ShipDialog:
    """Dialog for adding/editing ships"""
    def __init__(self, parent, title, ship_data=None):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Create form
        form_frame = ttk.Frame(self.dialog, padding="20")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # MMSI
        ttk.Label(form_frame, text="MMSI:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.mmsi_var = tk.StringVar(value=ship_data['mmsi'] if ship_data else "")
        mmsi_entry = ttk.Entry(form_frame, textvariable=self.mmsi_var, width=20)
        mmsi_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Name
        ttk.Label(form_frame, text="Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar(value=ship_data['name'] if ship_data else "")
        name_entry = ttk.Entry(form_frame, textvariable=self.name_var, width=20)
        name_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Latitude
        ttk.Label(form_frame, text="Latitude:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.lat_var = tk.StringVar(value=ship_data['lat'] if ship_data else "")
        lat_entry = ttk.Entry(form_frame, textvariable=self.lat_var, width=20)
        lat_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Longitude
        ttk.Label(form_frame, text="Longitude:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.lon_var = tk.StringVar(value=ship_data['lon'] if ship_data else "")
        lon_entry = ttk.Entry(form_frame, textvariable=self.lon_var, width=20)
        lon_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Heading
        ttk.Label(form_frame, text="Heading:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.heading_var = tk.StringVar(value=ship_data['heading'] if ship_data else "")
        heading_entry = ttk.Entry(form_frame, textvariable=self.heading_var, width=20)
        heading_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Speed
        ttk.Label(form_frame, text="Speed (kts):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.speed_var = tk.StringVar(value=ship_data['speed'] if ship_data else "")
        speed_entry = ttk.Entry(form_frame, textvariable=self.speed_var, width=20)
        speed_entry.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT)
        
        # Configure grid weights
        form_frame.columnconfigure(1, weight=1)
        
        # Focus on first entry
        mmsi_entry.focus()

    def validate_input(self):
        """Validate input data"""
        try:
            mmsi = int(self.mmsi_var.get())
            if mmsi < 100000000 or mmsi > 999999999:
                messagebox.showerror("Invalid MMSI", "MMSI must be a 9-digit number.")
                return False
            
            lat = float(self.lat_var.get())
            if lat < -90 or lat > 90:
                messagebox.showerror("Invalid Latitude", "Latitude must be between -90 and 90 degrees.")
                return False
            
            lon = float(self.lon_var.get())
            if lon < -180 or lon > 180:
                messagebox.showerror("Invalid Longitude", "Longitude must be between -180 and 180 degrees.")
                return False
            
            heading = float(self.heading_var.get())
            if heading < 0 or heading > 360:
                messagebox.showerror("Invalid Heading", "Heading must be between 0 and 360 degrees.")
                return False
            
            speed = float(self.speed_var.get())
            if speed < 0 or speed > 50:
                messagebox.showerror("Invalid Speed", "Speed must be between 0 and 50 knots.")
                return False
            
            return True
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values.")
            return False

    def ok_clicked(self):
        """Handle OK button click"""
        if self.validate_input():
            self.result = {
                'mmsi': self.mmsi_var.get(),
                'name': self.name_var.get() or "UNNAMED_SHIP",
                'lat': self.lat_var.get(),
                'lon': self.lon_var.get(),
                'heading': self.heading_var.get(),
                'speed': self.speed_var.get()
            }
            self.dialog.destroy()

    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.dialog.destroy()


def main():
    """Main function"""
    root = tk.Tk()
    app = AISSimulatorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
