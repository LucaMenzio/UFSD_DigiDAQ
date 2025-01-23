# CAEN DT1471ET control module, not all original features supported.

import pyvisa as pv
import time

# Tolerance for voltage target, setting function will return once
# the difference between set voltage and actual output is less than this
VOLTAGE_TOLERANCE = 2 # Volt

# Delay between commands sent to device, increase as needed
TIME_DELAY = 1 # s

class HighVoltage():

    def __init__(self, board, resource = None):
        self.board = board
        self.connected = False
        self.rm = pv.ResourceManager("@py")

        # If no VISA resource is specified when instantiating the class
        # ask the user directly!
        if resource == None:
            resource = self.promptResource()
        # Otherwise use it...
        else:
            resource = self.rm.list_resources()[resource]

        try:
            self.handle = self.rm.open_resource(resource)
        except:
            return

        # It worked, we are now connected
        self.connected = True
        self.handle.query_delay = TIME_DELAY

        # Make sure the power supply control mode is set to REMOTE
        while True:
            status = self.getQuery("BDCTR")
            if "REMOTE" not in status:
                input("Please set power supply to REMOTE control and \
                    press enter...")
            else:
                break

        self.model = self.getQuery("BDNAME")

    # General method to send a SET query to the power supply
    def setQuery(self, param, channel, value = None):
        time.sleep(TIME_DELAY)
        # Some queries don't have a _value_ to include
        if value == None:
            cmd = "$BD:{},CMD:SET,CH:{},PAR:{}".format(self.board,
                channel, param)
        # Others do...
        else:
            cmd = "$BD:{},CMD:SET,CH:{},PAR:{},VAL:{}".format(self.board,
                channel, param, value)

        check(self.handle.query(cmd))

    # General method to sent a GET query to the power supply
    def getQuery(self, param, channel = None):
        # No channel specified for this query
        if channel == None:
            cmd = "$BD:{},CMD:MON,PAR:{}".format(self.board, param)
        # We are getting something from a specific channel
        else:
            cmd = "$BD:{},CMD:MON,CH:{},PAR:{}".format(self.board,
                channel, param)

        out = self.handle.query(cmd)
        # Clean up the returned string and extract the value
        # we're interested in...
        if check(out):
            return out.split(",")[2].split(":")[1].rstrip()

    # Channels have to be enabled before a voltage is set
    def enableChannel(self, channel):
        # Implement OFF check using status bits
        for chn in getAsList(channel):
            self.setQuery("ON", chn)

    # Disable channel and set voltage to zero. If _confirm_ is set to True
    # then wait until the actual output voltage is zero before returning.
    def disableChannel(self, channel, confirm = True):
        for chn in getAsList(channel):
            self.setVoltage(chn, 0, confirm)
            self.setQuery("OFF", chn)

    # Set output voltage for _channel_. If _confirm_ is set to True
    # then wait until the actual output voltage is at most VOLTAGE_TOLERANCE
    # away from the set value before returning.
    def setVoltage(self, channel, value, confirm = True):
        self.setQuery("VSET", channel, value)
        if confirm:
            while True:
                delta = abs(self.getVoltage(channel) - value)
                if delta < VOLTAGE_TOLERANCE:
                    break

    # Set voltage ramp up speed, in Volt/s
    def setRampUp(self, channel, value):
        for chn in getAsList(channel):
            self.setQuery("RUP", chn, value)

    # Set voltage ramp down speed, in Volt/s
    def setRampDown(self, channel, value):
        for chn in getAsList(channel):
            self.setQuery("RDW", chn, value)

    # Get voltage across _channel_, in Volts
    def getVoltage(self, channel):
        return float(self.getQuery("VMON", channel))

    # Get current flowing out of _channel_, in uA
    def getCurrent(self, channel):
        return float(self.getQuery("IMON", channel))

    # Get model string for this power supply
    def getModel(self):
        return self.model

    # Close connection to power supply
    def close(self):
        self.handle.close()
        self.connected = False

    # List all resources connected to the PC, users can choose the right one
    # by typing the correct index from the list
    def promptResource(self):
        resources = self.rm.list_resources()
        num = len(resources)
        if num == 0:
            print("Fail! No devices found, exiting.")
            exit()

        print("\nNo resource specified, please select one now...",
            end = "\n\n")

        for i, device in enumerate(resources):
            print("[{}]: {}".format(i, device),
                end = "\n" if i + 1 != num else "\n\n")

        def isValidResource(selected):
            if not str.isdigit(selected):
                return False
            selected = int(selected)
            return selected >= 0 and selected < num

        while True:
            selected = input("Resource number [0-{}]: ".format(num - 1))
            if isValidResource(selected):
                break

        return resources[int(selected)]

def getAsList(data):
    if not isinstance(data, list):
        data = [data]
    return data

def check(msg):
    if "ERR" in msg:
        print("\nPower supply: an error occurred during the last operation.")
        return False
    else:
        return True

if __name__ == "__main__":
    print("I'm a module, please don't run me alone.")
    exit()
else:
    print("[High voltage ok] ", end = "")
