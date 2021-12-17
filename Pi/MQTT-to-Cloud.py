#!/usr/bin/env python

# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Python sample for connecting to Google Cloud IoT Core via MQTT, using JWT.
This example connects to Google Cloud IoT Core via MQTT, using a JWT for device
authentication. After connecting, by default the device publishes 100 messages
to the device's MQTT topic at a rate of one per second, and then exits.
Before you run the sample, you must follow the instructions in the README
for this sample.
"""

# [START iot_mqtt_includes]
import datetime
import logging
import os
import random
import ssl
import time
import json
import threading
import jwt
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
from PLC import PLC
from modbus import modbus
# [END iot_mqtt_includes]

GPIO.setmode(GPIO.BCM)
led = 17
GPIO.setup(led, GPIO.OUT)
GPIO.output(led, GPIO.LOW)


args = {
    "project_id": "industryward",
    "cloud_region": "europe-west1",
    "registry_id": "mct-devices",
    "device_id": "rpi-ward",
    "private_key_file": "rsa_private_gcp.pem",
    "algorithm": "RS256",
    "ca_certs": "roots.pem",
    "mqtt_bridge_hostname": "mqtt.googleapis.com",
    "mqtt_bridge_port": 8883,
    "jwt_expires_minutes":720,
    "message_type": "event",
    "service_account_json": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
}

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.CRITICAL)

# The initial backoff time after a disconnection occurs, in seconds.
minimum_backoff_time = 1

# The maximum backoff time before giving up, in seconds.
MAXIMUM_BACKOFF_TIME = 32

# Whether to wait with exponential backoff before publishing.
should_backoff = False


# [START iot_mqtt_jwt]
def create_jwt(project_id, private_key_file, algorithm):
    """Creates a JWT (https://jwt.io) to establish an MQTT connection.
        Args:
         project_id: The cloud project ID this device belongs to
         private_key_file: A path to a file containing either an RSA256 or
                 ES256 private key.
         algorithm: The encryption algorithm to use. Either 'RS256' or 'ES256'
        Returns:
            A JWT generated from the given project_id and private key, which
            expires in 20 minutes. After 20 minutes, your client will be
            disconnected, and a new JWT will have to be generated.
        Raises:
            ValueError: If the private_key_file does not contain a known key.
        """

    token = {
            # The time that the token was issued at
            'iat': datetime.datetime.utcnow(),
            # The time the token expires.
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            # The audience field should always be set to the GCP project id.
            'aud': project_id
    }

    # Read the private key file.
    with open(private_key_file, 'r') as f:
        private_key = f.read()

    print('Creating JWT using {} from private key file {}'.format(
            algorithm, private_key_file))

    return jwt.encode(token, private_key, algorithm=algorithm)
# [END iot_mqtt_jwt]


# [START iot_mqtt_config]
def error_str(rc):
    """Convert a Paho error to a human readable string."""
    return '{}: {}'.format(rc, mqtt.error_string(rc))


def on_connect(unused_client, unused_userdata, unused_flags, rc):
    """Callback for when a device connects."""
    print('on_connect', mqtt.connack_string(rc))

    # After a successful connect, reset backoff time and stop backing off.
    global should_backoff
    global minimum_backoff_time
    should_backoff = False
    minimum_backoff_time = 1


def on_disconnect(unused_client, unused_userdata, rc):
    """Paho callback for when a device disconnects."""
    print('on_disconnect', error_str(rc))

    # Since a disconnect occurred, the next loop iteration will wait with
    # exponential backoff.
    global should_backoff
    should_backoff = True


def on_publish(unused_client, unused_userdata, unused_mid):
    """Paho callback when a message is sent to the broker."""
    # print('on_publish')


def on_message(unused_client, unused_userdata, message):
    """Callback when the device receives a message on a subscription."""
    payload = message.payload.decode('utf-8', "ignore")
    payload = json.loads(payload)
    print('Received message \'{}\' on topic \'{}\' with Qos {}'.format(payload, message.topic, str(message.qos)))
    dev = payload["device"]
    cmd = payload["command"]
    if dev == "LED":
        if cmd == "on": GPIO.output(led, GPIO.HIGH)
        elif cmd == "off": GPIO.output(led, GPIO.LOW)


def get_client(
        project_id, cloud_region, registry_id, device_id, private_key_file,
        algorithm, ca_certs, mqtt_bridge_hostname, mqtt_bridge_port):
    """Create our MQTT client. The client_id is a unique string that identifies
    this device. For Google Cloud IoT Core, it must be in the format below."""
    client_id = 'projects/{}/locations/{}/registries/{}/devices/{}'.format(
            project_id, cloud_region, registry_id, device_id)
    print('Device client_id is \'{}\''.format(client_id))

    client = mqtt.Client(client_id=client_id)

    # With Google Cloud IoT Core, the username field is ignored, and the
    # password field is used to transmit a JWT to authorize the device.
    pwd = create_jwt(project_id, private_key_file, algorithm)

    print(f"JWT:{pwd}")

    client.username_pw_set(
            username='unused',
            password=pwd)

    # Enable SSL/TLS support.
    client.tls_set(ca_certs=ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)

    # Register message callbacks. https://eclipse.org/paho/clients/python/docs/
    # describes additional callbacks that Paho supports. In this example, the
    # callbacks just print to standard out.
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Connect to the Google MQTT bridge.
    client.connect(mqtt_bridge_hostname, mqtt_bridge_port)

    # This is the topic that the device will receive configuration updates on.
    mqtt_config_topic = '/devices/{}/config'.format(device_id)

    # Subscribe to the config topic.
    client.subscribe(mqtt_config_topic, qos=1)

    # The topic that the device will receive commands on.
    mqtt_command_topic = '/devices/{}/commands/#'.format(device_id)

    # Subscribe to the commands topic, QoS 1 enables message acknowledgement.
    print('Subscribing to {}'.format(mqtt_command_topic))
    client.subscribe(mqtt_command_topic, qos=0)

    # Subscribe to the topic BB/+/data to get data to write to GCP
    #client.subscribe("BB/+/data")

    client.loop_start()

    return client
# [END iot_mqtt_config]


def detach_device(client, device_id):
    """Detach the device from the gateway."""
    # [START iot_detach_device]
    detach_topic = '/devices/{}/detach'.format(device_id)
    print('Detaching: {}'.format(detach_topic))
    client.publish(detach_topic, '{}', qos=1)
    # [END iot_detach_device]


def attach_device(client, device_id, auth):
    """Attach the device to the gateway."""
    # [START iot_attach_device]
    attach_topic = '/devices/{}/attach'.format(device_id)
    attach_payload = '{{"authorization" : "{}"}}'.format(auth)
    client.publish(attach_topic, attach_payload, qos=1)
    # [END iot_attach_device]


def mqtt_device_demo(args, sensValue, sensName, Device):
    global client
    """Connects a device, sends data, and receives data."""
    # [START iot_mqtt_run]
    global minimum_backoff_time
    global MAXIMUM_BACKOFF_TIME

    # Publish to the events or state topic based on the flag.
    sub_topic = 'events'

    mqtt_topic = '/devices/{}/{}'.format(args["device_id"], sub_topic)
    #mqtt_topic = 'projects/iotcoredemo-265409/topics/temperaturen'

    jwt_iat = datetime.datetime.utcnow()
    jwt_exp_mins = args["jwt_expires_minutes"]

    # Wait if backoff is required.
    if should_backoff:
        # If backoff time is too large, give up.
        if minimum_backoff_time > MAXIMUM_BACKOFF_TIME:
            print('Exceeded maximum backoff time. Giving up.')

            # Otherwise, wait and connect again.
            delay = minimum_backoff_time + random.randint(0, 1000) / 1000.0
            print('Waiting for {} before reconnecting.'.format(delay))
            time.sleep(delay)
            minimum_backoff_time *= 2
            client.connect(args["mqtt_bridge_hostname"], args["mqtt_bridge_port"])

    #payload = '{}/{}-payload-{}'.format(args.registry_id, args.device_id, i)

    payload = {'sensorvalue': sensValue, 'sensorname': sensName, 'device': Device}
    payload = json.dumps(payload)

    #print('Publishing message: \'{}\''.format(payload))

    # [START iot_mqtt_jwt_refresh]
    seconds_since_issue = (datetime.datetime.utcnow() - jwt_iat).seconds
    if seconds_since_issue > 60 * jwt_exp_mins:
        print('Refreshing token after {}s'.format(seconds_since_issue))
        jwt_iat = datetime.datetime.utcnow()
        client.disconnect()
        client = get_client(
            args["project_id"], args["cloud_region"],
            args["registry_id"], args["device_id"], args["private_key_file"],
            args["algorithm"], args["ca_certs"], args["mqtt_bridge_hostname"],
            args["mqtt_bridge_port"])
    # [END iot_mqtt_jwt_refresh]
    # Publish "payload" to the MQTT topic. qos=1 means at least once
    # delivery. Cloud IoT Core also supports qos=0 for at most once
    # delivery.
    client.publish(mqtt_topic, payload, qos=1)

    # Send events every second. State should not be updated as often
    # time.sleep(0.5)
    # [END iot_mqtt_run]

def setupBroker():
    global MQTTClient
    MQTTClient = mqtt.Client()
    MQTTClient.on_connect = mqtt_on_connect
    MQTTClient.on_message = mqtt_on_message

    MQTTClient.connect("172.23.83.254", 1883, 60)
    MQTTClient.loop_forever()

def mqtt_on_connect(client, userdata, flags, rc):
    global MQTTClient
    print("Connected with result code " + str(rc))
    MQTTClient.subscribe("BB/+/data")

def mqtt_on_message(client, userdata, msg):
    message = msg.payload.decode("utf8", "ignore")
    message = json.loads(message)
    vbatt = message["vbatt"]
    tempint = message["tempint"]
    temp1 = message["temp1"]
    humidity = message["humidity"]
    di1 = message["di1"]
    ai2 = message["ai2"]
    ai1 = message["ai1"]
    # print(f"vbatt: {vbatt}, tempint: {tempint}, temp1: {temp1}, humidity: {humidity}, di1: {di1}, ai1: {ai1}, ai2: {ai2}, timestamp: {timestamp}")
    sensors = {'vbatt': vbatt, 'tempint': tempint, 'temp1': temp1, 'humidity': humidity, 'di1': di1, 'ai1': ai1, 'ai2': ai2}
    send_data_GCP(sensors, "SmartSwarm")
    # print(payload)

def send_data_GCP(dataset, device):
    for data in dataset:
        mqtt_device_demo(args, dataset[data], data, device)
    print(f"{dataset} for device {device} sent")

def PLCData():
    plcClient = PLC.new_client()
    while True:
        plcData = plcClient.getData()
        send_data_GCP(plcData, "PLC")
        time.sleep(60)

def ModBusData():
    modbusClient = modbus.new_client()
    time.sleep(15)
    while True:
        modbusData = modbusClient.getData()
        send_data_GCP(modbusData, "ADAM")
        time.sleep(60)

if __name__ == '__main__':
    try:
        global client
        client = get_client(
            args["project_id"], args["cloud_region"], args["registry_id"],
            args["device_id"], args["private_key_file"], args["algorithm"],
            args["ca_certs"], args["mqtt_bridge_hostname"], args["mqtt_bridge_port"])
        PLC_Thread = threading.Thread(target=PLCData)
        PLC_Thread.start()
        ModBus_Thread = threading.Thread(target=ModBusData)
        ModBus_Thread.start()
        setupBroker()

    except KeyboardInterrupt as e:
        GPIO.cleanup()
    finally:
        print("Closing script")