"""
### BEGIN NODE INFO
[info]
name = kuro
version = 2.0
description = 
instancename = %LABRADNODE%_kuro

[startup]
cmdline = %PYTHON% %FILE%
timeout = 60

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

import os
# Import the .NET class library
import h5py
import sys
import numpy as np
import os, glob, string
import time
import scipy
from labrad.server import setting, LabradServer, Signal, ThreadedServer
from twisted.internet import reactor, defer


import matplotlib.pyplot as plt
import numpy as np

import scipy
from scipy import signal

import datetime

from picoscope import ps5000a

class PicoscopeServer(ThreadedServer):
    name = '%LABRADNODE%_picoscope'
    update = Signal(698461, 'signal: update', 's')

    def initServer(self):
    	
        self.serial_number = 'IV947/0114'
        self.trigger_threshold = 1.
        self.duration = 1.0
        self.sampling_interval = .000001
        self.n_capture = 1	

        self.ps = ps5000a.PS5000a(self.serial_number)
        self.ps.resolution = self.ps.ADC_RESOLUTIONS["16"]

        self.ps.setChannel('A', VRange = 1.0)
        self.ps.setChannel('B', VRange = 1.0)

        self.ps.setSamplingInterval(self.sampling_interval,self.duration)
        self.ps.setSimpleTrigger('External', self.trigger_threshold)
        self.ps.memorySegments(self.n_capture)
        self.ps.setNoOfCaptures(self.n_capture)

#    @setting(10)
#    def run_block(self, c):
#    	self.ps.runBlock()
#    	self.ps.waitReady()
	
    @setting(11)    
    def get_data(self, c, path):
        self.ps.runBlock()
        self.ps.waitReady()
        ct = datetime.datetime.now()
        ts = ct.timestamp()
        data1 = self.ps.getDataV(0)
        data2 = self.ps.getDataV(1)
#        for i in range(len(data1)):
#            if data1[i] == 0.:
#                data1[i] = 1./2**16
#            if data2[i] == 0.:
#                data2[i] = 1./2**16
        taus = np.linspace(0,self. duration, len(data1))
        taus = taus + ts

        dataframe = np.vstack((taus, data1, data2))
        dataframe = np.transpose(dataframe)

        #np.savetxt('/home/srgang/srqdata/' + path + 'data.txt', dataframe)

        #h5f = h5py.File(path, "w")
        print(path)
        #h5f.create_dataset('picoscope_data', data = dataframe)
        #h5f.close()


Server = PicoscopeServer
if __name__ == "__main__":
    from labrad import util
    util.runServer(Server())
