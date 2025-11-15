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

sen1_command_topic = "home/automation/Senario1/command"
sen1_status_topic = "home/automation/Senario1/status"

Lights = {
    L1_command_topic: [5, 1, 1],
    L2_command_topic: [5, 1, 2],
    L3_command_topic: [5, 1, 4],
    L4_command_topic: [5, 1, 8],
}

Senarioes = {
    sen1_command_topic: [125, 2, 26]
}

temp_status_topic = "home/automation/Temperature/status"


ser = serial.Serial(serialPort, baudRate, timeout=1)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    for topic in Lights.keys():
        client.subscribe(topic)
        
    
        
def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    if msg.topic in Lights:

        command = msg.payload.decode("utf-8").lower()
        light_info = Lights[msg.topic] if msg.topic in Lights else None

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
     
                
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(mqttBroker, mqttPort, 60)
client.loop_forever()
