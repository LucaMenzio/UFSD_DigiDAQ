# CAEN DT5742 control module, not all original API features supported.

from ctypes import *
import time

# ===================== PSEUDO STRUCTURES (C INHERITED) =======================

# General data about our digitizer... might be useful
class BoardInfo(Structure):
    _fields_ = [
        ("ModelName", c_char*12),
        ("Model", c_uint32),
        ("Channels", c_uint32),
        ("FormFactor", c_uint32),
        ("FamilyCode", c_uint32),
        ("ROC_FirmwareRel", c_char*20),
        ("AMC_FirmwareRel", c_char*20),
        ("SerialNumber", c_uint32),
        ("MezzanineSerNum", c_char), # Will be invalid (unused in 742)
        ("PCB_Revision", c_uint32),
        ("ADC_NBits", c_uint32),
        ("SAMCorrectionDataLoaded", c_uint32), # Will be invalid (unused in 742)
        ("CommHandle", c_int),
        ("VMEHandle", c_int),
        ("License", c_char)]

# Samples and some stats for one input group (8 channels),
# relative to one event
class Group(Structure):
    _fields_ = [
        ("ChSize", c_uint32*9),
        ("DataChannel", POINTER(c_float)*9),
        ("TriggerTimeLag", c_uint32),
        ("StartIndexCell", c_uint16)]

# Event structure, holds groups (up to four, as there are 742 models with)
# twice as many channels as our own and some stats...
class Event(Structure):
    _fields_ = [
        ("GrPresent", c_uint8*4),
        ("DataGroup", Group*4)]

# Stats about one event
class EventInfo(Structure):
    _fields_ = [
        ("EventSize", c_uint32),
        ("BoardId", c_uint32),
        ("Pattern", c_uint32),
        ("ChannelMask", c_uint32),
        ("EventCounter", c_uint32),
        ("TriggerTimeTag", c_uint32)]

SO_FILENAME = "libCAENDigitizer.so"
API = CDLL("/usr/lib/" + SO_FILENAME)

class Digitizer:

    def __init__(self, number):
        self.connected = False
        # This will keep track of the connection to our device
        self.handle = self.open(number)

        # Stores the event that's currently being processed. Is overwritten by
        # the next event as soon as decodeEvent() is called
        self.eventObject = POINTER(Event)()
        # Points to the event that's currently being processed
        self.eventPointer = POINTER(c_char)()
        # Stores some stats about the event that's currently being processed
        self.eventInfo = EventInfo()

        # Stores the last block of events transferred from the digitizer
        self.eventBuffer = POINTER(c_char)()

        # Size in memory of the event object
        self.eventAllocatedSize = c_uint32()
        # Size in memory of the events' block transfer
        self.eventBufferSize = c_uint32()
        # Need to create a **void since technically speaking other
        # kinds of Event() esist as well (the CAENDigitizer
        # library supports a multitude of devices, with different Event()
        # structures) and we need to pass this to "universal" methods.
        self.eventVoidPointer = cast(byref(self.eventObject),
            POINTER(c_void_p))

# ============================= BOARD COMMUNICATION ===========================

    # Open connection (at number)
    def open(self, number):
        device = c_long(0) # USB device
        conet = c_int(0) # Conet device (unused, set to 0)
        address = c_uint32(0) # Base address (unused, set to 0)
        handle = c_int() # Handle object, keep track of our connection

        if API.CAEN_DGTZ_OpenDigitizer(device, c_int(number),
            conet, address, byref(handle)) != 0:
            return

        self.connected = True
        return handle

    # Close connection
    def close(self):
        check(API.CAEN_DGTZ_CloseDigitizer(self.handle))
        self.connected = False

    # Reset digitizer registers
    def reset(self):
        check(API.CAEN_DGTZ_Reset(self.handle))

    # Write bytes to register at offset (address)
    def writeRegister(self, address, data):
        check(API.CAEN_DGTZ_WriteRegister(
            self.handle, c_uint32(address), c_uint32(data)))

    # Read bytes from register at address and store them in _dest_
    def readRegister(self, address, dest):
        check(API.CAEN_DGTZ_ReadRegister(
            self.handle, c_uint32(address), byref(dest)))

    # How is the digitizer going to work?
    # Mode: 0 -> Software controlled
    # ...other modes
    def setAcquisitionMode(self, mode):
        check(API.CAEN_DGTZ_SetAcquisitionMode(
            self.handle, c_long(mode)))

    # Get digitizer info (refer to BoardInfo class)
    def getInfo(self):
        info = BoardInfo()
        check(API.CAEN_DGTZ_GetInfo(self.handle, byref(info)))
        return info

    # Allocate space in memory for the event object
    def allocateEvent(self):
        check(API.CAEN_DGTZ_AllocateEvent(self.handle, self.eventVoidPointer))

    # Allocate space in memory for the events' block transfer
    def mallocBuffer(self):
        check(API.CAEN_DGTZ_MallocReadoutBuffer(
            self.handle, byref(self.eventBuffer),
            byref(self.eventAllocatedSize)))

    # Free memory that was allocated for the event object
    def freeEvent(self):
        ptr = cast(pointer(self.eventObject), POINTER(c_void_p))
        check(API.CAEN_DGTZ_FreeEvent(self.handle, ptr))

    # Free memory that was allocated for the events' block transfer
    def freeBuffer(self):
        check(API.CAEN_DGTZ_FreeReadoutBuffer(byref(self.eventBuffer)))

    # Max number of events per block transfer
    # Minimum is 1, maximum is 1023. It's recommended to set it to
    # the maximum allowed value and continuously poll the digitizer for
    # new data: binary transfer is fast while a full buffer means the digitizer
    # will discard events.
    def setMaxNumEventsBLT(self, setting):
        check(API.CAEN_DGTZ_SetMaxNumEventsBLT(
            self.handle, c_uint32(setting)))

    # Wait - read - wait - read to clear registers and get digitizer's status.
    # Funny but works.
    def status(self):
        time.sleep(0.3)
        status = c_uint32()
        self.readRegister(0x8104, status)
        time.sleep(0.2)
        self.readRegister(0x8104, status)
        return status.value

# ============================== TR0 TRIGGER ==================================

    # Set fast trigger (TR0) mode: this is the one we want to use
    # Mode: 0 -> Disabled
    # Mode: 1 -> Acquisition only
    # ...other options
    def setFastTriggerMode(self, mode):
        check(API.CAEN_DGTZ_SetFastTriggerMode(
            self.handle, c_long(mode)))

    # Set if fast trigger (TR0) should be digitized (and added to output
    # as channel 8 and 16, which means each group gets an extra column of
    # samples)
    # Setting: 0 -> DISABLED
    # Setting: 1 -> ENABLED
    def setFastTriggerDigitizing(self, setting):
        check(API.CAEN_DGTZ_SetFastTriggerDigitizing(
            self.handle, c_long(setting)))

    # Set the DC offset for the trigger channel TR0 in ADC steps.
    # Since the digitizer has 16 bit ADCs this means _offset_ takes values
    # from 0 to 65536 (= 0xFFFF, 0b1111111111111111, 2^16... you get the point)
    # It might be useful to set this to half the max value for signals that
    # span both polarities. NOTE: this seems to be rather nonlinear...
    def setFastTriggerDCOffset(self, offset):
        # For our digitizer model we only have one TRn input, shared between
        # the two groups. We only care about that one and that's what the
        # c_uint32(0) is for.
        check(API.CAEN_DGTZ_SetGroupFastTriggerDCOffset(
            self.handle, c_uint32(0), c_uint32(offset)))

    # Set TR0 trigger threshold, in ADC steps.
    # Together with setFastTriggerDCOffset this can be used to trigger
    # on positive, negative or bipolar signals.
    def setFastTriggerThreshold(self, threshold):
        # For our digitizer model we only have one TRn input, shared between
        # the two groups. We only care about that one and that's what the
        # c_uint32(0) is for.
        check(API.CAEN_DGTZ_SetGroupFastTriggerThreshold(
            self.handle, c_uint32(0), c_uint32(threshold)))

    # Set how many samples should be taken AFTER triggering, useful for
    # situations where triggering happens before the actual signal arrives.
    # This shouldn't be used to correct for trigger lag, as that is already
    # taken care by the digitizer.
    # _size_ is in percentage of the full acquisition window, thus it
    # goes from 0 to 100.
    def setPostTriggerSize(self, size):
        check(API.CAEN_DGTZ_SetPostTriggerSize(
            self.handle, c_uint32(size)))

    # Set how many samples should be taken for each event. Allowed values
    # are: 1024, 520, 256 and 136
    def setRecordLength(self, length):
        check(API.CAEN_DGTZ_SetRecordLength(
            self.handle, c_uint32(length)))

# ============================== TRG IN TRIGGER ===============================


    # Set how the TRG IN trigger should behave: we
    # want this one to be disabled
    # Mode: 0 -> Disabled
    # Mode: 1 -> Acquisition only
    def setExtTriggerInputMode(self, mode):
        check(API.CAEN_DGTZ_SetExtTriggerInputMode(
            self.handle, c_long(mode)))

# ============================== CHANNEL TRIGGER ==============================

    # Polarity: 0 -> Rising edge
    # Polarity: 1 -> Falling edge
    def setGroupTriggerPolarity(self, group, polarity):
        check(API.CAEN_DGTZ_SetTriggerPolarity(
            self.handle, c_uint32(group), c_long(polarity)));

# ============================== DATA CAPTURE =================================

    # Manually trigger the digitizer, might be useful when testing stuff...
    def trigger(self):
        check(API.CAEN_DGTZ_SendSWtrigger(
            self.handle))

    # Set sampling frequency
    # Frequency: 0 -> 5 GHz
    # ...other frequencies
    def setSamplingFrequency(self, frequency):
        check(API.CAEN_DGTZ_SetDRS4SamplingFrequency(
            self.handle, c_long(frequency)))

    # Set which groups to enable and/or disable.
    # Since our digitizer only has two groups we can enable the first one
    # (ch 0-7) by using 0b01 as mask, or the second one (ch 8-15) with 0b10.
    # Of course both groups will be enabled using 0b11 and disabled with 0b00.
    # If our model had 4 groups we could've used 0b1111 or 0xF to enable all
    # of them. THERE IS NO WAY TO ENABLE OR DISABLE SINGLE CHANNELS SELECTIVELY.
    def setGroupEnableMask(self, mask):
        check(API.CAEN_DGTZ_SetGroupEnableMask(
            self.handle, c_uint32(mask)))

    # Set the DC offset for a particular channel (0-15) in ADC steps.
    # Since the digitizer has 16 bit ADCs this means _offset_ takes values
    # from 0 to 65536 (= 0xFFFF, 0b1111111111111111, 2^16... you get the point)
    # It might be useful to set this to half the max value for signals that
    # span both polarities.
    def setChannelDCOffset(self, channel, offset):
        check(API.CAEN_DGTZ_SetChannelDCOffset(
            self.handle, c_uint32(channel), c_uint32(offset)))

    def getChannelDCOffset(self, channel):
        value = c_uint32(0)
        check(API.CAEN_DGTZ_GetChannelDCOffset(
            self.handle, c_uint32(channel), byref(value)))

        return value

    # Start listening for triggers
    def startAcquisition(self):
        check(API.CAEN_DGTZ_SWStartAcquisition(self.handle))

    # Stop listening for triggers
    def stopAcquisition(self):
        check(API.CAEN_DGTZ_SWStopAcquisition(self.handle))

    # Start an event block transfer and put all data in eventBuffer.
    # eventBufferSize will contain the length of the event.
    def readData(self):
        check(API.CAEN_DGTZ_ReadData(
            self.handle, c_long(0), self.eventBuffer,
            byref(self.eventBufferSize)))

    # Get the number of EVENTS contained in the last block transfer initiated,
    # and therefore in eventBuffer.
    def getNumEvents(self):
        eventNumber = c_uint32()
        check(API.CAEN_DGTZ_GetNumEvents(
            self.handle, self.eventBuffer, self.eventBufferSize,
            byref(eventNumber)))

        return eventNumber.value

    # Fill the eventInfo object declared in __init__ with stats from
    # the i-th event in the buffer (and thus from the last block transfer).
    # At the end of this function eventPointer will point to the i-th event.
    def getEventInfo(self, index):
        check(API.CAEN_DGTZ_GetEventInfo(
            self.handle, self.eventBuffer, self.eventBufferSize, c_uint32(index),
            byref(self.eventInfo), byref(self.eventPointer)))

        return self.eventInfo

    # Decode the event in eventPointer and put all data in the eventObject
    # created in __init__. eventPointer is filled by calling getEventInfo first.
    def decodeEvent(self):
        check(API.CAEN_DGTZ_DecodeEvent(
            self.handle, self.eventPointer, self.eventVoidPointer))

        return self.eventObject.contents

    # Get event data without having to call getEventInfo first. If event
    # info is to be returned as well, pass wantInfo = True.
    def getEvent(self, index, wantInfo = False):
        info = self.getEventInfo(index)
        event = self.decodeEvent()
        if wantInfo:
            return event, info
        else:
            return event

    # Load correction tables from digitizer's memory at right frequency.
    def loadCorrectionData(self, frequency):
        check(API.CAEN_DGTZ_LoadDRS4CorrectionData(
            self.handle, c_long(frequency)))

    # Enable raw data correction using tables loaded with loadCorrectionData.
    # This corrects for slight differences in ADC capacitors' values and
    # different latency between the two groups' circutry. Refer to manual for
    # more.
    def enableCorrection(self):
        check(API.CAEN_DGTZ_EnableDRS4Correction(
            self.handle))

# ======================== UTIL FUNCTIONS =====================================

# Simply check that the API function returned 0L
def check(code):
    if code != 0:
        print("\nDigitizer: an error occurred during the last operation. \
            Code: {}".format(code))

# All digitizer functions return a long, indicating the operation outcome.
# Make ctypes be aware of that.
def register(*ext):
    for func in ext:
        func.restype = c_long

def __init__():
    register(API.CAEN_DGTZ_OpenDigitizer,
        API.CAEN_DGTZ_CloseDigitizer,
        API.CAEN_DGTZ_Reset,
        API.CAEN_DGTZ_WriteRegister,
        API.CAEN_DGTZ_ReadRegister,
        API.CAEN_DGTZ_SetAcquisitionMode,
        API.CAEN_DGTZ_GetInfo,
        API.CAEN_DGTZ_AllocateEvent,
        API.CAEN_DGTZ_MallocReadoutBuffer,
        API.CAEN_DGTZ_FreeEvent,
        API.CAEN_DGTZ_FreeReadoutBuffer,
        API.CAEN_DGTZ_SetMaxNumEventsBLT,
#
        API.CAEN_DGTZ_SetFastTriggerMode,
        API.CAEN_DGTZ_SetFastTriggerDigitizing,
        API.CAEN_DGTZ_SetGroupFastTriggerDCOffset,
        API.CAEN_DGTZ_SetGroupFastTriggerThreshold,
        API.CAEN_DGTZ_SetPostTriggerSize,
        API.CAEN_DGTZ_SetRecordLength,
#
        API.CAEN_DGTZ_SetExtTriggerInputMode,
#
        API.CAEN_DGTZ_SetTriggerPolarity,
#
        API.CAEN_DGTZ_SendSWtrigger,
        API.CAEN_DGTZ_SetDRS4SamplingFrequency,
        API.CAEN_DGTZ_SetGroupEnableMask,
        API.CAEN_DGTZ_SetChannelDCOffset,
        API.CAEN_DGTZ_GetChannelDCOffset,
        API.CAEN_DGTZ_SWStartAcquisition,
        API.CAEN_DGTZ_SWStopAcquisition,
        API.CAEN_DGTZ_ReadData,
        API.CAEN_DGTZ_GetNumEvents,
        API.CAEN_DGTZ_GetEventInfo,
        API.CAEN_DGTZ_DecodeEvent,
        API.CAEN_DGTZ_LoadDRS4CorrectionData,
        API.CAEN_DGTZ_EnableDRS4Correction)

if __name__ == "__main__":
    print("I'm a module, please don't run me alone.")
    exit()
else:
    print("[Digitizer ok] ", end = "")
