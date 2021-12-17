from opcua import Client
from opcua import ua
import json

from opcua.ua.uaprotocol_auto import PublishedDataItemsDataType
   
class PLC:
    def __init__(self, ip_address, port):
        self.client = Client(f"opc.tcp://{ip_address}:{port}")
        self.client.connect()
        self.sw_out_3 = self.client.get_node("ns=4;s=Root.setter/resetter.switch_output3")

    def read_node(self, node):
        node = self.client.get_node(node)
        value = node.get_value()
        return value

    def write_output_3(self, value):
        value = ua.DataValue(ua.Variant(value, ua.VariantType.Boolean))
        value.ServerTimestamp = None
        value.SourceTimestamp = None
        self.sw_out_3.set_data_value(value)

    def disconnect(self):
        self.client.disconnect()

    
    def new_client():
        return PLC("172.23.177.83", 48020)
    
    def getData(client):

        setpoint = client.read_node("ns=4;s=Root.heating.setpoint_heating")
        #print(f"setpoint: {setpoint}")

        digin0 = client.read_node("ns=4;s=Root.inputs.Digital_Inputs_0")
        #print(f"digi in 0: {digin0}")

        digin1 = client.read_node("ns=4;s=Root.inputs.Digital_Inputs_1")
        #print(f"digi in 1: {digin1}")

        digout0 = client.read_node("ns=4;s=Root.outputs.Digital_Outputs_0")
        #print(f"digi out 0: {digout0}")

        digout1 = client.read_node("ns=4;s=Root.outputs.Digital_Outputs_1")
        #print(f"digi out 1: {digout1}")

        reset4 = client.read_node("ns=4;s=Root.setter/resetter.reset_output4")
        #print(f"reset output 4: {reset4}")

        set4 = client.read_node("ns=4;s=Root.setter/resetter.set_output4")
        #print(f"set 4: {set4}")

        switch3 = client.read_node("ns=4;s=Root.setter/resetter.switch_output3")
        #print(f"switch output 3: {switch3}")

        switch5 = client.read_node("ns=4;s=Root.setter/resetter.switch_output5")
        #print(f"switch output 5: {switch5}")

        payload = {"setpoint":setpoint, "digin0":digin0, "digin1":digin1, "digout0":digout0, "digout1":digout1, "reset4":reset4, "set4":set4, "switch3": switch3, "switch5":switch5}

        return payload