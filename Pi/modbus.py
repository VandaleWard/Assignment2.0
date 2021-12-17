from pyModbusTCP.client import ModbusClient

class modbus:

    def __init__(self, ip_address, unit_id, port):
        self.device = ModbusClient(host=ip_address,unit_id=unit_id, port=port,auto_open=True, auto_close=True)

    # 7.4
    def read_registers(self, begin_register, total_registers):
        regs = self.device.read_holding_registers(begin_register,total_registers)
        return regs

    def get_voltage_conductors(self, regs):
        print("Reading registers 0 to 6 for the 3 Conductor voltages")
        voltages = []
        for i in range (0, len(regs), 2):
            value = (regs[i]<<16|regs[i+1])/1000
            voltages.append(value)
        return voltages

    def get_currunts_conductors(self, regsConductor):
        currunts = []
        for i in range (0, len(regsConductor), 2):
            value = (regsConductor[i]<<16|regsConductor[i+1])/1000
            if regsConductor[i] & 0x8000: # Check sign bit of first register
                value -= 2 ** 32 # sign = 1 => make negative
            currunts.append(value)
        return currunts

    def get_active_power_phases(self, regsPowerPhase):
        powerPhases = []
        for i in range (0, 12, 4):
            value = regsPowerPhase[i]<<48|regsPowerPhase[i+1]<<32|regsPowerPhase[i+2]<<16|regsPowerPhase[i+3]
            if regsPowerPhase[i] & 0x8000: # Each hexa number represents 8 bits, filter first bit to check positive of negative
                value -= 2 ** 64
            powerPhases.append(value)
        return powerPhases

    # 7.5
    def calculate_voltage(self, register):
        volt = (register - 32768) / 3276
        return volt

    def get_brightness(self, reg_brightness):
        voltage_brightness = self.calculate_voltage(reg_brightness)
        brightness = voltage_brightness / 10 * 150
        return brightness

    def get_windspeed(self, reg_windspeed):
        voltage_windspeed = self.calculate_voltage(reg_windspeed)
        windspeed = voltage_windspeed / 10 * 40
        return windspeed

    def get_temperature(self, reg_temperature):
        voltage_temperature = self.calculate_voltage(reg_temperature)
        temperature = voltage_temperature / 10 * 80 - 20
        return temperature

    def get_humidity(self, reg_humidity):
        voltage_humidity = self.calculate_voltage(reg_humidity)
        humidity = voltage_humidity * 10
        return humidity

    def new_client():
        eva = modbus('172.23.176.39', 1, 502)
        return eva

    def getData(eva):
        regsAdam = eva.read_registers(4, 4)
        brightness = eva.get_brightness(regsAdam[0])
        windspeed = eva.get_windspeed(regsAdam[1])
        temperature = eva.get_temperature(regsAdam[2])
        humidity = eva.get_humidity(regsAdam[3])

        payload = {"brightness": brightness, "windspeed": windspeed, "temperature": temperature, "humidity": humidity}
        return payload


# if __name__ == "__main__":
#     c = modbus('172.23.177.27', 255, 502)