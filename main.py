from modules import *
import sys, os, datetime, time

CONFIG_PATH = "config.ini"

DIGITIZER_MODELS = ["DT5742"]
HIGHVOLTAGE_MODELS = ["DT1471ET", "DT1470ET"]

class UFSDPyDAQ:

    def __init__(self, config):
        self.config = config

        # PyUSB acts weird if we try to connect the digitizer first...
        self.connectHighVoltage()

        self.connectStage()
        self.programStage()

        self.connectDigitizer()
        self.programDigitizer()
        status = self.dgt.status()
        print("Digitizer status is {}, ".format(hex(status)), end = "")
        if status == 0x180:
            formatted(" good!", FORMAT_OK)
        else:
            formatted("something's wrong. Exiting.", FORMAT_ERROR)
            exit()
        self.dgt.allocateEvent()
        self.dgt.mallocBuffer()

    def prepare(self):
        dir = self.config.outputPath
        if not os.path.exists(dir):
            os.mkdir(dir)
        self.file = io.tree.TreeFile(dir, self.config.outputFile)

        self.file.setFrequency(self.config.frequencyValue)
        self.file.setEventLength(self.config.eventSize)

        self.hv.enableChannel(self.config.powerChannels)
        self.hvSetBlocking(self.config.triggerChannel,
            self.config.triggerBias)

        if input("Start acquisition? [y/n] ") == "n":
            return False
        else:
            return True

    def acquire(self):
        (xStart, xStep, xStop,
            yStart, yStep, yStop) = self.config.getGrid(inclusive = True)

        for bias in self.config.sensorBiases:
            self.hvSetBlocking(self.config.sensorChannel, bias)
            self.file.setBias(bias)
            formatted("\nNow acquiring with sensor bias at {} V".format(bias),
                FORMAT_NOTE)

            if not self.askSkipQuit(self.config.isHvAuto()):
                continue

            mode = self.config.mode
            # Single point
            if mode == 0:
                self.acquirePoint(xStart, yStart)
            # Grid acquisition
            elif mode == 1:
                for x in range(xStart, xStop, xStep):
                    for y in range(yStart, yStop, yStep):
                        self.acquirePoint(x, y)
            # Diagonal acquisition
            elif mode == 2:
                xRatioEnd = xEnd - xStep
                yRatioEnd = yEnd - yStep
                aspectRatio = (yRatioEnd - yStart) / (xRatioEnd - xStart)

                for x in range(xStart, xStop, xStep):
                    y = yStart + ((x - xStart) * aspectRatio)
                    self.acquirePoint(x, y)
            elif mode == 3:
                points = self.config.getPoints()
                for point in points:
                    self.acquirePoint(point[0], point[1])

    def acquirePoint(self, x, y):
        target = self.config.eventsPerPoint
        formatted("\nNow acquiring {} events at (x = {}, y = {})".format(
            target, x, y), FORMAT_NOTE, "")

        self.stage.to2d(x, y, True)
        if self.config.isStageAuto():
            position = self.stage.getPosition()
            formatted("Current position is (x = {:.3f}, y = {:.3f})".format(
                position[0], position[1]), FORMAT_NOTE)

        if not self.askSkipQuit(self.config.isStageAuto()):
            return
        self.file.setPosition(x, y)

        events = 0
        self.dgt.startAcquisition()
        while True:
            events += self.poll(events, target)
            #print(events)
            if events >= target:
                formatted("Acquired {}/{} events.".format(events,
                    target), FORMAT_OK, "")
                break
        self.dgt.stopAcquisition()

        self.file.write()

    def poll(self, taken, target):
        self.dgt.readData() # Update local buffer with data from the digitizer

        size = self.dgt.getNumEvents() # How many events in this block?
        remaining = min(size, target - taken)
        for i in range(remaining):
            data, info = self.dgt.getEvent(i, True) # Get event data and info

            for j in range(18):
                group = int(j / 9)
                if data.GrPresent[group] != 1:
                    continue # If this group was disabled then skip it

                channel = j - (9 * group)
                block = data.DataGroup[group]
                size = block.ChSize[channel]

                if channel == 8:
                    self.file.setTrigger(group,
                        block.DataChannel[channel], size)
                else:
                    self.file.setChannel(j - group,
                        block.DataChannel[channel], size)

            self.file.fill()
        return remaining

    def cleanup(self):
        self.file.close()

        formatted("\nDigitizer cleanup... ", FORMAT_NOTE, "")
        self.dgt.stopAcquisition()
        self.dgt.freeEvent()
        self.dgt.freeBuffer()
        formatted("Done!", FORMAT_OK)

        formatted("Closing connection to digitizer... ", FORMAT_NOTE, "")
        self.dgt.close()
        formatted("Done!", FORMAT_OK)

        if self.config.isHvAuto():
            formatted("Power supply cleanup... ", FORMAT_NOTE, "")
            self.hv.disableChannel(self.config.powerChannels)
            formatted("Done!", FORMAT_OK)

            formatted("Closing connection to power supply... ", FORMAT_NOTE, "")
            self.hv.close()
            formatted("Done!", FORMAT_OK)

        if self.config.isStageAuto():
            formatted("Stage cleanup... ", FORMAT_NOTE, "")


            self.stage.to2d(0, 0)
            formatted("Done!", FORMAT_OK)
            
            formatted("Closing connection to stage...", FORMAT_NOTE, "")
            self.stage.close()
            formatted("Done!", FORMAT_OK)

        formatted("Exiting, goodbye...", FORMAT_NOTE, "")

# ============================ STAGE STUFF ====================================

    def connectStage(self):
        if not self.config.isStageAuto():
            self.stage = Nothing()
            return False

        formatted("Connecting to stage...", FORMAT_NOTE, "")
        self.stage = stage.Stage(self.config.stageAxes)

        if not self.stage.connected:
            formatted("Fail! Couldn't connect to stage, exiting.",
                FORMAT_ERROR)
            exit()

        formatted("Done! Hello stage...", FORMAT_OK)
        return True

    def programStage(self):
        self.stage.setSpeed(self.config.stageSpeed)

# ========================= HIGH VOLTAGE STUFF ================================

    def connectHighVoltage(self):
        if not self.config.isHvAuto():
            self.hv = Nothing()
            return False

        formatted("\nConnecting to power supply... ", FORMAT_NOTE, end = "")
        self.hv = highvoltage.HighVoltage(self.config.hvID)
        if not self.hv.connected:
            formatted("Fail!", "Couldn't connect to device, exiting.",
                FORMAT_ERROR)
            exit()

        hvModel = self.hv.getModel()
        if not hvModel in HIGHVOLTAGE_MODELS:
            formatted("Fail! This model is not supported, exiting.",
                FORMAT_ERROR)
            exit()
        formatted("Done! Hello " + hvModel, FORMAT_OK)
        return True

    def programHighVoltage(self):
        self.hv.setRampUp(self.config.powerChannels,
            self.config.rampUpRate)
        self.hv.setRampDown(self.config.powerChannels,
            self.config.rampDownRate)

    def hvSetBlocking(self, channel, bias):
        if self.config.isHvAuto():
            formatted("\nWaiting for power supply... ", FORMAT_NOTE, "")
            self.hv.setVoltage(channel, bias, True)
            formatted("Ready!", FORMAT_OK)

# ========================= DIGITIZER STUFF ===================================

    def connectDigitizer(self):
        formatted("\nConnecting to digitizer... ", FORMAT_NOTE, "")
        self.dgt = digitizer.Digitizer(self.config.digitizerID)
        if not self.dgt.connected:
            formatted("Fail! Couldn't connect to device, exiting.",
                FORMAT_ERROR)
            exit()

        self.dgt.reset()
        dgtInfo = self.dgt.getInfo()
        dgtModel = str(dgtInfo.ModelName, "utf-8")
        if dgtModel not in DIGITIZER_MODELS:
            formatted("Fail! This model is not supported, exiting.",
                FORMAT_ERROR)
            exit()

        formatted("Done! Hello " + dgtModel, FORMAT_OK)
        return True

    def programDigitizer(self):
        formatted("Programming digitizer... ", FORMAT_NOTE, end = "")
        # Data acquisition
        self.dgt.setSamplingFrequency(self.config.frequency)
        self.dgt.setRecordLength(self.config.eventSize)
        self.dgt.setMaxNumEventsBLT(1023) # Packet size for file transfer
        self.dgt.setAcquisitionMode(0) # Software controlled
        self.dgt.setExtTriggerInputMode(0) # Disable TRG IN trigger

        self.dgt.writeRegister(0x811C, 0x000D0001) # Enable busy signal on GPO
        # device.writeRegister(0x8004, 1<<3) # Enable test pattern

        self.dgt.setFastTriggerMode(1) # Enable TR0 trigger
        self.dgt.setFastTriggerDigitizing(1) # Digitize TR0

        # Enable or disable groups
        self.dgt.setGroupEnableMask(0b11)

        channelOffset = self.config.channelsOffset
        if channelOffset != None:
            for i in range(16):
                self.dgt.setChannelDCOffset(i, channelOffset)

        # Positive polarity signals for both groups, unused but doesn't hurt
        self.dgt.setGroupTriggerPolarity(0, 0)
        self.dgt.setGroupTriggerPolarity(1, 0)

        self.dgt.setFastTriggerDCOffset(self.config.triggerOffset)
        self.dgt.setFastTriggerThreshold(self.config.triggerThreshold)

        # Data processing
        if self.config.isCorrectionEnabled():
            # Correction tables for 5 GHz operation
            self.dgt.loadCorrectionData(self.config.frequency)
            self.dgt.enableCorrection()

        # Extra time after trigger
        self.dgt.setPostTriggerSize(self.config.postTriggerDelay)
        formatted("Done!", FORMAT_OK)

    def askSkipQuit(self, bypass):
        if bypass:
            return True

        prompt = input("Press enter to continue, type 's' to skip or 'q' to quit... ")
        if prompt == "s":
            return False
        elif prompt == "q":
            self.dgt.stopAcquisition()

            self.cleanup()
            exit()
        return True

# ============================= UI SERVICES ===================================

FORMAT_ERROR = "\033[91m"
FORMAT_WARNING = "\033[93m"
FORMAT_NOTE = "\033[94m"
FORMAT_OK = "\033[92m"

def formatted(string, format, end = "\n"):
    print(format, end = "")
    sys.stdout.write("\b")
    print(string, "\033[0m", end)

class Nothing():

    def __init__(self, *args, **kwargs):
        self.connected = True

    def __getattr__(self, attr):
        def bye(*args, **kwargs):
            pass
        return bye

if __name__ == "__main__":
    args = sys.argv

    configPath = CONFIG_PATH
    if len(args) == 2:
        configPath = args[1]

    config = io.config.Config(configPath)

    daq = UFSDPyDAQ(config)
    
    if daq.prepare():
        daq.acquire()
        #discord_alert()  

    daq.cleanup()
else:
    print("Please don't run me as a module...")
    exit()
