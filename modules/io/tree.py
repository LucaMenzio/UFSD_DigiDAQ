import ROOT as rt
from array import array
import os, math

MAX_FILE_SIZE = 500 # GB

class TreeFile():

    def __init__(self, path, name, compression = 0):
        path = os.path.join(path, "{}.root".format(name))

        while(os.path.isfile(path)):
            path = path.replace(".root", "_.root")
        self.file = rt.TFile(path, "RECREATE", name, compression)
        self.tree = rt.TTree("wfm", "Digitizer waveforms")
        self.tree.SetMaxTreeSize(math.floor(MAX_FILE_SIZE * 10E9))

        self.bias = array("d", [0.0])
        self.tree.Branch("bias", self.bias, "bias/D")

        self.frequency = array("d", [0.0])
        self.tree.Branch("freq", self.frequency, "freq/D")

        self.length = array("d", [0.0])
        self.tree.Branch("size", self.length, "size/D")

        self.pos = rt.std.vector("double")()
        self.tree.Branch("pos", self.pos)

        self.channels = []
        for c in range(16):
            wave = rt.std.vector("double")()
            self.tree.Branch("w{}".format(c), wave)
            self.channels.append(wave)

        self.triggers = []
        for t in range(2):
            wave = rt.std.vector("double")()
            self.tree.Branch("trg{}".format(t), wave)
            self.triggers.append(wave)

    def fill(self):
        self.tree.Fill()

    def clearEvent(self):
        for c in self.channels:
            c.clear()

        for t in self.triggers:
            t.clear()

    def clearMeta(self):
        self.length[0] = 0
        self.bias[0] = 0
        self.frequency[0] = 0
        self.pos.clear()

    def write(self):
        self.file.Write()

    def close(self):
        self.file.Write()
        self.file.Close()

    def setChannel(self, index, data, length):
        channel = self.channels[index]
        channel.clear()
        for w in range(length):
            channel.push_back(float(data[w]))

    def setTrigger(self, index, data, length):
        trigger = self.triggers[index]
        trigger.clear()
        for t in range(length):
            trigger.push_back(float(data[t]))

    def setFrequency(self, frequency):
        self.frequency[0] = float(frequency)

    def setEventLength(self, length):
        self.length[0] = float(length)

    def setPosition(self, x, y):
        self.pos.clear()
        self.pos.push_back(float(x))
        self.pos.push_back(float(y))

    def setBias(self, bias):
        self.bias[0] = float(bias)
