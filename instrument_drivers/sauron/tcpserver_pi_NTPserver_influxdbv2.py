'''
This relies on the fact that there is a NTP server running on the Pi. The ESP32 then asks Pi at regular intervals its time and corrects its own time.
DATA THE pi RECIEVES IS 'datetimetuple , v1,v2,v3,v4,'

'''
import socket, os
from datetime import datetime, timezone
import logging
import csv
import itertools
import gc
from influxdb_client import InfluxDBClient, BucketRetentionRules
from influxdb_client.client.write_api import SYNCHRONOUS
import atexit

class sauron_server:

    def __init__(self,
                 PORT=65433,  # maps to the sensor. One port for each sensor
                 SENSOR_NAME = 'Voltage_Humidity_Temp_AirPressure',
                 measurement_name_list = ['v1_Volts','v2_percent','v3_celsius','v4_psi'],
                 IP="192.168.4.1",  # do not touch ideally, IP of the wifi network adaptor being used
                 LOG_LEVEL=logging.INFO,
                 INFLUX_WRITE = True,
                 DATA_WRITE = False,
                 NUM_OF_ADC = 1, #Change if you have multiple ADCs connected to a single ESP32, and recieveing a stream of more data points
                 INFLUX_ORG_NAME = 'hatlab',
                 INFLUX_TOKEN = '729p9yTT5HtNBui-B8kiM2QFlKVCz4-LLaD1no_FxBx7eaw3fTFWhQ2yFrs5GuwyMXRni4UgkFvWodEdVL2rfw=='
                 ):

        # basic object variables setup
        self.PORT = PORT  # maps to the sensor
        self.SENSOR_NAME = SENSOR_NAME
        self.measurement_name_list = measurement_name_list
        self.LOG_DESTINATION = f'log_{self.SENSOR_NAME}.txt'
        self.IP = IP
        self.org_name = INFLUX_ORG_NAME
        self.influx_token = INFLUX_TOKEN
        self.spinner = itertools.cycle(u'◐◓◑◒')

        # Data recieving parameters
        self.BUNCH = int(4*NUM_OF_ADC) + 1                 # used for reshaping data later, +1 for datetime tuple in recieved data
        self.sockettimeout = 50      # seconds


        # Data write parameters setup
        self.DATA_WRITE = DATA_WRITE
        self.DATA_DESTINATION_FOLDER = f"./{self.SENSOR_NAME}/"
        if DATA_WRITE : os.makedirs(self.DATA_DESTINATION_FOLDER, exist_ok=True)
        if INFLUX_WRITE :
            self.INFLUX = True
            self.infdb = InfluxDBClient(url='http://localhost:8086', token=self.influx_token, org=self.org_name)
            self.infdb_write_api = self.infdb.write_api(write_options=SYNCHRONOUS)

            # TODO : check if bucket/database exists. If not create one wiht a 16 week retention policy
            self.infdb_bucket_api = self.infdb.buckets_api()
            if self.infdb_bucket_api.find_bucket_by_name(f'{self.SENSOR_NAME}') == None:
                retention_rules = BucketRetentionRules(type="expire", every_seconds=4*30*24*60*60)
                self.infdb_bucket_api.create_bucket(bucket_name=f'{self.SENSOR_NAME}', retention_rules=retention_rules, org=self.org_name)


        # setup logging
        logging.basicConfig(filename=self.LOG_DESTINATION,
                            format="%(levelname)s %(asctime)s %(message)s", level=LOG_LEVEL,
                            datefmt='%m/%d/%Y %H:%M:%S')
        logging.debug("New program session started.")
        self.first = True

        # Initiate connection
        self.s = None
        self.con, self.addr = self.initiate_connection()

        self.iter = 0



        return

    def record_loop(self):
        '''
        Sets up a data recieving and writing loopac
        '''
        time0 = datetime.now()
        logging.info("Starting recording loooooop.")

        while True:
            gc.collect()
            temp = self.receive_chunk()
            print("\r>>", next(self.spinner), end='')
            if self.first : continue # implemented to properly handle reconnections
            timestamped_data, timestamped_data_influx = self.process_chunk(temp)

            if self.DATA_WRITE : self.write_data_to_file(timestamped_data)
            if self.INFLUX : self.data_to_influxdbv2(timestamped_data_influx,self.measurement_name_list)

            if abs(datetime.now().hour - time0.hour) == 1  :
                logging.info(f"Beep Boop. Still collecting data.")
                time0 = datetime.now()
        return

    def initiate_connection(self):
        '''
        sets up sockets and starts listening for a connection from ESP32.
        '''

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((self.IP,self.PORT))
        self.s.listen()
        logging.info("Listening for new connections...")
        self.con, self.addr = self.s.accept()
        self.con.settimeout(self.sockettimeout)
        logging.info(f"Connected to {self.addr}")

        atexit.register(self.exit)
        return self.con, self.addr

    def exit(self):
        self.s.close()
        logging.warning("Program exiting, socket closed.")
        return

    def reconnect(self):
        logging.debug("Accepting new connections")
        # self.s.close()
        self.con, self.addr = self.s.accept()
        self.con.settimeout(self.sockettimeout)
        logging.info(f"Connected to {self.addr}")
        return

    def receive_chunk(self, chunk_size=int(10*69)):
        #chunk size is the amount of data points python would read at once
        try:
            data_chunk = self.con.recv(chunk_size).decode('utf-8')[:-1]   #[:-1] for removing the , at the last

        except socket.timeout:
            logging.warning("Connection with the ESP32 lost.")
            self.reconnect()
            data_chunk = self.con.recv(chunk_size).decode('utf-8')[:-1]
            return None # TODO Figure out what happens here what to return and if a socket flush is needed

        if self.first:
            logging.debug(f"Received first datapoint.")
            self.first = False

        return data_chunk

    def convert_data_points_to_units(self,points):
        '''
        TO BE CHANGED accordign to need. Basic implementation is to convert to voltage assuming 16bit ADC range from -6.144 to 6.144V as in ADS_1115
        '''
        try:
            points_ = [int(i)*6144/(2**15-1) for i in points]
        except:
            logging.warning(f"Invalid datapoint recieved -> {points}")
            points_ = [0]*len(points)

        return points_

    def process_chunk(self, data_chunk: str, delimiter=','):
        '''
        Time stamp the recieved data and prepare for writing onto disk and influxdb
        '''
        # discretize data from the TCP stream and process measurement data
        data = data_chunk.split(delimiter)
        data = [data[i:i + self.BUNCH] for i in range(0, len(data), self.BUNCH)]
        for (i,points) in enumerate(data):
            data[i] = [points[0]] + self.convert_data_points_to_units(points[1:])

        # process time information
        timestamped_data = [0]*len(data)
        timestamped_data_influx = [0]*len(data)
        for (i, point) in enumerate(data):
            dt_list = [int(i) for i in point[0][1:-1].split(".")]
            dt_tuple = datetime(dt_list[0],dt_list[1],dt_list[2],dt_list[4],dt_list[5],dt_list[6],dt_list[7],tzinfo=timezone.utc)
            timestamped_data[i] = [dt_tuple.strftime("%m/%d/%Y %H:%M:%S.%f")] + point[1:]
            timestamped_data_influx[i] = [int(dt_tuple.timestamp()*1e3)] + point[1:]  # preserve milliseconds

        # Timestamped data looks like : [['10/18/2023 00:11:38.823553', 200.34, 300.423, 3453, 23452], ['10/18/2023 00:11:48.823553', 124, 1234, 1235, 5681], ['10/18/2023 00:11:58.823553', 23463, 134, 1354, 1234]]
        return timestamped_data, timestamped_data_influx

    def write_data_to_file(self,timestamped_data):
        '''
        Writes data to a file with the date. Creates a new file if needed.
        '''
        filepath = self.DATA_DESTINATION_FOLDER+datetime.now().strftime('%Y-%m-%d')+'_'+self.SENSOR_NAME+'.csv'
        with open(filepath,'a+',newline='') as f:
            writer = csv.writer(f)
            writer.writerows(timestamped_data)
        logging.debug("wrote to data file")
        return


    def data_to_influxdbv2(self,timestamped_data, measurement_name_list = []):
        '''
        writes data to influxdb v2 database specified in init.
        '''
        # TODO : Implement writing to influxdb
        linelist = []
        for i in range(len(timestamped_data)):
            line = f'{self.SENSOR_NAME} '
            for j in range(1,len(timestamped_data[i])):
                if measurement_name_list[j-1] : line += f'{measurement_name_list[j-1]}={timestamped_data[i][j]},'
                else : line += f'V{j-1}={timestamped_data[i][j]},'
            line = line[:-1]
            line += " "
            line += str(timestamped_data[i][0])
            linelist.append(line)
        self.infdb_write_api.write(bucket =f'{self.SENSOR_NAME}', record = linelist, write_precision='ms')
        logging.debug("wrote to influxdb")


        return

if __name__ == '__main__':
    sensor1_sauron = sauron_server(
                 PORT=65433,  # maps to the sensor. One port for each sensor
                 SENSOR_NAME = 'LabAirPressure',
                 IP="192.168.4.1",  # do not touch ideally, IP of the wifi network adaptor being used
                 LOG_LEVEL=logging.INFO,  # do not touch ideally
    )
    sensor1_sauron.record_loop()
