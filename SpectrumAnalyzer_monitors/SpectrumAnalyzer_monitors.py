import vxi11
import time

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# connect to device over the network
addresses = ['192.168.1.101','192.168.1.8','192.168.1.8']
measurements = ["Sr2_tens4_monitor", "Sr2_clock_monitor", "Sr2_imaging_monitor"]
labels = ["tens4_frequency", "clock_frequency", "imaging_frequency"]

insts = []

for address in addresses:
    insts.append(vxi11.Instrument(address))

for i,inst in enumerate(insts):
    print(inst.ask('*IDN?'))# returns device info

    # commands are written to and from the instrument using 
    inst.write(':CALC:MARK1:CPE:STAT ON')

while True:

    output = [] # prepare list that will contain set of output measurements

    for i, inst in enumerate(insts):
        # query the measurements and append to output
        freq = inst.ask(':CALC:MARK1:X?')
        output.append(freq)

    token = 'yelabtoken'
    org = 'yelab'
    bucket = 'data_logging'

    records=[
            {
            "measurement": measurements,
            "tags": {"Name": labels},
            "fields": {"Value": output}
            }
        ]
    print(records)

    with InfluxDBClient(url="http://yesnuffleupagus.colorado.edu:8086", token=token, org=org, debug=False) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            for i in range(len(output)):
                write_api.write(bucket, org, str(measurements[i])+",Channel=" + str(labels[i]) +  " Value=" + str(output[i]))
            client.close()

    time.sleep(10)

