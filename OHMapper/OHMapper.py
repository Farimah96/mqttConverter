import xml.etree.ElementTree as ET
import json
import requests
import time

xml_file = "Nodes.xml"
openhab_url = "http://localhost:8080/rest/things"
items_url = "http://localhost:8080/rest/items"
# links_url = "http://localhost:8080/rest/links"

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer oh.xmltoken.HdJ12pnv7E0mIg1ZVFkbAUk3LixqnnztbEJnKu4fn6wuMgxBqmCapqixYQ7HaCZGCnY1MkB7qP31nRtetYv1Q"
}

mqtt_bridge_uid = "mqtt:broker:914491f742"
thing_type_uid = "mqtt:topic"

features_map = {
    "lights": "home/automation/Light{}/command",
    "fan": "home/automation/FS/command",
    "generalMode": "home/automation/GM/command",
    "desiredTemp": "home/automation/RS/command",
    "temperature": "home/automation/Temperature/status"
}

tree = ET.parse(xml_file)
root = tree.getroot()
things = []

for serialnode in root.findall("serialnode"):
    node_type = serialnode.find("type").text
    node_subtype = serialnode.find("subtype").text
    node_name = serialnode.find("name").text
    node_id = serialnode.find("nodeID").text

    bridge_id = mqtt_bridge_uid.split(":")[-1]
    thing_uid = f"mqtt:topic:{bridge_id}:{node_id}"
    label = node_name
    channels = []

    if node_type == "1":
        cmd_topic = features_map["lights"].format(node_subtype)
        status_topic = cmd_topic.replace("command", "status")

        channels.append({
            "uid": f"{thing_uid}:light{node_subtype}",
            "id": f"light{node_subtype}",
            "channelTypeUID": "mqtt:switch",
            "itemType": "Switch",
            "kind": "STATE",
            "label": f"Light {node_subtype}",
            "description": "",
            "defaultTags": [],
            "properties": {},
            "configuration": {
                "commandTopic": cmd_topic,
                "stateTopic": status_topic
            },
            "autoUpdatePolicy": "DEFAULT"
        })

    thing = {
        "label": label,
        "bridgeUID": mqtt_bridge_uid,
        "configuration": {},
        "properties": {},
        "UID": thing_uid,
        "thingTypeUID": thing_type_uid,
        "location": "",
        "semanticEquipmentTag": "",
        "channels": channels
    }

    things.append(thing)

for idx, thing in enumerate(things, start=1):
    try:
        resp = requests.post(openhab_url, headers=headers, data=json.dumps(thing))

        #get again for real UID
        thing_resp = requests.get(f"http://localhost:8080/rest/things/{thing['UID']}", headers=headers)
        thing_data = thing_resp.json()

        actual_channels = {ch["id"]: ch["uid"] for ch in thing_data["channels"]}
        #teg again for real UID


        if resp.status_code in (200, 201):
            print(f"[{idx}/{len(things)}] Thing '{thing['label']}' created successfully")
        elif resp.status_code == 409:
            print(f"[{idx}/{len(things)}] Thing '{thing['label']}' already exists")
        else:
            print(f"[{idx}/{len(things)}] Failed to create '{thing['label']}': {resp.status_code}, {resp.text}")
            continue

        for ch in thing["channels"]:
            item_name = f"{thing['label'].replace(' ','')}_{ch['id']}"

            item_payload = {
                "type": ch["itemType"],
                "name": item_name,
                "label": f"{thing['label']} {ch['label']}",
                "category": "lightbulb",
                "tags": ["Power", "Switch"],
                "groupNames": []
            }

            item_resp = requests.put(
                f"{items_url}/{item_name}",
                headers=headers,
                data=json.dumps(item_payload)
            )

            if item_resp.status_code in (200, 201):
                print(f"    → Item '{item_name}' created successfully")
            elif item_resp.status_code == 409:
                print(f"    → Item '{item_name}' already exists")
            else:
                print(f"    → Item fail {item_resp.status_code}: {item_resp.text}")
                continue


            ch_uid_real = actual_channels[ch["id"]]
            
            link_url = f"http://localhost:8080/rest/links/{item_name}/{ch_uid_real}"
            link_resp = requests.put(link_url, headers=headers)

            if link_resp.status_code in (200, 201):
                print(f"    → Linked '{item_name}' to channel '{ch_uid_real}'")
            else:
                print(f"    → Link fail {link_resp.status_code}: {link_resp.text}")

        time.sleep(0.1)

    except Exception as e:
        print(f"[{idx}/{len(things)}] Exception for '{thing['label']}': {e}")