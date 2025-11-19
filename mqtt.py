import paho.mqtt.client as mqtt
import serial
import time
import threading

mqttBroker = "127.0.0.1"
mqttPort = 1883

serialPort = "/dev/ttyAMA0"
baudRate = 115200

ser = serial.Serial(serialPort, baudRate, timeout=1)

################################## Features Configuration ##################################

features = {
    "lights": {
        "home/automation/Light1/command": {"code": [5,1,1]},
        "home/automation/Light2/command": {"code": [5,1,2]},
        "home/automation/Light3/command": {"code": [5,1,4]},
        "home/automation/Light4/command": {"code": [5,1,8]},
    },

    "fan": {
        "home/automation/FS/command": {
            "codeFS": [125,0,0],
            "commands": {
                "off": 0,
                "speed1": 1,
                "speed2": 2,
                "speed3": 3
            }
        }
    },

    "temperature": {
        "read_code": [125,2,26,0,0],
        "status_topic": "home/automation/Temperature/status"
    },
    
    "generalMode": {
        "home/automation/GM/command": {
            "codeGM": [125,0,0],
            "commands": {
                "sunny": 9,
                "snowy": 5
            }
        }
    },
    
    "desiredTemp": {
       "home/automation/RS/command": {
           "codeRS": [125, 3, 0]
       },
       "status_topic": "home/automation/RS/status"
    }
}

################################## Light Handler ##################################

def handle_light(client, msg):
    payload = msg.payload.decode().lower()
    base_code = features["lights"][msg.topic]["code"]

    cmd = bytearray(base_code)

    if payload == "on":
        cmd[1] = 1
    elif payload == "off":
        cmd[1] = 2
    else:
        print("Unknown light command:", payload)
        return

    ser.write(cmd)

    status_topic = msg.topic.replace("command", "status")
    client.publish(status_topic, payload)

################################## Fan Handler ##################################

def handle_fan(client, msg):
    payload = msg.payload.decode().lower()
    fan = features["fan"][msg.topic]

    if payload not in fan["commands"]:
        print("Unknown fan command:", payload)
        return

    speed = fan["commands"][payload]
    cmd = bytearray(fan["codeFS"])
    cmd[2] = speed

    ser.write(cmd)

    status_topic = msg.topic.replace("command", "status")
    client.publish(status_topic, payload)
    
################################## General Mode Handler ##################################

def handle_generalMode(client, msg):
    payload = msg.payload.decode().lower()
    generalMode = features["generalMode"][msg.topic]
    
    if payload not in generalMode["commands"]:
        print("Unknown generalMode command:", payload)
        return
    
    mode = generalMode["commands"][payload]
    cmd = bytearray(generalMode["codeGM"])
    cmd[2] = mode
    
    ser.write(cmd)
    
    status_topic = msg.topic.replace("command", "status")
    client.publish(status_topic, payload)

################################## Temperature Reader ##################################

def temperature_reader():
    read_cmd = bytearray(features["temperature"]["read_code"])
    status_topic = features["temperature"]["status_topic"]

    while True:
        ser.write(read_cmd)
        resp = ser.read(5)
        
        if len(resp) == 5:
            temp_raw = resp[3]
            temp_value = temp_raw / 2
            client.publish(status_topic, temp_value)

        time.sleep(5)

threading.Thread(target=temperature_reader, daemon=True).start()

################################## Desired Temp handler ##################################

def handle_desiredTemp(client, msg):
    try:
        # OpenHAB sends numeric values like "20"
        temp = float(msg.payload.decode())
    except:
        print("Invalid desired temperature:", msg.payload)
        return

    # Convert to device format: multiply by 2
    temp_code_value = int(temp * 2)

    feature = features["desiredTemp"][msg.topic]
    cmd = bytearray(feature["codeRS"])
    cmd[2] = temp_code_value

    ser.write(cmd)

    # Publish status back
    status_topic = features["desiredTemp"]["status_topic"]
    client.publish(status_topic, temp)



################################## MQTT Setup ##################################

topic_handlers = {}

for t in features["lights"].keys():
    topic_handlers[t] = handle_light

for t in features["fan"].keys():
    topic_handlers[t] = handle_fan
    
for t in features["generalMode"].keys():
    topic_handlers[t] = handle_generalMode
    
for t in features["desiredTemp"].keys():
    if t.endswith("command"):
        topic_handlers[t] = handle_desiredTemp


def on_connect(client, userdata, flags, rc):
    print("Connected:", rc)
    for topic in topic_handlers.keys():
        client.subscribe(topic)


def on_message(client, userdata, msg):
    handler = topic_handlers.get(msg.topic)
    if handler:
        handler(client, msg)
    else:
        print("Unhandled topic:", msg.topic)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(mqttBroker, mqttPort, 60)
client.loop_forever()
