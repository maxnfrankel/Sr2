# this is in python2

from labrad.server import ThreadedServer, Signal, setting, LabradServer, inlineCallbacks

import ctypes
import numpy as np
from picosdk.ps5000a import ps5000a as ps5
from picosdk.ps3000a import ps3000a as ps3
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
import h5py

# uses example code from https://github.com/picotech/picosdk-python-wrappers/blob/master/ps5000aExamples/ps5000aBlockExample.py
# combined with Will Milner's picoscope_labrad_server.py code

class PicoscopeServer(ThreadedServer):
    name = '%LABRADNODE%_picoscope'
    update = Signal(698461, 'signal: update', 's') # not sure what this does

    def initServer(self):

        # Create chandle and self.status ready for use
        self.chandle = ctypes.c_int16()
        self.status = {}
    """
    @setting(1)
    def set_recordduration_5000a(self,c,duration,presamples,postsamples):

        #self.timebase = 627 # 5us per sample # determines sampling rate. (n-2)/125000000 s/sample for both 15-bit operation on the ps5000a and 8-bit on the ps3000a 
            # See page 28 of picotech.com/download/manuals/picoscope-5000-series-a-api-programmers-guide.pdf
            # See page 15 of https://www.picotech.com/download/manuals/picoscope-3000-series-a-api-programmers-guide.pdf
        #self.preTriggerSamples = 0 # Set number of pre and post trigger samples to be collected
        #self.postTriggerSamples = 10000
        #self.maxSamples = self.preTriggerSamples + self.postTriggerSamples
        
        self.preTriggerSamples = presamples # Set number of pre and post trigger samples to be collected
        self.postTriggerSamples = postsamples
        self.maxSamples = self.preTriggerSamples + self.postTriggerSamples
        self.timebase = round(duration/self.maxSamples*125000000 + 2)
    """

    @setting(2)
    def set_recordduration(self,c,duration,presamples,postsamples):

        # we want to sample x32 more and then average back down to try to make up for the 5 less bits of resolution
        # TODO: make a separate command for ps3000a and ps5000a in the future

        #self.timebase = 627 # 5us per sample # determines sampling rate. (n-2)/125000000 s/sample for both 15-bit operation on the ps5000a and 8-bit on the ps3000a 
            # See page 28 of picotech.com/download/manuals/picoscope-5000-series-a-api-programmers-guide.pdf
            # See page 15 of https://www.picotech.com/download/manuals/picoscope-3000-series-a-api-programmers-guide.pdf
        #self.preTriggerSamples = 0 # Set number of pre and post trigger samples to be collected
        #self.postTriggerSamples = 10000
        #self.maxSamples = self.preTriggerSamples + self.postTriggerSamples
        
        self.preTriggerSamples = presamples*32 # Set number of pre and post trigger samples to be collected
        self.postTriggerSamples = postsamples*32
        self.maxSamples = self.preTriggerSamples + self.postTriggerSamples
        self.timebase = round(duration/self.maxSamples*125000000 + 2)

        print(f'\ndur={duration}s timebase={self.timebase} pre_trig_samples={presamples} post_trig_samples={postsamples} x32 sampling but avged back down again')
    
    @setting(3)
    def get_data_5000a(self,c,path):
        # based off of https://github.com/picotech/picosdk-python-wrappers/blob/master/ps5000aExamples/ps5000aBlockExample.py

            ## PICOSDK CODE ##

        self.serial_no = ctypes.create_string_buffer(bytes('IV947/0114',encoding='utf-8'))
        # Resolution set to 12 Bit
        self.resolution = ps5.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_15BIT"]

        # Open 5000 series PicoScope
        # Returns handle to chandle for use in future API functions
        self.status["openunit"] = ps5.ps5000aOpenUnit(ctypes.byref(self.chandle), self.serial_no, self.resolution)

        try:
            assert_pico_ok(self.status["openunit"])
        except: # PicoNotOkError:

            powerStatus = self.status["openunit"]

            if powerStatus == 286:
                self.status["changePowerSource"] = ps5.ps5000aChangePowerSource(self.chandle, powerStatus)
            elif powerStatus == 282:
                self.status["changePowerSource"] = ps5.ps5000aChangePowerSource(self.chandle, powerStatus)
            else:
                raise

            assert_pico_ok(self.status["changePowerSource"])

        # Set up channel A
        # handle = chandle
        channel = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        # enabled = 1
        coupling_type = ps5.PS5000A_COUPLING["PS5000A_DC"]
        # chARange = ps.PS5000A_RANGE["PS5000A_10V"]
        chARange = ps5.PS5000A_RANGE["PS5000A_5V"]
        # analogue offset = 5 V
        analog_offset=0#-5
        self.status["setChA"] = ps5.ps5000aSetChannel(self.chandle, channel, 1, coupling_type, chARange, analog_offset)
        assert_pico_ok(self.status["setChA"])

        # Set up channel B
        # handle = chandle
        channel = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
        # enabled = 1
        # coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
        chBRange = ps5.PS5000A_RANGE["PS5000A_5V"]
        # analogue offset = 5 V
        self.status["setChB"] = ps5.ps5000aSetChannel(self.chandle, channel, 1, coupling_type, chBRange, analog_offset)
        assert_pico_ok(self.status["setChB"])

        # find maximum ADC count value
        # handle = chandle
        # pointer to value = ctypes.byref(maxADC)
        maxADC = ctypes.c_int16()
        self.status["maximumValue"] = ps5.ps5000aMaximumValue(self.chandle, ctypes.byref(maxADC))
        assert_pico_ok(self.status["maximumValue"])

        # Set up single trigger
        # handle = chandle
        enabled = 1
        source = ps5.PS5000A_CHANNEL["PS5000A_EXTERNAL"]
        threshold = int(mV2adc(500,chARange, maxADC)) # def of mV2adc: https://github.com/picotech/picosdk-python-wrappers/blob/master/picosdk/functions.py#L42
        # direction = PS5000A_RISING = 2
        direction =  2
        delay = 0 # s
        autoTrigger_ms = 0 # setting to 0 makes scope wate indefinitely for a trigger - see page 115 of ps5000a programmer's guide
        self.status["trigger"] = ps5.ps5000aSetSimpleTrigger(self.chandle, enabled, source, threshold, enabled, delay, autoTrigger_ms) # (handle, enable, source, threshold, direction, delay, autoTrigger_ms)

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
        self.status["getTimebase2"] = ps5.ps5000aGetTimebase2(self.chandle, self.timebase, self.maxSamples, ctypes.byref(timeIntervalns), ctypes.byref(returnedMaxSamples), 0)
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
        self.status["runBlock"] = ps5.ps5000aRunBlock(self.chandle, self.preTriggerSamples, self.postTriggerSamples, self.timebase, None, 0, None, None)
        assert_pico_ok(self.status["runBlock"])

        # Check for data collection to finish using ps5000aIsReady
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        while ready.value == check.value:
            self.status["isReady"] = ps5.ps5000aIsReady(self.chandle, ctypes.byref(ready))

        # Create buffers ready for assigning pointers for data collection
        bufferAMax = (ctypes.c_int16 * self.maxSamples)()
        bufferAMin = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example
        bufferBMax = (ctypes.c_int16 * self.maxSamples)()
        bufferBMin = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example

        # Set data buffer location for data collection from channel A
        # handle = chandle
        source = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        # pointer to buffer max = ctypes.byref(bufferAMax)
        # pointer to buffer min = ctypes.byref(bufferAMin)
        # buffer length = self.maxSamples
        # segment index = 0
        # ratio mode = PS5000A_RATIO_MODE_NONE = 0
        self.status["setDataBuffersA"] = ps5.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferAMax), ctypes.byref(bufferAMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersA"])

        # Set data buffer location for data collection from channel B
        # handle = chandle
        source = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
        # pointer to buffer max = ctypes.byref(bufferBMax)
        # pointer to buffer min = ctypes.byref(bufferBMin)
        # buffer length = maxSamples
        # segment index = 0
        # ratio mode = PS5000A_RATIO_MODE_NONE = 0
        self.status["setDataBuffersB"] = ps5.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferBMax), ctypes.byref(bufferBMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersB"])

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
        self.status["getValues"] = ps5.ps5000aGetValues(self.chandle, 0, ctypes.byref(self.cmaxSamples), 0, 0, 0, ctypes.byref(overflow))
        assert_pico_ok(self.status["getValues"])

        # convert ADC counts data to mV
        adc2mVChAMax =  adc2mV(bufferAMax, chARange, maxADC)
        adc2mVChBMax =  adc2mV(bufferBMax, chBRange, maxADC)

        # Stop the scope
        # handle = chandle
        self.status["stop"] = ps5.ps5000aStop(self.chandle)
        assert_pico_ok(self.status["stop"])

        # Close unit Disconnect the scope
        # handle = chandle
        self.status["close"]=ps5.ps5000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])

        # display self.status returns
        #print(self.status)

            ## SAVING DATA ##

        # Create time data
        time = np.linspace(-self.preTriggerSamples*timeIntervalns.value, (self.postTriggerSamples - 1) * timeIntervalns.value, self.cmaxSamples.value)
        
        #"""
        # save data as a packed file
        packed = {}
        packed["time_ns"] = time
        packed["ChA_mV"] = adc2mVChAMax #- analog_offset*1e3 # Add the analog offset (which I believe is in V) to the mV trace
        packed["ChB_mV"] = adc2mVChBMax #- analog_offset*1e3
        np.savez(path,**packed)
        #"""
        
        print(f'Picoscope trace saved at {path}')

    @setting(4)
    def get_data_3000a(self,c,path): 
        # initially from https://github.com/picotech/picosdk-python-wrappers/blob/master/ps5000aExamples/ps5000aBlockExample.py
        # modified to match https://github.com/picotech/picosdk-python-wrappers/blob/master/ps3000aExamples/ps3000aBlockExample.py

            ## PICOSDK CODE ##
            

        self.serial_no = ctypes.create_string_buffer(bytes('IU888/0102',encoding='utf-8'))
        # ps3000a doesn't seem to have the option to set device resolution

        # Open 3000 series PicoScope
        # Returns handle to chandle for use in future API functions
        self.status["openunit"] = ps3.ps3000aOpenUnit(ctypes.byref(self.chandle), self.serial_no)

        try:
            assert_pico_ok(self.status["openunit"])
        except: # PicoNotOkError:

            powerStatus = self.status["openunit"]

            if powerStatus == 286:
                self.status["ChangePowerSource"] = ps3.ps3000aChangePowerSource(self.chandle, powerStatus)
            elif powerStatus == 282:
                self.status["ChangePowerSource"] = ps3.ps3000aChangePowerSource(self.chandle, powerStatus)
            else:
                raise

            assert_pico_ok(self.status["ChangePowerSource"])
    
        # STOPPED FOR THE DAY HERE
        # picked up 6/17/24

        # Set up channel A
        # handle = chandle
        # channel = PS3000A_CHANNEL_A = 0
        channel = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_A"]
        enabled = 1
        # coupling_type = PS3000A_10V = 1
        coupling_type = ps3.PS3000A_COUPLING["PS3000A_DC"]
        # range = PS3000A_10V = 8
        chARange = ps3.PS3000A_RANGE["PS3000A_10V"]
        # analogue offset = 0 V
        analog_offset=0
        self.status["setChA"] = ps3.ps3000aSetChannel(self.chandle, channel, enabled, coupling_type, chARange, analog_offset)
        assert_pico_ok(self.status["setChA"])

        # Set up channel B
        # handle = chandle
        # channel = PS3000A_CHANNEL_B = 1
        channel = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_B"]

        # enabled = 1
        # coupling_type = PS3000A_10V = 1
        coupling_type = ps3.PS3000A_COUPLING["PS3000A_DC"]
        # range = PS3000A_10V = 8
        chBRange = ps3.PS3000A_RANGE["PS3000A_10V"]
        # analogue offset = 0 V
        analog_offset=0
        self.status["setChB"] = ps3.ps3000aSetChannel(self.chandle, channel, enabled, coupling_type, chBRange, analog_offset)
        assert_pico_ok(self.status["setChB"])

        # Set up channel C
        # handle = chandle
        # channel = PS3000A_CHANNEL_C = 1
        channel = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_C"]
        # enabled = 1
        # coupling_type = PS3000A_10V = 1
        coupling_type = ps3.PS3000A_COUPLING["PS3000A_DC"]
        # range = PS3000A_10V = 8
        chCRange = ps3.PS3000A_RANGE["PS3000A_10V"]
        # analogue offset = 0 V
        analog_offset=0
        self.status["setChC"] = ps3.ps3000aSetChannel(self.chandle, channel, enabled, coupling_type, chCRange, analog_offset)
        assert_pico_ok(self.status["setChC"])

        # Set up channel D
        # handle = chandle
        # channel = PS3000A_CHANNEL_A = 1
        channel = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_D"]

        # enabled = 1
        # coupling_type = PS3000A_10V = 1
        coupling_type = ps3.PS3000A_COUPLING["PS3000A_DC"]
        # range = PS3000A_10V = 8
        chDRange = ps3.PS3000A_RANGE["PS3000A_10V"]
        # analogue offset = 0 V
        analog_offset=0
        self.status["setChD"] = ps3.ps3000aSetChannel(self.chandle, channel, enabled, coupling_type, chDRange, analog_offset)
        assert_pico_ok(self.status["setChD"])

        # find maximum ADC count value
        # handle = chandle
        # pointer to value = ctypes.byref(maxADC)
        maxADC = ctypes.c_int16()
        self.status["maximumValue"] = ps3.ps3000aMaximumValue(self.chandle, ctypes.byref(maxADC))
        assert_pico_ok(self.status["maximumValue"])

        # Set up single trigger
        # source = ps3000A_external = 0
        source = ps3.PS3000A_CHANNEL["PS3000A_EXTERNAL"]
        # threshold = 1024 ADC counts
        threshold = int(mV2adc(500,chARange, maxADC)) # def of mV2adc: https://github.com/picotech/picosdk-python-wrappers/blob/master/picosdk/functions.py#L42
        direction = ps3.PS3000A_THRESHOLD_DIRECTION["PS3000A_RISING"]
        delay = 0 # s
        autoTrigger_ms = 0 # 0 means device will wait indefinitely for a trigger - see page 105 of ps3000a programmer's guide
        self.status["trigger"] = ps3.ps3000aSetSimpleTrigger(self.chandle, 1, source, threshold, direction, delay, autoTrigger_ms) # (handle, enable, source, threshold, direction, delay, autoTrigger_ms)

        assert_pico_ok(self.status["trigger"])

        # Set number of pre and post trigger samples to be collected
        #self.preTriggerSamples = 5000
        #self.postTriggerSamples = 5000
        #self.maxSamples = self.preTriggerSamples + self.postTriggerSamples

        # Get self.timebase information
        # Warning: When using this example it may not be possible to access all Timebases as all channels are enabled by default when opening the scope.  
        # To access these Timebases, set any unused analogue channels to off.
        timeIntervalns = ctypes.c_float()
        returnedMaxSamples = ctypes.c_int32()
        self.status["GetTimebase"] = ps3.ps3000aGetTimebase2(self.chandle, self.timebase, self.maxSamples, ctypes.byref(timeIntervalns), 1, ctypes.byref(returnedMaxSamples), 0) # handle, timebase, noSamples, timeIntervalNanoseconds, oversample, maxSamples, segmentIndex - page 48 of ps3000a programmer's guide
        assert_pico_ok(self.status["GetTimebase"])

        # Run block capture
        # handle = chandle
        # number of pre-trigger samples = self.preTriggerSamples
        # number of post-trigger samples = PostTriggerSamples
        # self.timebase = 2 = 4 ns (see Programmer's guide for mre information on self.timebases)
        # time indisposed ms = None (not needed in the example)
        # segment index = 0
        # lpReady = None (using ps5000aIsReady rather than ps5000aBlockReady)
        # pParameter = None
        self.status["runBlock"] = ps3.ps3000aRunBlock(self.chandle, self.preTriggerSamples, self.postTriggerSamples, self.timebase, 1, None, 0, None, None) # page 75 of ps3000a programmer's guide
        assert_pico_ok(self.status["runBlock"])

        # Create buffers ready for assigning pointers for data collection
        bufferAMax = (ctypes.c_int16 * self.maxSamples)()
        bufferAMin = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example
        bufferBMax = (ctypes.c_int16 * self.maxSamples)()
        bufferBMin = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example
        bufferCMax = (ctypes.c_int16 * self.maxSamples)()
        bufferCMin = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example
        bufferDMax = (ctypes.c_int16 * self.maxSamples)()
        bufferDMin = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example

        # Set data buffer location for data collection from channel A
        # handle = chandle
        # source = ps3.ps3000_channel_A = 0
        # pointer to buffer max = ctypes.byref(bufferAMax)
        # pointer to buffer min = ctypes.byref(bufferAMin)
        # buffer length = self.maxSamples
        # segment index = 0
        # ratio mode = ps3000A_RATIO_MODE_NONE = 0
        source = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_A"]
        self.status["setDataBuffers"] = ps3.ps3000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferAMax), ctypes.byref(bufferAMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffers"])
        source = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_B"]
        self.status["setDataBuffers"] = ps3.ps3000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferBMax), ctypes.byref(bufferBMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffers"])
        source = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_C"]
        self.status["setDataBuffers"] = ps3.ps3000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferCMax), ctypes.byref(bufferCMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffers"])
        source = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_D"]
        self.status["setDataBuffers"] = ps3.ps3000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferDMax), ctypes.byref(bufferDMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffers"])

        # create overflow location
        overflow = (ctypes.c_int16 * 10)()
        # create converted type self.maxSamples
        self.cmaxSamples = ctypes.c_int32(self.maxSamples)

        # Check for data collection to finish using
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        while ready.value == check.value:
            self.status["isReady"] = ps3.ps3000aIsReady(self.chandle, ctypes.byref(ready))

        # Retried data from scope to buffers assigned above
        # handle = chandle
        # start index = 0
        # pointer to number of samples = ctypes.byref(self.cmaxSamples)
        # downsample ratiao = 0
        # downsample ratio mode = PS5000A_RATIO_MODE_NONE
        # pointer to overflow = ctypes.byref(overflow))

        self.status["GetValues"] = ps3.ps3000aGetValues(self.chandle, 0, ctypes.byref(self.cmaxSamples), 0, 0, 0, ctypes.byref(overflow))
        assert_pico_ok(self.status["GetValues"])

        # Finds the max ADC count
        # Handle = chandle
        # Value = ctype.byref(maxADC)
        maxADC = ctypes.c_int16()
        self.status["maximumValue"] = ps3.ps3000aMaximumValue(self.chandle, ctypes.byref(maxADC))
        assert_pico_ok(self.status["maximumValue"])

        # convert ADC counts data to mV
        adc2mVChAMax = adc2mV(bufferAMax, chARange, maxADC)
        adc2mVChBMax = adc2mV(bufferBMax, chBRange, maxADC)
        adc2mVChCMax = adc2mV(bufferCMax, chCRange, maxADC)
        adc2mVChDMax = adc2mV(bufferDMax, chDRange, maxADC)

        # Stop the scope
        # handle = chandle
        self.status["stop"] = ps3.ps3000aStop(self.chandle)
        assert_pico_ok(self.status["stop"])

        # Close unit Disconnect the scope
        # handle = chandle
        self.status["close"]=ps3.ps3000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])

        # display self.status returns
        #print(self.status)

            ## SAVING DATA ##

        # Create time data
        time = np.linspace(-self.preTriggerSamples*timeIntervalns.value, (self.postTriggerSamples - 1) * timeIntervalns.value, self.cmaxSamples.value)
        
        # average over 32-segment long intervals
        try:
            time = np.mean(np.reshape(time,(-1,32)),1)
            adc2mVChAMax = np.mean(np.reshape(adc2mVChAMax,(-1,32)),axis=1) # https://stackoverflow.com/questions/10847660/subsampling-averaging-over-a-numpy-array
            adc2mVChBMax = np.mean(np.reshape(adc2mVChBMax,(-1,32)),axis=1)
            adc2mVChCMax = np.mean(np.reshape(adc2mVChCMax,(-1,32)),axis=1)
            adc2mVChDMax = np.mean(np.reshape(adc2mVChDMax,(-1,32)),axis=1)

            #"""
            # save data as a packed file

            packed = {}
            packed["time_ns"] = time
            packed["ChA_mV"] = adc2mVChAMax
            packed["ChB_mV"] = adc2mVChBMax 
            packed["ChC_mV"] = adc2mVChCMax
            packed["ChD_mV"] = adc2mVChDMax

            np.savez(path,**packed)
            #"""
            
            print(f'Picoscope trace saved at {path}')

        except Exception as e:
            print(e)
        


Server = PicoscopeServer
if __name__ == "__main__":
    from labrad import util
    util.runServer(Server())
