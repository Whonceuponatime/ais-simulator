import socket
import sys
import math
import time
import xml.etree.ElementTree as ET
import threading
from datetime import datetime
from random import random
import wx
import wx.grid


#TCP sending
#sendsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#server_address = ('localhost', 30330)
#sendsocket.connect(server_address)

#UDP broadcasting
sendsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sendsocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sendsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sendsocket.bind(('0.0.0.0', 0))  # Bind to all interfaces
    print("--- UDP socket bound successfully")
except Exception as e:
    print(f"Warning: Could not bind socket: {str(e)}")
    print("--- Broadcasting NMEA messages to UDP:10110")

listensocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listensocket.bind(("", 20220))
listensocket.listen(1)
print ("--- Listening to NMEA messages at TCP:20220")




def nmeaChecksum(s): # str -> two hex digits in str
    chkSum = 0
    subStr = s[1:len(s)] # clip off the leading $ or !

    for e in range(len(subStr)):
        chkSum ^= ord((subStr[e]))

    hexstr = str(hex(chkSum))[2:4].upper()
    if len(hexstr) == 2:
        return hexstr
    else:
        return '0'+hexstr


def joinNMEAstrs(payloadstr): #str -> str
    tempstr = '!AIVDM,1,1,,A,' + payloadstr + ',0'
    result = tempstr + '*' + nmeaChecksum(tempstr) + "\r\n"
    return result


def num2bin (num, bitWidth):
    # deal with 2's complement
    # thx to https://stackoverflow.com/questions/12946116/twos-complement-binary-in-python
    num = int(num)
    num &= (2 << bitWidth-1)-1 # mask
    formatStr = '{:0'+str(bitWidth)+'b}'
    return formatStr.format(int(num))


def string2bin (myString, i_width):
    enc=''
    for i in range (len(myString)):
        enc += num2bin(ord(myString[i].upper()), 6)
        
    return enc.ljust(i_width, '0')[:i_width]



mapping = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVW`abcdefghijklmnopqrstuvw"
   
   
def ais_message1 (i_mtype, i_repeat, i_mmsi, i_status, i_turn, i_speed, i_accuracy, i_lat, i_lon, i_course, 
            i_heading, i_second, i_maneuver, i_spare, i_raim, i_radio):
    bits = num2bin(i_mtype,6) + num2bin(i_repeat,2) + num2bin(i_mmsi, 30) + num2bin(i_status, 4) + \
        num2bin(int(4.733*math.sqrt(float(i_turn))), 8) + num2bin(i_speed*10, 10) + num2bin(i_accuracy, 1) + num2bin(int(600000*float(i_lon)), 28) + \
        num2bin(int(600000*float(i_lat)), 27) + num2bin(i_course*10, 12) + num2bin(i_heading, 9) + num2bin(i_second, 6) + \
        num2bin(i_maneuver, 2) + num2bin(i_spare, 3) + num2bin(i_raim, 1) + num2bin(i_radio, 19)
    #print ("type..r.mmsi..........................sta.turn....speed.....alon.........................lat........................course......heading..sec...m.sp.rradio..............")
    #print (bits)
    enc = ''
    while bits:
        n=int(bits[:6],2)
        enc = enc + mapping[n:n+1]
        bits = bits[6:]

    return '' + joinNMEAstrs(enc)
    

def ais_message5 (i_mtype, i_repeat, i_mmsi, i_version, i_imo, i_callsign, i_name, i_shiptype, i_to_bow, i_to_stern, i_to_port, i_to_stbd, 
            i_fixtype, i_eta_month, i_eta_day, i_eta_hour, i_eta_minute, i_draught, i_destination, i_dte, i_spare, i_filler):
    bits = num2bin(i_mtype, 6) + num2bin(i_repeat, 2) + num2bin(i_mmsi, 30) + num2bin(i_version, 2) + \
        num2bin(i_imo, 30) + string2bin(i_callsign, 42) + string2bin(i_name, 120) + num2bin(i_shiptype, 8) + \
        num2bin(i_to_bow, 9) + num2bin(i_to_stern, 9) + num2bin(i_to_port, 6) + num2bin(i_to_stbd, 6) + \
        num2bin(i_fixtype, 4) + num2bin(i_eta_month, 4) + num2bin(i_eta_day, 5) + num2bin(i_eta_hour, 5) + \
        num2bin(i_eta_minute, 6) + num2bin(i_draught, 8) + string2bin(i_destination, 120) + num2bin(i_dte, 1) + \
        num2bin(i_spare, 1) + num2bin(i_filler, 2)
    #print ("type..r.mmsi..........................v.imo...........................callsign..................................name..........................................................................................................stype...tobow....stern....port..stbd..fix.m...d....hour.min...draught.destination.............................................................................................................dsff")
    #print (bits)
    enc = ''
    while bits:
        n=int(bits[:6],2)
        enc = enc + mapping[n:n+1]
        bits = bits[6:]
        
    tempstr1 = '!AIVDM,2,1,3,A,' + enc[:59] + ',0'
    tempstr2 = '!AIVDM,2,2,3,A,' + enc[59:] + ',0'
    return  tempstr1 + '*' + nmeaChecksum(tempstr1) + "\r\n" + tempstr2 + '*' + nmeaChecksum(tempstr2) + "\r\n"
    # return '' + joinNMEAstrs(enc) 

    

def rmc_message(i_lat, i_lon, i_heading, i_speed):
    t_ns = 'N' if i_lat > 0 else 'S'
    t_ew = 'E' if i_lon > 0 else 'W'
    i_lat = abs(i_lat)
    i_lon = abs(i_lon)
    t_lat = "%02.f%07.4f" % (math.trunc(i_lat), 60*(i_lat-math.trunc(i_lat)))
    t_lon = "%03.f%07.4f" % (math.trunc(i_lon), 60*(i_lon-math.trunc(i_lon)))
    t_time = datetime.utcnow().strftime("%H%M%S");
    t_date = datetime.utcnow().strftime("%d%m%y");

    tempstr = '$GPRMC,%s,A,%s,%s,%s,%s,%s,%s,%s,,' % (t_time, t_lat, t_ns, t_lon, t_ew, i_speed, i_heading, t_date)
    result = tempstr + '*' + nmeaChecksum(tempstr) + "\r\n"
    return result

def gll_message(i_lat, i_lon, i_heading, i_speed):
    t_ns = 'N' if i_lat > 0 else 'S'
    t_ew = 'E' if i_lon > 0 else 'W'
    i_lat = abs(i_lat)
    i_lon = abs(i_lon)
    t_lat = "%02.f%07.4f" % (math.trunc(i_lat), 60*(i_lat-math.trunc(i_lat)))
    t_lon = "%03.f%07.4f" % (math.trunc(i_lon), 60*(i_lon-math.trunc(i_lon)))
    t_date = datetime.utcnow().strftime("%d%m%y");
    t_time = datetime.utcnow().strftime("%H%M%S");

    tempstr = '$GPGLL,%s,%s,%s,%s,%s,A,C' % (t_lat, t_ns, t_lon, t_ew, t_time)
    result = tempstr + '*' + nmeaChecksum(tempstr) + "\r\n"
    return result

def mwv_message(i_awa, i_aws):
    t_awa = "%03.0f" % (float(i_awa))
    t_aws = "%03.1f" % (float(i_aws))
    tempstr = "$IIMWV,%s,R,%s,N,A" % (t_awa, t_aws)
    result = tempstr + '*' + nmeaChecksum(tempstr) + "\r\n"
    return result

def vhw_message(i_hdm, i_stwn):
    t_hdm = "%03.0f" % (float(i_hdm))
    t_stwn = "%03.1f" % (float(i_stwn))
    tempstr = "$IIVHW,,,%s,M,%s,N,," % (t_hdm, t_stwn)
    result = tempstr + '*' + nmeaChecksum(tempstr) + "\r\n"
    return result


def hdm_message(i_hdm):
    t_hdm = "%03.1f" % (float(i_hdm))
    
    tempstr = "$KKHDM,%s,M" % (t_hdm)
    result = tempstr + '*' + nmeaChecksum(tempstr) + "\r\n"
    return result


def hdt_message(i_hdm):
    t_hdm = "%03.1f" % (float(i_hdm))
    
    tempstr = "$KKHDT,%s,T" % (t_hdm)
    result = tempstr + '*' + nmeaChecksum(tempstr) + "\r\n"
    return result


def dbk_message(i_dbk):
    t_dbk = "%03.1f" % (float(i_dbk))
    
    tempstr = "$INDBK,,f,%s,M,,F" % (t_dbk)
    result = tempstr + '*' + nmeaChecksum(tempstr) + "\r\n"
    return result


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


class Simulation(object):
    boats = []
    ownBoat = []
    paused = False
    speedup = 60
    
    def __init__(self):
        self.c = 0  # progress counter
    
    def processBoats(self):
        """Main simulation loop"""
        if not self.paused:
            self.moveBoats()
        else:
            self.showBoats()
        self.timer = threading.Timer(1, self.processBoats)
        self.timer.daemon = True  # Make timer thread a daemon
        self.timer.start()

    def moveBoats(self):
        """Move all boats and show their positions"""
        for boat in self.boats:
            boat.move(self.speedup)
            boat.show()
            self.c += 1

    def showBoats(self):
        """Show current position of all boats"""
        for boat in self.boats:
            boat.show()

    def stopBoats(self, event):
        """Stop the simulation"""
        try:
            if hasattr(self, 'timer'):
                self.timer.cancel()
            print("Stopping simulation, stopped sending NMEA messages")
        except:
            pass

    def wrapup(self):
        """Clean up resources"""
        print("Closing UDP socket")
        sendsocket.close()

    def read_nmea_thread(self):
        while True:
            print ("Awaiting connection...")
            c,a = listensocket.accept()
            print ("Connection from: " + str(a) )
            while True:
                try:
                    m,x = c.recvfrom(1024)
                    if m:
                        first_line = m.decode().split("\r\n")[0]
                        line_elements = first_line.split(",")
                        if line_elements[0][3:] == "APB":
                            heading = float(line_elements[13])
                            # print ("Set heading to " + str(heading))
                            self.ownBoat.heading = heading
                        else:
                            print (f"Unknown message '{str(first_line)}'")
                    else:
                        break;
                except Exception as e:
                    print ("exception: " + str(e))
                    pass
            print ("Disconnected")
        print ("Ending thread")


    class Boat(object):
        def __init__(self, simulation, mmsi, name, lat, lon, heading, speed, status, maneuver, own):
            self.simulation = simulation
            self.mmsi = mmsi
            self.name = name
            self.lat = float(lat)
            self.lon = float(lon)
            self.speed = float(speed)
            self.heading = float(heading)
            self.status = status
            self.maneuver = maneuver
            self.own = own
            self.last_move = time.time()
            self.twd = 0
            self.tws = 0
            self.twv = 0
            self.curs = 0
            self.curd = 0
            
            # Initialize waypoints based on vessel type and location
            self.waypoints = self.get_route_waypoints()
            self.current_waypoint = 0
            self.route_completed = False

        def get_route_waypoints(self):
            """Generate circular route waypoints around starting position"""
            # Create a circular route with 16 waypoints for smoother circles
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

        def show(self):
            if self.own == False:
                my_message = ais_message1 (1, 0, self.mmsi, self.status, 0, self.speed, 1, self.lat, self.lon, 
                    self.heading, self.heading, 0, self.maneuver, 0, 0, 0) + \
                    ais_message5 (i_mtype=5, i_repeat=1, i_mmsi=self.mmsi, i_version=0, i_imo=0, i_callsign="PB1234", i_name=self.name, \
                        i_shiptype=79, i_to_bow=100, i_to_stern=50, i_to_port=15, i_to_stbd=15, i_fixtype=3, i_eta_month=0, i_eta_day=0, \
                        i_eta_hour=24, i_eta_minute=60, i_draught=50, i_destination="Timbuktu", i_dte=1, i_spare=0, i_filler=0)
            else:
                # calculate apparent wind:
                #print ("self.speed = %3f  self.tws=%3f  self.twd=%3f  self.heading=%3f" % (self.speed, self.tws, self.twd, self.heading))
                twa = (((self.twd + random() * 10 - self.heading + 180) %360) - 180)/180*math.pi
                aws = math.sqrt(self.speed**2+self.tws**2 + 2 * self.speed*self.tws*math.cos(twa))
                try:
                    angle = math.acos((self.tws * math.cos(twa) + self.speed)/(math.sqrt(self.tws**2 + self.speed**2 + 2*self.tws*self.speed*math.cos(twa))))/math.pi*180
                except:
                    angle = 0
                if (twa < 0):
                    angle = -(angle)
                #print ("angle=" + str(angle))
                awa = (angle) % 360 
                depth = 4-(math.sin(time.time()/20)+1)**2;
                my_message = rmc_message (self.lat, self.lon, self.heading, self.speed) + \
                                gll_message(self.lat, self.lon, self.heading, self.speed) + \
                                mwv_message(awa, aws) + \
                                hdm_message(self.heading) + \
                                hdt_message(self.heading) + \
                                vhw_message(self.heading, self.speed) + \
                                dbk_message(depth)
            #sys.stdout.write (my_message)    

            # TCP
            #sendsocket.sendall((my_message+"\r\n").encode('utf-8'))

            # Send NMEA message
            send_nmea(my_message)
            
        def move(self, speedup):
            # Get current target waypoint (circular route - never completed)
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
            
            if self.own == True:  # apply current only to own boat
                self.lat = self.lat + elapsed * self.curs/3600/60 * speedup * math.cos(math.radians(self.curd))
                self.lon = self.lon + elapsed * self.curs/3600/60 * speedup * math.sin(math.radians(self.curd)) / math.cos(math.radians(self.lat))

            self.last_move = time.time()


    def loadBoats(self, filename):

        print("--- Loading boats from %s" % filename)
        self.boats = []

        try:
            tree = ET.parse(filename)
        except:
            print ("*** Could not open file %s. Consider downloading example file ais_simulation.gpx from github." % filename)
            return False

        root = tree.getroot()

        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}

        for elem in root.findall('gpx:wpt', ns):
            lat=elem.get('lat')
            lon=elem.get('lon')
            name=elem.find('gpx:name', ns).text
            desc=elem.find('gpx:desc', ns).text
            descriptions=desc.split('\n')
            heading=0
            speed=0
            mmsi=0
            status=0
            for description in descriptions:
                tuple=description.split('=')
                if tuple[0]=='SPEED':
                    speed = tuple[1]
                if tuple[0]=='HEADING':
                    heading = tuple[1]
                if tuple[0]=='MMSI':
                    mmsi = tuple[1]
                if tuple[0]=='STATUS':
                    status = tuple[1]
            if name == 'AIS-OWN':
                own=True
            else:
                own=False
                
            # print ('name=%s, mmsi=%s, lat=%s, lon=%s, heading=%s, speed=%s, status=%s' % (name, mmsi, lat, lon, heading, speed, status))
            newBoat=self.Boat(self, mmsi, name, float(lat), float(lon), float(heading), float(speed), status, 0, own)
            self.boats.append(newBoat)
            if own:
                global nmea_thread
                self.ownBoat = newBoat
                nmea_thread = threading.Thread(target = self.read_nmea_thread, daemon=True)
                nmea_thread.start()
                
        return True


    def startBoats(self, event):
        filename=event.GetEventObject().filename
        self.loadBoats(filename)

        try:
            self.timer.cancel()
        except:
            pass
        if self.boats:
            print ("--- Starting simulation")
            self.timer = threading.Timer(1, self.processBoats)
            self.timer.start()
            self.paused = False
        else:
            print ("*** No boats")


    def pauseBoats(self, event):
        print ("--- Pausing simulation; keep on sending NMEA messages")
        self.paused = True


    def resumeBoats(self, event):
        print ("--- Resuming simulation")
        for boat in self.boats:
            boat.last_move = time.time()
        self.paused = False


    def steerBoat(self, event):
        steerValue = event.GetEventObject().steerValue
        print (steerValue)
        self.ownBoat.heading = self.ownBoat.heading + steerValue

    def getHeading(self):
        return str(self.ownBoat.heading)

    def setTrueWind(self, event):
        self.ownBoat.twd = float(event.GetEventObject().twd)
        self.ownBoat.tws = float(event.GetEventObject().tws)
        self.ownBoat.twv = float(event.GetEventObject().twv)

    def setTrueCurrent(self, event):
        self.ownBoat.curd = float(event.GetEventObject().curd)
        self.ownBoat.curs = float(event.GetEventObject().curs)
        self.ownBoat.curv = float(event.GetEventObject().curv)
        
    def setSpeedup(self, speedup):
        self.speedup = speedup

    def addBoatFromGUI(self, mmsi, name, lat, lon, heading, speed, status=0, own=False):
        """Add a boat directly from GUI parameters"""
        newBoat = self.Boat(self, mmsi, name, float(lat), float(lon), float(heading), float(speed), status, 0, own)
        self.boats.append(newBoat)
        if own:
            global nmea_thread
            self.ownBoat = newBoat
            nmea_thread = threading.Thread(target=self.read_nmea_thread, daemon=True)
            nmea_thread.start()
        return newBoat

    def clearBoats(self):
        """Clear all boats from simulation"""
        self.boats = []
        self.ownBoat = None


class ShipGrid(wx.grid.Grid):
    """Custom grid for ship management"""
    def __init__(self, parent):
        super().__init__(parent)
        
        # Create grid with columns
        self.CreateGrid(0, 6)
        self.SetColLabelValue(0, "MMSI")
        self.SetColLabelValue(1, "Name")
        self.SetColLabelValue(2, "Latitude")
        self.SetColLabelValue(3, "Longitude")
        self.SetColLabelValue(4, "Heading")
        self.SetColLabelValue(5, "Speed (kts)")
        
        # Set column widths
        self.SetColSize(0, 100)
        self.SetColSize(1, 150)
        self.SetColSize(2, 120)
        self.SetColSize(3, 120)
        self.SetColSize(4, 80)
        self.SetColSize(5, 100)
        
        # Enable editing
        self.EnableEditing(True)
        
        # Set cell editors for better input
        self.SetColFormatFloat(2, 6)  # Latitude with 6 decimal places
        self.SetColFormatFloat(3, 6)  # Longitude with 6 decimal places
        self.SetColFormatFloat(4, 1)  # Heading with 1 decimal place
        self.SetColFormatFloat(5, 1)  # Speed with 1 decimal place
        
        # Bind events for validation
        self.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_cell_changed)

    def on_cell_changed(self, event):
        """Validate cell data when changed"""
        row = event.GetRow()
        col = event.GetCol()
        value = self.GetCellValue(row, col)
        
        # Validate based on column
        if col == 0:  # MMSI
            try:
                mmsi = int(value)
                if mmsi < 100000000 or mmsi > 999999999:
                    self.SetCellTextColour(row, col, wx.RED)
                else:
                    self.SetCellTextColour(row, col, wx.BLACK)
            except ValueError:
                self.SetCellTextColour(row, col, wx.RED)
        elif col == 2:  # Latitude
            try:
                lat = float(value)
                if lat < -90 or lat > 90:
                    self.SetCellTextColour(row, col, wx.RED)
                else:
                    self.SetCellTextColour(row, col, wx.BLACK)
            except ValueError:
                self.SetCellTextColour(row, col, wx.RED)
        elif col == 3:  # Longitude
            try:
                lon = float(value)
                if lon < -180 or lon > 180:
                    self.SetCellTextColour(row, col, wx.RED)
                else:
                    self.SetCellTextColour(row, col, wx.BLACK)
            except ValueError:
                self.SetCellTextColour(row, col, wx.RED)
        elif col == 4:  # Heading
            try:
                heading = float(value)
                if heading < 0 or heading > 360:
                    self.SetCellTextColour(row, col, wx.RED)
                else:
                    self.SetCellTextColour(row, col, wx.BLACK)
            except ValueError:
                self.SetCellTextColour(row, col, wx.RED)
        elif col == 5:  # Speed
            try:
                speed = float(value)
                if speed < 0 or speed > 50:
                    self.SetCellTextColour(row, col, wx.RED)
                else:
                    self.SetCellTextColour(row, col, wx.BLACK)
            except ValueError:
                self.SetCellTextColour(row, col, wx.RED)
        
        event.Skip()

    def add_ship(self, mmsi="", name="", lat="", lon="", heading="", speed=""):
        """Add a new row with ship data"""
        self.AppendRows(1)
        row = self.GetNumberRows() - 1
        
        self.SetCellValue(row, 0, str(mmsi))
        self.SetCellValue(row, 1, str(name))
        self.SetCellValue(row, 2, str(lat))
        self.SetCellValue(row, 3, str(lon))
        self.SetCellValue(row, 4, str(heading))
        self.SetCellValue(row, 5, str(speed))

    def get_ships(self):
        """Get all ships from the grid with validation"""
        ships = []
        for row in range(self.GetNumberRows()):
            try:
                mmsi = int(self.GetCellValue(row, 0)) if self.GetCellValue(row, 0) else 123456000 + row
                name = self.GetCellValue(row, 1) or f"VESSEL_{row+1}"
                lat = float(self.GetCellValue(row, 2)) if self.GetCellValue(row, 2) else 0.0
                lon = float(self.GetCellValue(row, 3)) if self.GetCellValue(row, 3) else 0.0
                heading = float(self.GetCellValue(row, 4)) if self.GetCellValue(row, 4) else 0.0
                speed = float(self.GetCellValue(row, 5)) if self.GetCellValue(row, 5) else 10.0
                
                # Validate coordinates
                if lat == 0.0 and lon == 0.0:
                    continue  # Skip ships with no coordinates
                
                # Validate MMSI (should be 9 digits)
                if mmsi < 100000000 or mmsi > 999999999:
                    mmsi = 123456000 + row
                
                # Validate speed (reasonable range)
                if speed < 0 or speed > 50:
                    speed = 10.0
                
                # Validate heading
                if heading < 0 or heading > 360:
                    heading = 0.0
                
                ships.append({
                    'mmsi': mmsi,
                    'name': name,
                    'lat': lat,
                    'lon': lon,
                    'heading': heading,
                    'speed': speed
                })
            except ValueError:
                continue  # Skip invalid rows
        return ships

    def delete_selected_rows(self):
        """Delete selected rows"""
        selected_rows = []
        for row in range(self.GetNumberRows()):
            if self.IsInSelection(row, 0):
                selected_rows.append(row)
        
        # Delete in reverse order to maintain indices
        for row in reversed(selected_rows):
            self.DeleteRows(row, 1)
    
    def clear_all_ships(self):
        """Clear all ships from the grid"""
        if self.GetNumberRows() > 0:
            self.DeleteRows(0, self.GetNumberRows())
    
    def get_valid_ships_count(self):
        """Get count of ships with valid coordinates"""
        valid_count = 0
        for row in range(self.GetNumberRows()):
            try:
                lat = float(self.GetCellValue(row, 2)) if self.GetCellValue(row, 2) else 0.0
                lon = float(self.GetCellValue(row, 3)) if self.GetCellValue(row, 3) else 0.0
                if lat != 0.0 or lon != 0.0:
                    valid_count += 1
            except ValueError:
                continue
        return valid_count


class AISSimulatorFrame(wx.Frame):
    """Main application window"""
    def __init__(self):
        super().__init__(None, title="AIS Simulator - Circular Routes", size=(800, 600))
        
        self.simulation = Simulation()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(panel, label="AIS Simulator - Circular Route Generator")
        title_font = title.GetFont()
        title_font.PointSize += 4
        title_font = title_font.Bold()
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)
        
        # Ship management section
        ship_box = wx.StaticBox(panel, label="Ship Management")
        ship_sizer = wx.StaticBoxSizer(ship_box, wx.VERTICAL)
        
        # Ship grid
        self.ship_grid = ShipGrid(panel)
        ship_sizer.Add(self.ship_grid, 1, wx.EXPAND | wx.ALL, 5)
        
        # Ship management buttons
        ship_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.add_ship_btn = wx.Button(panel, label="Add Ship")
        self.add_ship_btn.Bind(wx.EVT_BUTTON, self.on_add_ship)
        ship_btn_sizer.Add(self.add_ship_btn, 0, wx.ALL, 5)
        
        self.delete_ship_btn = wx.Button(panel, label="Delete Selected")
        self.delete_ship_btn.Bind(wx.EVT_BUTTON, self.on_delete_ship)
        ship_btn_sizer.Add(self.delete_ship_btn, 0, wx.ALL, 5)
        
        self.clear_all_btn = wx.Button(panel, label="Clear All")
        self.clear_all_btn.Bind(wx.EVT_BUTTON, self.on_clear_all_ships)
        ship_btn_sizer.Add(self.clear_all_btn, 0, wx.ALL, 5)
        
        self.add_sample_btn = wx.Button(panel, label="Add Sample Ships")
        self.add_sample_btn.Bind(wx.EVT_BUTTON, self.on_add_sample_ships)
        ship_btn_sizer.Add(self.add_sample_btn, 0, wx.ALL, 5)
        
        ship_sizer.Add(ship_btn_sizer, 0, wx.ALIGN_CENTER)
        
        # Ship count display
        self.ship_count_label = wx.StaticText(panel, label="Ships: 0")
        ship_sizer.Add(self.ship_count_label, 0, wx.ALL | wx.CENTER, 5)
        main_sizer.Add(ship_sizer, 1, wx.EXPAND | wx.ALL, 10)
        
        # Control section
        control_box = wx.StaticBox(panel, label="Simulation Control")
        control_sizer = wx.StaticBoxSizer(control_box, wx.VERTICAL)
        
        # Speed control
        speed_sizer = wx.BoxSizer(wx.HORIZONTAL)
        speed_sizer.Add(wx.StaticText(panel, label="Speed Multiplier:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.speed_ctrl = wx.SpinCtrl(panel, value="60", min=1, max=3600)
        speed_sizer.Add(self.speed_ctrl, 0, wx.ALL, 5)
        control_sizer.Add(speed_sizer, 0, wx.ALIGN_CENTER)
        
        # Control buttons
        control_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.start_btn = wx.Button(panel, label="Start Simulation")
        self.start_btn.Bind(wx.EVT_BUTTON, self.on_start_simulation)
        control_btn_sizer.Add(self.start_btn, 0, wx.ALL, 5)
        
        self.pause_btn = wx.Button(panel, label="Pause")
        self.pause_btn.Bind(wx.EVT_BUTTON, self.on_pause_simulation)
        self.pause_btn.Enable(False)
        control_btn_sizer.Add(self.pause_btn, 0, wx.ALL, 5)
        
        self.resume_btn = wx.Button(panel, label="Resume")
        self.resume_btn.Bind(wx.EVT_BUTTON, self.on_resume_simulation)
        self.resume_btn.Enable(False)
        control_btn_sizer.Add(self.resume_btn, 0, wx.ALL, 5)
        
        self.stop_btn = wx.Button(panel, label="Stop")
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop_simulation)
        self.stop_btn.Enable(False)
        control_btn_sizer.Add(self.stop_btn, 0, wx.ALL, 5)
        
        control_sizer.Add(control_btn_sizer, 0, wx.ALIGN_CENTER)
        main_sizer.Add(control_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Status section
        status_box = wx.StaticBox(panel, label="Status")
        status_sizer = wx.StaticBoxSizer(status_box, wx.VERTICAL)
        
        self.status_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 100))
        self.status_text.SetValue("Ready to start simulation.\nAdd ships and click 'Start Simulation'.\nShips will follow circular routes around their starting positions.\nNMEA messages will be sent to OpenCPN at 192.168.10.100:10110.")
        status_sizer.Add(self.status_text, 1, wx.EXPAND | wx.ALL, 5)
        
        main_sizer.Add(status_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(main_sizer)
        
        # Bind close event
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
    def on_add_ship(self, event):
        """Add a new empty ship row"""
        self.ship_grid.add_ship()
        self.update_ship_count()
        
    def on_delete_ship(self, event):
        """Delete selected ships"""
        self.ship_grid.delete_selected_rows()
        self.update_ship_count()
        
    def on_clear_all_ships(self, event):
        """Clear all ships from the grid"""
        if self.ship_grid.GetNumberRows() > 0:
            dlg = wx.MessageDialog(self, "Are you sure you want to clear all ships?", 
                                 "Confirm Clear", wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_YES:
                self.ship_grid.clear_all_ships()
                self.update_ship_count()
                self.update_status("All ships cleared.")
            dlg.Destroy()
        
    def on_add_sample_ships(self, event):
        """Add some sample ships with realistic coordinates"""
        sample_ships = [
            {"mmsi": "123456001", "name": "CONTAINER_SHIP", "lat": "35.104722", "lon": "129.087778", "heading": "45", "speed": "15"},
            {"mmsi": "123456002", "name": "CARGO_VESSEL", "lat": "35.200000", "lon": "129.200000", "heading": "90", "speed": "12"},
            {"mmsi": "123456003", "name": "TANKER", "lat": "35.000000", "lon": "129.000000", "heading": "180", "speed": "18"},
            {"mmsi": "123456004", "name": "FISHING_BOAT", "lat": "35.150000", "lon": "129.150000", "heading": "270", "speed": "8"},
            {"mmsi": "123456005", "name": "PASSENGER_FERRY", "lat": "35.250000", "lon": "129.250000", "heading": "0", "speed": "20"},
        ]
        
        for ship in sample_ships:
            self.ship_grid.add_ship(**ship)
            
        self.update_ship_count()
        self.update_status("Added 5 sample ships with realistic coordinates. Each will follow a circular route around its starting position.")
        
    def on_start_simulation(self, event):
        """Start the simulation"""
        ships = self.ship_grid.get_ships()
        if not ships:
            wx.MessageBox("Please add at least one ship before starting the simulation.", 
                         "No Ships", wx.OK | wx.ICON_WARNING)
            return
            
        # Clear existing boats
        self.simulation.clearBoats()
        
        # Add ships from grid
        for ship in ships:
            self.simulation.addBoatFromGUI(
                ship['mmsi'], ship['name'], ship['lat'], ship['lon'],
                ship['heading'], ship['speed']
            )
        
        # Set speed multiplier
        self.simulation.setSpeedup(self.speed_ctrl.GetValue())
        
        # Start simulation
        try:
            if hasattr(self.simulation, 'timer'):
                self.simulation.timer.cancel()
        except:
            pass
            
        self.simulation.timer = threading.Timer(1, self.simulation.processBoats)
        self.simulation.timer.start()
        self.simulation.paused = False
        
        # Update UI
        self.start_btn.Enable(False)
        self.pause_btn.Enable(True)
        self.stop_btn.Enable(True)
        
        self.update_status(f"Simulation started with {len(ships)} ships.\nShips are following circular routes.\nNMEA messages are being broadcast to OpenCPN at 192.168.10.100:10110.")
        
    def on_pause_simulation(self, event):
        """Pause the simulation"""
        self.simulation.paused = True
        self.pause_btn.Enable(False)
        self.resume_btn.Enable(True)
        self.update_status("Simulation paused. NMEA messages continue to be sent.")
        
    def on_resume_simulation(self, event):
        """Resume the simulation"""
        for boat in self.simulation.boats:
            boat.last_move = time.time()
        self.simulation.paused = False
        self.pause_btn.Enable(True)
        self.resume_btn.Enable(False)
        self.update_status("Simulation resumed.")
        
    def on_stop_simulation(self, event):
        """Stop the simulation"""
        try:
            if hasattr(self.simulation, 'timer'):
                self.simulation.timer.cancel()
        except:
            pass
            
        self.simulation.clearBoats()
        
        # Update UI
        self.start_btn.Enable(True)
        self.pause_btn.Enable(False)
        self.resume_btn.Enable(False)
        self.stop_btn.Enable(False)
        
        self.update_status("Simulation stopped.")
        
    def update_ship_count(self):
        """Update the ship count display"""
        total_ships = self.ship_grid.GetNumberRows()
        valid_ships = self.ship_grid.get_valid_ships_count()
        self.ship_count_label.SetLabel(f"Ships: {valid_ships}/{total_ships} (valid/total)")
        
    def update_status(self, message):
        """Update the status text"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.AppendText(f"\n[{timestamp}] {message}")
        
    def on_close(self, event):
        """Handle window close"""
        try:
            if hasattr(self.simulation, 'timer'):
                self.simulation.timer.cancel()
            self.simulation.wrapup()
        except:
            pass
        self.Destroy()


class AISSimulatorApp(wx.App):
    """Main application class"""
    def OnInit(self):
        frame = AISSimulatorFrame()
        frame.Show()
        return True


if __name__ == "__main__":
    app = AISSimulatorApp()
    app.MainLoop()
