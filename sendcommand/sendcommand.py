import os
from google.cloud import iot_v1

args = {
    "project_id":"industryward",
    "cloud_region":"europe-west1",
    "registry_id":"mct-devices",
    "device_id":"rpi-ward",
    "send_command": "",
    "service_account_json": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
}
clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')

def send_command(service_account_json, project_id, cloud_region, registry_id, device_id,command):
    """Send a command to a device."""
    # [START iot_send_command]
    print('Sending command to device')
    client = iot_v1.DeviceManagerClient()
    device_path = client.device_path(
        project_id, cloud_region, registry_id, device_id)

    data = command.encode('utf-8')

    return client.send_command_to_device(device_path, data)
    # [END iot_send_command]

if __name__ == '__main__':
    # send_command(args["service_account_json"], args["project_id"], args["cloud_region"], args["registry_id"], args["device_id"], args["send_command"])
    while True:
        print("------------------------------------------------------")
        print("------------------ CHOOSE AN OPTION ------------------")
        print("------------------------------------------------------")
        print("|                   Turn LED on (1)                  |")
        print("|                  Turn LED off  (2)                 |")
        choice = str(input("| your choice: "))
        if choice == "1":
            args["send_command"] = "{\"device\":\"LED\",\"command\":\"on\"}"
            send_command(args["service_account_json"], args["project_id"], args["cloud_region"], args["registry_id"], args["device_id"], args["send_command"])
        elif choice == "2":
            args["send_command"] = "{\"device\":\"LED\",\"command\":\"off\"}"
            send_command(args["service_account_json"], args["project_id"], args["cloud_region"], args["registry_id"], args["device_id"], args["send_command"])
        
        clearConsole()
        