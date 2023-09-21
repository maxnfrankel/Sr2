import vxi11
import time

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

address = '192.168.1.101'
inst = vxi11.Instrument(address)

print(inst.ask('*IDN?'))

inst.write(':CALC:MARK1:CPE:STAT ON')

labels = ["tens4_frequency"]
while True:
    output = []
    freq = inst.ask(':CALC:MARK1:X?')
    output.append(freq)

    token = 'yelabtoken'
    org = 'yelab'
    bucket = 'data_logging'

    records=[
            {
            "measurement": "Sr2_tens4_monitor",
            "tags": {"Name": labels},
            "fields": {"Value": output}
            #"time": datetime.now()
            }
        ]
    print(records)

    with InfluxDBClient(url="http://yesnuffleupagus.colorado.edu:8086", token=token, org=org, debug=False) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            for i in range(len(output)):
                write_api.write(bucket, org, "Sr2_tens4_monitor,Channel=" + str(labels[i]) +  " Value=" + str(output[i]))
            client.close()

    time.sleep(10)

