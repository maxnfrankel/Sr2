from labrad.server import ThreadedServer, Signal, setting, LabradServer

import ctypes
import numpy as np
from picosdk.ps5000a import ps5000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc

# uses example code from https://github.com/picotech/picosdk-python-wrappers/blob/master/ps5000aExamples/ps5000aBlockExample.py
# combined with Will Milner's picoscope_labrad_server.py code

class PicoscopeServer(ThreadedServer):
    name = '%LABRADNODE%_picoscope'
    update = Signal(698461, 'signal: update', 's') # not sure what this does

    def initServer(self):
          
        ## IMPORTANT PARAMETERS ##

        self.timebase = 66 # determines sampling rate for 12-bit operation. (n-3)/62,500,000 ns. See page 28 of picotech.com/download/manuals/picoscope-5000-series-a-api-programmers-guide.pdf
        self.preTriggerSamples = 5000 # Set number of pre and post trigger samples to be collected
        self.postTriggerSamples = 5000
        self.maxSamples = self.preTriggerSamples + self.postTriggerSamples

        self.serial_no = ctypes.create_string_buffer(bytes('IV947/0114',encoding='utf-8'))
        # Resolution set to 12 Bit
        self.resolution = ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_12BIT"]

    @setting(11)
    def get_data(self, path):
            ## PICOSDK CODE ##
            
        # Create chandle and self.status ready for use
        chandle = ctypes.c_int16()
        self.status = {}

        # Open 5000 series PicoScope
        # Returns handle to chandle for use in future API functions
        self.status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(chandle), self.serial_no, self.resolution)

        try:
            assert_pico_ok(self.status["openunit"])
        except: # PicoNotOkError:

            powerStatus = self.status["openunit"]

            if powerStatus == 286:
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(chandle, powerStatus)
            elif powerStatus == 282:
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(chandle, powerStatus)
            else:
                raise

            assert_pico_ok(self.status["changePowerSource"])

        # Set up channel A
        # handle = chandle
        channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        # enabled = 1
        coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
        chARange = ps.PS5000A_RANGE["PS5000A_20V"]
        # analogue offset = 0 V
        self.status["setChA"] = ps.ps5000aSetChannel(chandle, channel, 1, coupling_type, chARange, 0)
        assert_pico_ok(self.status["setChA"])

        # find maximum ADC count value
        # handle = chandle
        # pointer to value = ctypes.byref(maxADC)
        maxADC = ctypes.c_int16()
        self.status["maximumValue"] = ps.ps5000aMaximumValue(chandle, ctypes.byref(maxADC))
        assert_pico_ok(self.status["maximumValue"])

        # Set up single trigger
        # handle = chandle
        # enabled = 1
        source = ps.PS5000A_CHANNEL["PS5000A_EXTERNAL"]
        threshold = int(mV2adc(500,chARange, maxADC))
        # direction = PS5000A_RISING = 2
        # delay = 0 s
        # auto Trigger = 1000 ms
        self.status["trigger"] = ps.ps5000aSetSimpleTrigger(chandle, 1, source, threshold, 2, 0, 0) # (handle, enable, source, threshold, direction, delay, autoTrigger_ms)

        assert_pico_ok(self.status["trigger"])

        # Set number of pre and post trigger samples to be collected
        #self.preTriggerSamples = 5000
        #self.postTriggerSamples = 5000
        #self.maxSamples = self.preTriggerSamples + self.postTriggerSamples

        # Get self.timebase information
        # Warning: When using this example it may not be possible to access all Timebases as all channels are enabled by default when opening the scope.  
        # To access these Timebases, set any unused analogue channels to off.
        # handle = chandle
        #self.timebase = 8
        # noSamples = self.maxSamples
        # pointer to timeIntervalNanoseconds = ctypes.byref(timeIntervalns)
        # pointer to self.maxSamples = ctypes.byref(returnedMaxSamples)
        # segment index = 0
        timeIntervalns = ctypes.c_float()
        returnedMaxSamples = ctypes.c_int32()
        self.status["getTimebase2"] = ps.ps5000aGetTimebase2(chandle, self.timebase, self.maxSamples, ctypes.byref(timeIntervalns), ctypes.byref(returnedMaxSamples), 0)
        assert_pico_ok(self.status["getTimebase2"])

        # Run block capture
        # handle = chandle
        # number of pre-trigger samples = self.preTriggerSamples
        # number of post-trigger samples = PostTriggerSamples
        # self.timebase = 8 = 80 ns (see Programmer's guide for mre information on self.timebases)
        # time indisposed ms = None (not needed in the example)
        # segment index = 0
        # lpReady = None (using ps5000aIsReady rather than ps5000aBlockReady)
        # pParameter = None
        self.status["runBlock"] = ps.ps5000aRunBlock(chandle, self.preTriggerSamples, self.postTriggerSamples, self.timebase, None, 0, None, None)
        assert_pico_ok(self.status["runBlock"])

        # Check for data collection to finish using ps5000aIsReady
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        while ready.value == check.value:
            self.status["isReady"] = ps.ps5000aIsReady(chandle, ctypes.byref(ready))

        # Create buffers ready for assigning pointers for data collection
        bufferAMax = (ctypes.c_int16 * self.maxSamples)()
        bufferAMin = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example

        # Set data buffer location for data collection from channel A
        # handle = chandle
        source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        # pointer to buffer max = ctypes.byref(bufferAMax)
        # pointer to buffer min = ctypes.byref(bufferAMin)
        # buffer length = self.maxSamples
        # segment index = 0
        # ratio mode = PS5000A_RATIO_MODE_NONE = 0
        self.status["setDataBuffersA"] = ps.ps5000aSetDataBuffers(chandle, source, ctypes.byref(bufferAMax), ctypes.byref(bufferAMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersA"])

        # create overflow loaction
        overflow = ctypes.c_int16()
        # create converted type self.maxSamples
        self.cmaxSamples = ctypes.c_int32(self.maxSamples)

        # Retried data from scope to buffers assigned above
        # handle = chandle
        # start index = 0
        # pointer to number of samples = ctypes.byref(self.cmaxSamples)
        # downsample ratiao = 0
        # downsample ratio mode = PS5000A_RATIO_MODE_NONE
        # pointer to overflow = ctypes.byref(overflow))
        self.status["getValues"] = ps.ps5000aGetValues(chandle, 0, ctypes.byref(self.cmaxSamples), 0, 0, 0, ctypes.byref(overflow))
        assert_pico_ok(self.status["getValues"])

        # convert ADC counts data to mV
        adc2mVChAMax =  adc2mV(bufferAMax, chARange, maxADC)

        # Stop the scope
        # handle = chandle
        self.status["stop"] = ps.ps5000aStop(chandle)
        assert_pico_ok(self.status["stop"])

        # Close unit Disconnect the scope
        # handle = chandle
        self.status["close"]=ps.ps5000aCloseUnit(chandle)
        assert_pico_ok(self.status["close"])

        # display self.status returns
        #print(self.status)

            ## SAVING DATA ##

        # Create time data
        time = np.linspace(-self.preTriggerSamples*timeIntervalns.value, (self.postTriggerSamples - 1) * timeIntervalns.value, self.cmaxSamples.value)

        print(f'Picoscope trace saved at {path}')

        """
        # save data as a packed file
        packed = {}
        packed["time_ns"] = time
        packed["ChA_mV"] = adc2mVChAMax
        np.savez(path,**packed)
        """
        
        
Server = PicoscopeServer
if __name__ == "__main__":
    from labrad import util
    util.runServer(Server())
