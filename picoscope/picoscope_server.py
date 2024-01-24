from picoscope import ps5000a

serial_number = 'IV947/0114'
trigger_threshold = 1.
duration = 10.0
sampling_interval = .000001
n_capture = 1

ps = ps5000a.PS5000a(serial_number)
ps.resolution = ps.ADC_RESOLUTIONS["16"]

ps.setChannel('A', VRange = 1.0)
ps.setChannel('B', VRange = 1.0)

ps.setSamplingInterval(sampling_interval, duration)
ps.setSimpleTrigger('External', trigger_threshold)
ps.memorySegments(n_capture)
ps.setNoOfCaptures(n_capture)

ps.runBlock()
ps.waitReady()

data1 = ps.getDataV(0)
data2 = ps.getDataV(1)

#print(data1)
#print(data2)
for i in range(len(data1)):
    if data1[i] == 0.:
        data1[i] = .00001
    if data2[i] == 0.:
        data2[i] = .00001


import matplotlib.pyplot as plt
import numpy as np

import scipy
from scipy import signal


fig, ax = plt.subplots(2)

taus = np.linspace(0, duration, len(data1))
#print(taus[1] - taus[0])

#data1 = scipy.signal.decimate(data1, 100)
#data2 = scipy.signal.decimate(data2, 100)
#taus = taus[::100]

#ax[0].plot(taus,data1, 10)
#ax[0].plot(taus,data2)
#ax[0].set_ylabel('Volts')
#ax[0].set_xlabel('Time (s)')

ratio = np.array(data1)/np.array(data2)
phases = np.arctan(ratio)
#print(np.unwrap(phases, period = np.pi/2.))
unwrapped_phases = np.unwrap(phases, period = np.pi/2.)


taus_dec = taus[::20]
rads_dec = scipy.signal.decimate(scipy.signal.decimate(scipy.signal.detrend(unwrapped_phases), 10),2)

ax[0].plot(taus_dec[5:-5],rads_dec[5:-5])
ax[0].set_ylabel('Phase (rad.)')
ax[0].set_xlabel('Time (s)')

pxx, freqs = plt.mlab.psd(rads_dec, Fs = 1./(taus_dec[1] - taus_dec[0]), NFFT = int(len(taus_dec)/10))

freqs = freqs[1:len(freqs)//2]
pxx = pxx[1:len(pxx)//2]

import clock_noise
laser = clock_noise.siPlusComb()
laser_psd = laser.psd(freqs)

#print(freqs)
#print(pxx)

ax[1].loglog(freqs, pxx*freqs**2, label = 'Slave additive noise')
ax[1].loglog(freqs, laser_psd,'--', color = 'red', label = 'Si + comb' )
ax[1].set_xlabel('Frequency (Hz)')
ax[1].set_ylabel(r'$Hz^{2}$/Hz')
ax[1].grid()
fig.set_size_inches(9.6, 5.4)
fig.tight_layout()
fig.legend(loc = (.1, .35))
fig.savefig('Heterodyne_noise_new_diode_adjust_MJM.pdf', dpi = 250)

plt.show()

np.savetxt('additive_phase_noise_new_diode.txt', pxx)
np.savetxt('freqs.txt', freqs)
