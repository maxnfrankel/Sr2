from labjack import ljm
import time

# labjack device serial no
serialno = "440011420"

# https://labjack.com/support/software/api/ljm


""" 
LabJack T4 I/O datatypes
______________________________________
| SGND                             V |
| SPC                            GND |
| SGND        DAC0 : FLOAT32 / UINT32|
| VS          DAC1 : FLOAT32 / UINT32|
|                                    |
| FIO7 : UINT16                   VS |
| FIO6 : UINT16                  GND |
| GND                  AIN2 : FLOAT32|
| VS                   AIN3 : FLOAT32|
|                                    |
| FIO5 : UINT16                   VS |
| FIO4 : UINT16                  GND |
| GND                  AIN0 : FLOAT32|
| VS                   AIN1 : FLOAT32|
--------------------------------------
"""

# local constants for shortening commands
WRITE = ljm.constants.WRITE
READ = ljm.constants.READ
FLOAT32 = ljm.constants.UINT16
UINT32 = ljm.constants.UINT32

# open LabJack
handle = ljm.openS("T4", "ANY", serialno) # T4 device, any connection, and identifier serial number: "440011420"

info = ljm.getHandleInfo(handle)
print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
      "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
      (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

## RUN 1 (trying to see if the labjack can be read and written multiple times)

# Write to DAC0 and read result on AIN0
numFrames = 4 # number of frames we want to access
aNames = ['DAC0', 'DAC1','AIN0','AIN1'] # names of the frames
aWrites = [WRITE, WRITE, READ, READ] # access type
aNumValues = [1, 1, 1, 1] # number of values stored in frame
aValues = [1, 1, 0, 0] # value to write, in V (0 if read)
results = ljm.eNames(handle, numFrames, aNames, aWrites, aNumValues, aValues) # the results are read out as a list of values

print("\neAdresses results: ")
start = 0 # we define a start and end index so that we only select our desired value(s) from the list of returned values with results[start:end]
for i in range(numFrames):
    end = start + aNumValues[i]
    print("     Name - %s, write - %i, values: %s" % (aNames[i],aWrites[i], str(results[start:end])))
    start = end

## RUN 2

# Write to DAC0 and read result on AIN0
numFrames = 4 # number of frames we want to access
aNames = ['DAC0', 'DAC1','AIN0','AIN1'] # names of the frames
aWrites = [WRITE, WRITE, READ, READ] # access type
aNumValues = [1, 1, 1, 1] # number of values stored in frame
aValues = [0, 0, 0, 0] # value to write, in V (0 if read)
results = ljm.eNames(handle, numFrames, aNames, aWrites, aNumValues, aValues) # the results are read out as a list of values

results = ljm.eNames(handle, numFrames, aNames, aWrites, aNumValues, aValues) # the results are read out as a list of values
print("\neAdresses results: ")
start = 0 # we define a start and end index so that we only select our desired value(s) from the list of returned values with results[start:end]
for i in range(numFrames):
    end = start + aNumValues[i]
    print("     Name - %s, write - %i, values: %s" % (aNames[i],aWrites[i], str(results[start:end])))

# Close handle
ljm.close(handle)
