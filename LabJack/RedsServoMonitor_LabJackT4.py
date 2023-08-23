# script to continuously send labjack data to InfluxDB
# script is intended to monitor the error signal of the red MOT lasers
# and give us an easy way to track the lock remotely

from labjack import ljm
import time

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

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

while True:
    labels = ['alpha_error', 'beta_error']
    output = []

    # open LabJack
    handle = ljm.openS("T4", "ANY", serialno) # T4 device, any connection, and identifier serial number: "440011420"

    numFrames = 2 # number of frames we want to access
    aNames = ['AIN0','AIN2'] # names of the frames
    aWrites = [READ, READ] # access typed
    aNumValues = [1, 1] # number of values read/written to each frame

    aValues = [0, 0] # value to write, in V (0 if read)
    results = ljm.eNames(handle, numFrames, aNames, aWrites, aNumValues, aValues) # the results are read out as a list of values
    
    alpha_error = results[0] # alpha_error measured from AIN0
    output.append(alpha_error)
    print(alpha_error)

    beta_error = results[1] # beta_error measured from AIN1
    output.append(beta_error)
    print(beta_error)

    records=[
            {
            "measurement": "Sr2_LabJack_reds",
            "tags": {"Name": labels},
            "fields": {"Value": output}
            #"time": datetime.now()
            }
        ]
    print(records)

    token = 'yelabtoken'
    org = 'yelab'
    bucket = 'data_logging'

    with InfluxDBClient(url="http://yesnuffleupagus.colorado.edu:8086", token=token, org=org, debug=False) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            for i in range(len(output)):
                write_api.write(bucket, org, "Sr2_LabJack_reds,Channel=" + str(labels[i]) +  " Value=" + str(output[i]))
            client.close()

    # Close handle
    ljm.close(handle)

    time.sleep(10)