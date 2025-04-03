import time
from pymavlink import mavutil

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





# Main function to connect to the flight controller

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
    
# Once connected, use 'the_connection' to get and send messages