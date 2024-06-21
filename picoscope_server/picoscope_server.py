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
# and https://github.com/picotech/picosdk-python-wrappers/blob/master/ps3000aExamples/ps3000aBlockExample.py
# combined with Will Milner's picoscope_labrad_server.py code

class PicoscopeServer(ThreadedServer):
    name = '%LABRADNODE%_picoscope'
    update = Signal(698461, 'signal: update', 's') #?

    def initServer(self):
        # Create chandle and self.status ready for use
        self.chandle = ctypes.c_int16()
        self.status = {}

    @setting(1)
    def set_recordduration_5000a(self,c,duration,presamples,postsamples):
        # TODO: - add option to change device resolution. 4ch requires 14bit, 2ch can do 16
        #       - add option to select number of channels without having to go in and edit the get_data method
        # Inputs:
        #   c: context varaible passed when the conductor accesses this labrad server. See https://github.com/PickyPointer/SrE/wiki/Labrad_Tools-overview for more details
        #   duration: record duration in s
        #   presamples: number of samples before external trigger
        #   postsamples: number of samples after external trigger

        # timebase calculation from duration and # of samples
        # See page 28 of picotech.com/download/manuals/picoscope-5000-series-a-api-programmers-guide.pdf
        # 4 channels, 14-bit: (n-2)/125000000 s/sample
        # 2 channels, 15-bit: (n-2)/125000000 s/sample
        # 1 channels, 16-bit: (n-3)/62500000 s/sample
        # where n is an integer used to specify the picoscope timebase
                
        self.resolution = ps5.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_14BIT"]
        self.preTriggerSamples = presamples # Set number of pre and post trigger samples to be collected
        self.postTriggerSamples = postsamples
        self.maxSamples = self.preTriggerSamples + self.postTriggerSamples
        self.timebase = round(duration/self.maxSamples*125000000 + 2)
    
        print(f'\ndur={duration}s timebase={self.timebase} pre_trig_samples={presamples} post_trig_samples={postsamples}')
    
    @setting(2)
    def set_recordduration_3000a(self,c,duration,presamples,postsamples):
        # Inputs:
            #   c: context varaible passed when the conductor accesses this labrad server. See https://github.com/PickyPointer/SrE/wiki/Labrad_Tools-overview for more details
            #   duration: record duration in s
            #   presamples: number of samples before external trigger
            #   postsamples: number of samples after external trigger

        # timebase calculation from duration and # of samples
        # See page 15 of picotech.com/download/manuals/picoscope-3000-series-a-api-programmers-guide.pdf
        # 3000D series
        # 4 channels, 8-bit: (n-2)/125000000 s/sample
        # where n is an integer used to specify the picoscope timebase
        # ps3000a doesn't have the option to set device resolution

        # picoscope can only sample at 8bits of resolution
        # we want to sample x32 more and then average back down to try to make up for the 7 less bits of resolution


        self.preTriggerSamples = presamples*32 # Set number of pre and post trigger samples to be collected
        self.postTriggerSamples = postsamples*32
        self.maxSamples = self.preTriggerSamples + self.postTriggerSamples
        self.timebase = round(duration/self.maxSamples*125000000 + 2)

        print(f'\ndur={duration}s timebase={self.timebase} pre_trig_samples={presamples} post_trig_samples={postsamples} x32 sampling but avged back down again')
    
    @setting(3)
    def get_data_5000a(self,c,path,serial_no):
        # based off of https://github.com/picotech/picosdk-python-wrappers/blob/master/ps5000aExamples/ps5000aBlockExample.py

            ## PICOSDK CODE ##

        self.serial_no = ctypes.create_string_buffer(bytes(serial_no,encoding='utf-8'))

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
        channel = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        enabled = 1
        coupling_type = ps5.PS5000A_COUPLING["PS5000A_DC"]
        chARange = ps5.PS5000A_RANGE["PS5000A_10V"] # range is +- around 0V
        analog_offset=0 # voltage to add to the input channel before digitization 
        self.status["setChA"] = ps5.ps5000aSetChannel(self.chandle, channel, enabled, coupling_type, chARange, analog_offset)
        assert_pico_ok(self.status["setChA"])

        # Set up channel B
        channel = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
        enabled = 1
        chBRange = ps5.PS5000A_RANGE["PS5000A_10V"]
        analog_offset=0 # voltage to add to the input channel before digitization 
        self.status["setChB"] = ps5.ps5000aSetChannel(self.chandle, channel, enabled, coupling_type, chBRange, analog_offset)
        assert_pico_ok(self.status["setChB"])

        # Set up channel C
        channel = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_C"]
        enabled = 1
        chCRange = ps5.PS5000A_RANGE["PS5000A_10V"]
        analog_offset=0 # voltage to add to the input channel before digitization 
        self.status["setChC"] = ps5.ps5000aSetChannel(self.chandle, channel, enabled, coupling_type, chCRange, analog_offset)
        assert_pico_ok(self.status["setChC"])

        # Set up channel D
        channel = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_D"]
        enabled = 1
        chDRange = ps5.PS5000A_RANGE["PS5000A_10V"]
        analog_offset=0 # voltage to add to the input channel before digitization 
        self.status["setChD"] = ps5.ps5000aSetChannel(self.chandle, channel, enabled, coupling_type, chDRange, analog_offset)
        assert_pico_ok(self.status["setChD"])

        # find maximum ADC count value
        # pointer to value = ctypes.byref(maxADC)
        maxADC = ctypes.c_int16()
        self.status["maximumValue"] = ps5.ps5000aMaximumValue(self.chandle, ctypes.byref(maxADC))
        assert_pico_ok(self.status["maximumValue"])

        # Set up single trigger
        enabled = 1
        source = ps5.PS5000A_CHANNEL["PS5000A_EXTERNAL"]
        threshold = int(mV2adc(500,chARange, maxADC)) # 500mV threshold for trigger. For def of mV2adc: https://github.com/picotech/picosdk-python-wrappers/blob/master/picosdk/functions.py#L42
        direction = ps5.PS5000A_THRESHOLD_DIRECTION["PS5000A_RISING"]
        delay = 0 # s
        autoTrigger_ms = 0 # setting to 0 makes scope wate indefinitely for a trigger - see page 115 of ps5000a programmer's guide
        self.status["trigger"] = ps5.ps5000aSetSimpleTrigger(self.chandle, enabled, source, threshold, enabled, delay, autoTrigger_ms) # (handle, enable, source, threshold, direction, delay, autoTrigger_ms)

        assert_pico_ok(self.status["trigger"])

        # Get self.timebase information
        # Warning: When using this example it may not be possible to access all Timebases as all channels are enabled by default when opening the scope.  
        # To access these Timebases, set any unused analogue channels to off.
        # pointer to timeIntervalNanoseconds = ctypes.byref(timeIntervalns)
        # pointer to self.maxSamples = ctypes.byref(returnedMaxSamples)
        segment_index = 0
        timeIntervalns = ctypes.c_float()
        returnedMaxSamples = ctypes.c_int32()
        self.status["getTimebase2"] = ps5.ps5000aGetTimebase2(self.chandle, self.timebase, self.maxSamples, ctypes.byref(timeIntervalns), ctypes.byref(returnedMaxSamples), segment_index)
        assert_pico_ok(self.status["getTimebase2"])

        # Run block capture
        timeIndisposedMs = None # not needed in the example
        segmentIndex = 0
        lpReady = None # using ps5000aIsReady rather than ps5000aBlockReady
        pParameter = None
        self.status["runBlock"] = ps5.ps5000aRunBlock(self.chandle, self.preTriggerSamples, self.postTriggerSamples, self.timebase, timeIndisposedMs, segmentIndex, lpReady, pParameter)
        assert_pico_ok(self.status["runBlock"])

        # Check for data collection to finish using ps5000aIsReady
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        while ready.value == check.value:
            self.status["isReady"] = ps5.ps5000aIsReady(self.chandle, ctypes.byref(ready))

        # Create buffers ready for assigning pointers for data collection
        bufferAMax = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example
        bufferAMin = (ctypes.c_int16 * self.maxSamples)()
        bufferBMax = (ctypes.c_int16 * self.maxSamples)()
        bufferBMin = (ctypes.c_int16 * self.maxSamples)()
        bufferCMax = (ctypes.c_int16 * self.maxSamples)()
        bufferCMin = (ctypes.c_int16 * self.maxSamples)() 
        bufferDMax = (ctypes.c_int16 * self.maxSamples)()
        bufferDMin = (ctypes.c_int16 * self.maxSamples)() 

        # Set data buffer location for data collection from channel A
        source = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        # pointer to buffer max = ctypes.byref(bufferAMax)
        # pointer to buffer min = ctypes.byref(bufferAMin)
        # buffer length = self.maxSamples
        # segment index = 0
        # ratio mode = PS5000A_RATIO_MODE_NONE = 0
        self.status["setDataBuffersA"] = ps5.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferAMax), ctypes.byref(bufferAMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersA"])

        # Set data buffer location for data collection from channel B
        source = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
        self.status["setDataBuffersB"] = ps5.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferBMax), ctypes.byref(bufferBMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersB"])

        source = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_C"]
        self.status["setDataBuffersC"] = ps5.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferCMax), ctypes.byref(bufferCMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersC"])

        source = ps5.PS5000A_CHANNEL["PS5000A_CHANNEL_D"]
        self.status["setDataBuffersD"] = ps5.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferDMax), ctypes.byref(bufferDMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersD"])

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
        adc2mVChCMax =  adc2mV(bufferCMax, chCRange, maxADC)
        adc2mVChDMax =  adc2mV(bufferDMax, chDRange, maxADC)

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

        """
        # 2-channel option
        # save data as a packed file
        packed = {}
        packed["time_ns"] = time
        packed["ChA_mV"] = adc2mVChAMax #- analog_offset*1e3 # Add the analog offset (which I believe is in V) to the mV trace
        packed["ChB_mV"] = adc2mVChBMax #- analog_offset*1e3
        np.savez(path,**packed)
        """

        #"""
        # 4-channel option
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

    @setting(4)
    def get_data_3000a(self,c,path,serial_no): 
        # initially from https://github.com/picotech/picosdk-python-wrappers/blob/master/ps5000aExamples/ps5000aBlockExample.py
        # modified to match https://github.com/picotech/picosdk-python-wrappers/blob/master/ps3000aExamples/ps3000aBlockExample.py

            ## PICOSDK CODE ##
            
        self.serial_no = ctypes.create_string_buffer(bytes(serial_no,encoding='utf-8'))

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
    
        # Set up channel A
        channel = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_A"]
        enabled = 1
        coupling_type = ps3.PS3000A_COUPLING["PS3000A_DC"]
        chARange = ps3.PS3000A_RANGE["PS3000A_10V"]
        analog_offset=0
        self.status["setChA"] = ps3.ps3000aSetChannel(self.chandle, channel, enabled, coupling_type, chARange, analog_offset)
        assert_pico_ok(self.status["setChA"])

        # Set up channel B
        channel = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_B"]
        coupling_type = ps3.PS3000A_COUPLING["PS3000A_DC"]
        chBRange = ps3.PS3000A_RANGE["PS3000A_10V"]
        analog_offset=0
        self.status["setChB"] = ps3.ps3000aSetChannel(self.chandle, channel, enabled, coupling_type, chBRange, analog_offset)
        assert_pico_ok(self.status["setChB"])

        # Set up channel C
        channel = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_C"]
        coupling_type = ps3.PS3000A_COUPLING["PS3000A_DC"]
        chCRange = ps3.PS3000A_RANGE["PS3000A_10V"]
        analog_offset=0
        self.status["setChC"] = ps3.ps3000aSetChannel(self.chandle, channel, enabled, coupling_type, chCRange, analog_offset)
        assert_pico_ok(self.status["setChC"])

        # Set up channel D
        channel = ps3.PS3000A_CHANNEL["PS3000A_CHANNEL_D"]
        coupling_type = ps3.PS3000A_COUPLING["PS3000A_DC"]
        chDRange = ps3.PS3000A_RANGE["PS3000A_10V"]
        analog_offset=0
        self.status["setChD"] = ps3.ps3000aSetChannel(self.chandle, channel, enabled, coupling_type, chDRange, analog_offset)
        assert_pico_ok(self.status["setChD"])

        # find maximum ADC count value
        # pointer to value = ctypes.byref(maxADC)
        maxADC = ctypes.c_int16()
        self.status["maximumValue"] = ps3.ps3000aMaximumValue(self.chandle, ctypes.byref(maxADC))
        assert_pico_ok(self.status["maximumValue"])

        # Set up single trigger
        source = ps3.PS3000A_CHANNEL["PS3000A_EXTERNAL"]
        threshold = int(mV2adc(500,chARange, maxADC)) # def of mV2adc: https://github.com/picotech/picosdk-python-wrappers/blob/master/picosdk/functions.py#L42
        direction = ps3.PS3000A_THRESHOLD_DIRECTION["PS3000A_RISING"]
        delay = 0 # s
        autoTrigger_ms = 0 # 0 means device will wait indefinitely for a trigger - see page 105 of ps3000a programmer's guide
        self.status["trigger"] = ps3.ps3000aSetSimpleTrigger(self.chandle, 1, source, threshold, direction, delay, autoTrigger_ms) # (handle, enable, source, threshold, direction, delay, autoTrigger_ms)

        assert_pico_ok(self.status["trigger"])

        # Get self.timebase information
        # Warning: When using this example it may not be possible to access all Timebases as all channels are enabled by default when opening the scope.  
        # To access these Timebases, set any unused analogue channels to off.
        timeIntervalns = ctypes.c_float()
        returnedMaxSamples = ctypes.c_int32()
        self.status["GetTimebase"] = ps3.ps3000aGetTimebase2(self.chandle, self.timebase, self.maxSamples, ctypes.byref(timeIntervalns), 1, ctypes.byref(returnedMaxSamples), 0) # handle, timebase, noSamples, timeIntervalNanoseconds, oversample, maxSamples, segmentIndex - page 48 of ps3000a programmer's guide
        assert_pico_ok(self.status["GetTimebase"])

        # Run block capture
        # time indisposed ms = None (not needed in the example)
        # segment index = 0
        # lpReady = None (using ps5000aIsReady rather than ps5000aBlockReady)
        # pParameter = None
        self.status["runBlock"] = ps3.ps3000aRunBlock(self.chandle, self.preTriggerSamples, self.postTriggerSamples, self.timebase, 1, None, 0, None, None) # page 75 of ps3000a programmer's guide
        assert_pico_ok(self.status["runBlock"])

        # Create buffers ready for assigning pointers for data collection
        bufferAMax = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example
        bufferAMin = (ctypes.c_int16 * self.maxSamples)() 
        bufferBMax = (ctypes.c_int16 * self.maxSamples)()
        bufferBMin = (ctypes.c_int16 * self.maxSamples)() 
        bufferCMax = (ctypes.c_int16 * self.maxSamples)()
        bufferCMin = (ctypes.c_int16 * self.maxSamples)() 
        bufferDMax = (ctypes.c_int16 * self.maxSamples)()
        bufferDMin = (ctypes.c_int16 * self.maxSamples)() 

        # Set data buffer location for data collection from channel A
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
        # start index = 0
        # pointer to number of samples = ctypes.byref(self.cmaxSamples)
        # downsample ratiao = 0
        # downsample ratio mode = PS5000A_RATIO_MODE_NONE
        # pointer to overflow = ctypes.byref(overflow))

        self.status["GetValues"] = ps3.ps3000aGetValues(self.chandle, 0, ctypes.byref(self.cmaxSamples), 0, 0, 0, ctypes.byref(overflow))
        assert_pico_ok(self.status["GetValues"])

        # Finds the max ADC count
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
        self.status["stop"] = ps3.ps3000aStop(self.chandle)
        assert_pico_ok(self.status["stop"])

        # Close unit Disconnect the scope
        self.status["close"]=ps3.ps3000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])

            ## SAVING DATA ##

        # Create time data
        time = np.linspace(-self.preTriggerSamples*timeIntervalns.value, (self.postTriggerSamples - 1) * timeIntervalns.value, self.cmaxSamples.value)
        
        # average over 32-segment long intervals
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


Server = PicoscopeServer
if __name__ == "__main__":
    from labrad import util
    util.runServer(Server())
