import paho.mqtt.client as mqtt
import serial
import time
import threading


mqttBroker = "127.0.0.1"
mqttPort = 1883
serialPort = "/dev/ttyAMA0"
baudRate = 115200

L1_command_topic = "home/automation/Light1/command"
L1_status_topic = "home/automation/Light1/status"
L2_command_topic = "home/automation/Light2/command"
L2_status_topic = "home/automation/Light2/status"
L3_command_topic = "home/automation/Light3/command"
L3_status_topic = "home/automation/Light3/status"
L4_command_topic = "home/automation/Light4/command"
L4_status_topic = "home/automation/Light4/status"

lights = {
    L1_command_topic: [5, 1, 1],
    L2_command_topic: [5, 1, 2],
    L3_command_topic: [5, 1, 4],
    L4_command_topic: [5, 1, 8],
}

temp_status_topic = "home/automation/Temperature/status"


speed1 = "home/automation/FS/command"
speed1_status = "home/automation/FS/status"
# cooling_heating_command_topic = "home/automation/CH/command"
# cooling_heating_status_topic = "home/automation/CH/status"
# hand_auto_command_topic = "home/automation/HA/command"
# hand_auto_status_topic = "home/automation/HA/status"
# general_mode_command_topic = "home/automation/GM/command"
# general_mode_status_topic = "home/automation/GM/status"
# represent_temp_command_topic = "home/automation/RT/status"
# desired_temp_command_topic = "home/automation/RS/command"
# desired_temp_status_topic = "home/automation/RS/status"
# cooling_valve_command_topic = "home/automation/CV/command"
# cooling_valve_status_topic = "home/automation/CV/status"
# heating_valve_command_topic = "home/automation/HV/command"
# heating_valve_status_topic = "home/automation/HV/status"


thermo = {
    speed1 : [125, 0, 1],
    # "speed 2": [125, 0, 2],
    # "speed 3": [125, 0, 3],
    # "off":     [125, 0, 0]
}

ser = serial.Serial(serialPort, baudRate, timeout=1)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    for topic in lights.keys():
        client.subscribe(topic)
        
    for topic in thermo.keys():
        client.subscribe(topic)
        
    
################# light control ####################        
def on_message_lights(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    if msg.topic in lights:

        command = msg.payload.decode("utf-8").lower()
        light_info = lights[msg.topic] if msg.topic in lights else None

        serial_command = bytearray()
        serial_command.append(light_info[0])
        serial_command.append(light_info[1])
        serial_command.append(light_info[2])
    
        if command == "on":
            serial_command[1] = 1
        elif command == "off":
            serial_command[1] = 2
        else:
            print("Unknown command:", command)
            return
        ser.write(serial_command)
        status_topic = msg.topic.replace("command", "status")
        client.publish(status_topic, command)
            
            
        

################ temperature reading ####################        
temp_info = [125, 2, 26, 0, 0]

def read_temperature():
    while True:
        serial_command = bytearray(temp_info)
        ser.write(serial_command)
        response = ser.read(5)
        if len(response) == 5:
            unknown_byte = response[3]
            temp_value = unknown_byte / 2
            print("Temperature:", temp_value)
            client.publish(temp_status_topic, temp_value)
        time.sleep(5)

threading.Thread(target=read_temperature, daemon=True).start()
     
     
################ fan control #################### 
def on_message_thermo(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    if msg.topic in thermo:
        
        command = msg.payload.decode("utf-8").lower()
        thermo_info = thermo[msg.topic] if msg.topic in thermo else None

        serial_command = bytearray(thermo[command])
        serial_command.append(thermo_info[0])
        serial_command.append(thermo_info[1])
        serial_command.append(thermo_info[2])
        
        if command == "speed 1":
            serial_command[0] = 1
            serial_command[1] = 0
            serial_command[2] = 125
    
    



################# On message dispatcher ####################
def on_message(client, userdata, msg):
    if msg.topic in lights:
        on_message_lights(client, userdata, msg)
    elif msg.topic in thermo:
        on_message_thermo(client, userdata, msg)
    else:
        print("Unknown MQTT topic:", msg.topic)
      
            
                
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(mqttBroker, mqttPort, 60)
client.loop_forever()