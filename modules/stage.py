# Standa 8MTF control module, not all original API features supported.

from ctypes import *
import urllib.parse

# Container for the transformation coefficient between steps and *meters
class CustomUnits(LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("A", c_double),
        ("MicrostepMode", c_uint)]

# List of all devices (motor controllers, axes) connected to PC
class Devices(LittleEndianStructure):
    pass

# Motor settings container
class MotorSettings(Structure):
	_fields_ = [
		("NomVoltage", c_uint),
		("NomCurrent", c_uint),
		("NomSpeed", c_uint),
		("uNomSpeed", c_uint),
		("EngineFlags", c_uint),
		("Antiplay", c_int),
		("MicrostepMode", c_uint),
		("StepsPerRev", c_uint)]

# Motion settings container
class MoveSettings(Structure):
	_fields_ = [
		("Speed", c_uint),
		("uSpeed", c_uint),
		("Accel", c_uint),
		("Decel", c_uint),
		("AntiplaySpeed", c_uint),
		("uAntiplaySpeed", c_uint),
		("MoveFlags", c_uint)]

# Position readout data container
class Position(Structure):
	_fields_ = [
		("Position", c_float),
		("EncPosition", c_longlong)]

SO_FILENAME = "libximc.so.7"
API = CDLL("/usr/lib/" + SO_FILENAME)

# Absolute maximum speed in steps/min
MAX_STEP_SPEED = 2000
# Maximum microstepping mode index, crazy accurate
USTEP_MODE_256 = 0x09
# Time to wait between subsequent polls to the controller to check if
# axes have reached their position and motors have stopped
STOP_POLL_INTERVAL = 100
# Multiplicative coefficient to convert between steps and micrometers
# =======================> AT 1/256 MICROSTEPPING MODE <=======================
# NOTE: THIS VALUE WILL BE DIFFERENT AT OTHER MODES!
CONVERSION_COEFFICIENT = 2.496 # um/step

# Each Axis class that gets instantiated controls one axis, this will be used
# in the Stage class
class Axis():

    # Connect to _id_ axis, referring to _stage_
    def __init__(self, stage, id):
        self.connected = False

        name = API.get_device_name(stage.devices, id)

        # Couldn't get the axis' handle
        if name == None:
            return

        self.axis = API.open_device(name)
        # Keep track of the original stage class
        self.stage = stage

        self.connected = True

    # Move to a specific point, relative to the origin.
    # The Standa controllers keep track of where each axis is at even
    # if powered down completely, thus the origin will remain set until
    # changed externally.
    # If _wait_ is set to True the function will wait for the motor to stop
    # before returning.
    def to(self, pos, wait = True):
        check(API.command_move_calb(self.axis, c_float(pos),
            byref(self.stage.units)))

        if wait:
            check(API.command_wait_for_stop(self.axis, STOP_POLL_INTERVAL))

    # Zero this axis, this sets the current position as the origin
    def setZero(self):
        check(API.command_zero(self.axis))

    # Set microstepping mode for this axis
    def setMicrostep(self, value):
        settings = MotorSettings()

        check(API.get_engine_settings(self.axis, byref(settings)))
        settings.MicrostepMode = value
        check(API.set_engine_settings(self.axis, byref(settings)))

        new = MotorSettings()
        check(API.get_engine_settings(self.axis, byref(new)))

    # Set speed for this axis in steps/min
    def setSpeed(self, value):
        if value > MAX_STEP_SPEED:
            print("Speed is too high!")
            return

        settings = MoveSettings()
        check(API.get_move_settings(self.axis, byref(settings)))
        settings.Speed = int(value)
        check(API.set_move_settings(self.axis, byref(settings)))

    # Get readout position from controller
    def getPosition(self):
        position = Position()
        check(API.get_position_calb(self.axis, byref(position),
            byref(self.stage.units)))

        return position.Position

    # Close connection to this axis
    def close(self):
        handle = cast(self.axis, POINTER(c_int))
        check(API.close_device(byref(handle)))
        self.connected = False

class Stage():

    # Connect to each axis
    def __init__(self, axes, units = None):
        self.devices = API.enumerate_devices(0x01, b"addr=")
        self.connected = True

        self.axes = {}
  
        for k, axis in axes.items():
            self.axes[k] = Axis(self, axis)
            self.connected &= self.axes[k].connected

        if not self.connected:
            print("Axes not connected")
            return

        # If no custom units are specified then use our own
        if units == None:
            self.units = CustomUnits()

            self.units.A = CONVERSION_COEFFICIENT
            self.units.MicrostepMode = USTEP_MODE_256
        else:
            self.units = units

        # Finally, set the microstepping mode from the custom units
        self.setMicrostep(self.units.MicrostepMode)

    # Get the number of axes connected to the PC
    def getDeviceCount(self):
        return API.get_device_count(self.devices)

    # Set the current position as the origin for all axes
    def setZero(self):
        for axis in self.axes.values():
            axis.setZero()

    # Set the microstepping mode for all axes
    def setMicrostep(self, value):
        for axis in self.axes.values():
            axis.setMicrostep(value)

    # Move to a specific point, relative to the origin.
    # The Standa controllers keep track of where each axis is at even
    # if powered down completely, thus the origin will remain set until
    # changed externally.
    # If _wait_ is set to True the function will wait for all motors to stop
    # before returning.
    def to(self, coords, wait = True):
        for k, coord in coords.items():
            self.axes[k].to(coord, wait)

    def to2d(self, x, y, wait = True):
        coords = {"x": x, "y": y}
        self.to(coords, wait)

    # Get the current position relative to the origin
    def getPosition(self):
        return [axis.getPosition() for axis in self.axes.values() ]

    # Set the speed in steps/min for all axes
    def setSpeed(self, value):
        for axis in self.axes.values():
            axis.setSpeed(value)

    # Close the connection to all axes
    def close(self):
        for axis in self.axes.values():
            axis.close()
        self.connected = False

def check(code):
    if code != 0:
        print("\nStage: an error occurred during the last operation. \
            Code: {}".format(code))

def register():
    API.enumerate_devices.restype = POINTER(Devices)
    API.get_device_name.restype = c_char_p

def __init__():
    register()

if __name__ == "__main__":
    print("I'm a module, please don't run me alone.")
    exit()
else:
    print("[Stage ok] ", end = "")
