import configparser, os

SAMPLING_FREQUENCIES = [5E3, 2.5E3, 1E3, 750] # MHz

class Config():

    def __init__(self, path = None):
        default = not path
        if not default:
            full = os.path.abspath(path)

            print("\nReading config file at {}... ".format(full))
            config = load(full)

            self.acq = config["ACQUISITION"]
            self.dgt = config["DIGITIZER"]
            self.hv = config["HIGHVOLTAGE"]
            self.stage = config["STAGE"]

            if len(self.acq["X_LIST"]) != len(self.acq["Y_LIST"]):
                print("Lists have to be the same length... Exiting")
                exit()
        else:
            self.loadDefaults()

        self.printConfig()
        print("\nDone!")

    def printConfig(self):
        print("\nFollowing settings loaded:")
        sections = [("acq", "ACQUISITION"), ("dgt", "DIGITIZER"),
            ("hv", "HIGHVOLTAGE"), ("stage", "STAGE")]
        for section in sections:
            print("\n[{}]".format(section[1]))
            data = self.__dict__[section[0]]
            for k, param in data.items():
                print("{}: {}".format(k, param))

    def loadDefaults(self):
        acq, dgt, hv, stage = {}, {}, {}, {}

        acq["MAX_EVENTS"] = 1000
        acq["MODE"] = 0

        acq["X_START"], acq["Y_START"] = 0, 0
        acq["X_END"], acq["Y_END"] = 1000, 1000
        acq["X_STEP"], acq["Y_STEP"] = 10, 10

        acq["X_LIST"], acq["Y_LIST"] = [0], [0]

        acq["DATA_PATH"] = ""
        acq["FILENAME"] = "output"
#
        dgt["DEVICE_ID"] = 0

        dgt["TRIGGER_THRESHOLD"] = 24894
        dgt["TRIGGER_OFFSET"] = 32768

        dgt["FREQUENCY"] = 0
        dgt["EVENT_LENGTH"] = 1024
        dgt["USE_INTERNAL_CORRECTION"] = True
        dgt["POST_TRIGGER_DELAY"] = 50
        dgt["CHANNEL_DC_OFFSET"] = 45000
#
        hv["MANUAL"] = False
        hv["DEVICE_ID"] = 0

        hv["SENSOR_BIAS"] = [10] # Volt
        hv["TRIGGER_BIAS"] = 10 # Volt
        hv["RAMP_UP_RATE"] = 5 # Volt/s
        hv["RAMP_DOWN_RATE"] = 25 # Volt/s
        hv["SENSOR_CHANNEL"], hv["TRIGGER_CHANNEL"] = 0, 1
#
        stage["MANUAL"] = False

        stage["X_AXIS"], stage["Y_AXIS"] = 1, 0
        stage["SPEED"] = 1500 # steps/min

        self.acq, self.dgt, self.hv, self.stage = acq, dgt, hv, stage

    def getGrid(self, inclusive = True):
        xStop = self.acq["X_END"]
        xStep = self.acq["X_STEP"]

        yStop = self.acq["Y_END"]
        yStep = self.acq["Y_STEP"]

        if inclusive:
            xStop += xStep
            yStop += yStep

        return (self.acq["X_START"], xStep, xStop,
            self.acq["Y_START"], yStep, yStop)

    def getPoints(self):
        return list(zip(self.acq["X_LIST"],
            self.acq["Y_LIST"]))

    @property
    def outputPath(self):
        return self.acq["DATA_PATH"]

    @property
    def outputFile(self):
        return self.acq["FILENAME"]

    @property
    def eventsPerPoint(self):
        return self.acq["MAX_EVENTS"]

    @property
    def mode(self):
        return self.acq["MODE"]

    @property
    def digitizerID(self):
        return self.dgt["DEVICE_ID"]

    @property
    def frequency(self):
        return self.dgt["FREQUENCY"]

    @property
    def frequencyValue(self):
        return SAMPLING_FREQUENCIES[self.frequency]

    @property
    def triggerOffset(self):
        return self.dgt["TRIGGER_OFFSET"]

    @property
    def triggerThreshold(self):
        return self.dgt["TRIGGER_THRESHOLD"]

    def isCorrectionEnabled(self):
        return self.dgt["USE_INTERNAL_CORRECTION"]

    @property
    def postTriggerDelay(self):
        return self.dgt["POST_TRIGGER_DELAY"]

    @property
    def eventSize(self):
        return self.dgt["EVENT_LENGTH"]

    @property
    def channelsOffset(self):
        try:
            value = self.dgt["CHANNEL_DC_OFFSET"]
        except:
            return None
        return value

    @property
    def hvID(self):
        return self.hv["DEVICE_ID"]

    @property
    def rampDownRate(self):
        return self.hv["RAMP_DOWN_RATE"]

    @property
    def rampUpRate(self):
        return self.hv["RAMP_UP_RATE"]

    @property
    def sensorChannel(self):
        return self.hv["SENSOR_CHANNEL"]

    @property
    def triggerChannel(self):
        return self.hv["TRIGGER_CHANNEL"]

    @property
    def triggerBias(self):
        return self.hv["TRIGGER_BIAS"]

    @property
    def sensorBiases(self):
        return self.hv["SENSOR_BIAS"]

    @property
    def powerChannels(self):
        return [self.sensorChannel, self.triggerChannel]

    def isHvAuto(self):
        return not self.hv["MANUAL"]

    @property
    def stageAxes(self):
        return {"x": self.stage["X_AXIS"], "y": self.stage["Y_AXIS"]}

    @property
    def stageSpeed(self):
        return self.stage["SPEED"]

    def isStageAuto(self):
        return not self.stage["MANUAL"]

BOOLEAN_PARAM = {"YES": True, "NO": False}
MODE_PARAM = {"SINGLE": 0, "GRID": 1, "DIAG": 2, "LIST": 3}
KEYS_ARRAY = ["SENSOR_BIAS", "X_LIST", "Y_LIST"]

def load(path):
    parser = configparser.ConfigParser()
    parser.optionxform = lambda option: option
    parser.read(path)

    def parse(key):
        # Print params and make them machine-usable
        config = {}
        for k, param in parser[key].items():
            if k in KEYS_ARRAY:
                config[k] = [int(i) for i in param[1:-1].split(",")]
            elif param in BOOLEAN_PARAM.keys():
                config[k] = BOOLEAN_PARAM[param]
            elif param in MODE_PARAM.keys():
                config[k] = MODE_PARAM[param]
            else:
                try:
                    config[k] = int(param)
                except:
                    config[k] = str(param)

        return config

    config = {key: parse(key) for key in parser.sections()}
    return config

if __name__ == "__main__":
    print("I'm a module, please don't run me alone.")
    exit()
