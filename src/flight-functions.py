import time
import math
from pymavlink import mavutil

class mission_item_int:
    def __init__(self, seq, frame, command, current, autocontinue, param1, param2, param3, param4, x, y, z):
        self.seq = 1
        self.frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT  # Use global relative longitudev and latitude
        self.command = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT  # move to waypoint
        self.current = current
        self.autocontinue = 1
        #See https://mavlink.io/en/messages/common.html#mav_commands for param descriptions
        self.param1 = 0.0   
        self.param2 = 2.0  
        self.param3 = 20.0 
        self.param4 = math.nan
        self.x = x
        self.y = y
        self.z = z
        self.mission_type = 0  

# HEARTBEAT: Start connection listen on a UDP port (14550 default for API access)
def connect_to_fc(connection_string, baudrate):
    #the_connection = mavutil.mavlink_connection('udpin:localhost:14550')
    #the_connection=mavutil.mavlink_connection('udpout:localhost:14550', robust_parsing=True)   #initiates an IP connection
    
    the_connection = mavutil.mavlink_connection(connection_string, baud=baudrate, robust_parsing=True)  #ex. /dev/serial0, 115200
    the_connection.wait_heartbeat() # Wait for the first heartbeat
    print("Heartbeat from system (system_id %u component_id %u)" % (the_connection.target_system, the_connection.target_component))
    return the_connection

# Set flight mode to GUIDED
def set_mode_guided(the_connection):
    the_connection.set_mode_guided()
    print("Mode set to GUIDED")
    # Wait for mode confirmation
    while True:
        msg = the_connection.recv_match(type='HEARTBEAT', blocking=True)
        if msg:
            mode = mavutil.mode_string_v10(msg)
            if mode == 'GUIDED':
                print("Mode confirmed as GUIDED")
                break
            else:
                print("Current mode: %s" % mode)
        time.sleep(1)

# ARMING: the vehicle prepares to take off. This is a safety feature to prevent accidental takeoffs
def arm_vehicle(the_connection):
    the_connection.arducopter_arm()
    print("Arming vehicle")
    the_connection.motors_armed_wait()
    print("Vehicle armed")

def takeoff(master, target_altitude):
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0, 0, 0, 0, 0, 0, 0, target_altitude
    )
    print("Taking off to altitude: %s" % target_altitude)
    
     # Wait until the vehicle reaches the target altitude
    while True:
        msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
        if msg:
            altitude = msg.relative_alt / 1000.0  # Convert from mm to meters
            print(f"Current altitude: {altitude:.2f} meters")
            if altitude >= target_altitude * 0.95:  # 95% of target altitude
                print("Reached target altitude.")
                break
        time.sleep(1)

def land(master):
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("Land command sent.")

    # Wait until the vehicle lands
    while True:
        msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
        if msg:
            altitude = msg.relative_alt / 1000.0  # Convert from mm to meters
            print(f"Current altitude: {altitude:.2f} meters")
            if altitude <= 0.1:  # Consider landed if altitude is less than or equal to 0.1 meters
                print("Vehicle landed.")
                break
        time.sleep(1)

def start_dataflash_logging(master):
    # Send a command to start logging
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_LOGGING_START,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("Started DataFlash logging.")

def stop_dataflash_logging(master):
    # Send a command to stop logging
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_LOGGING_STOP,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("Stopped DataFlash logging.")


# Main function to connect to the flight controller. Once connected, use 'the_connection' to get and send messages
the_connection = connect_to_fc('udp:localhost:14550', 115200)
while True: # Keep sending heartbeat messages to the flight controller
    the_connection.mav.heartbeat_send(
        type=mavutil.mavlink.MAV_TYPE_QUADROTOR,
        autopilot=mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
        base_mode=0,
        custom_mode=0,
        system_status=mavutil.mavlink.MAV_STATE_ACTIVE
    )
    time.sleep(1)
    
# Send heartbeat from a GCS (types are define as enum in the dialect file).
the_connection.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)

# Send heartbeat from a MAVLink application.
the_connection.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER,mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)

def main():
    connection_string = 'udp:localhost:14550'  # Change as needed