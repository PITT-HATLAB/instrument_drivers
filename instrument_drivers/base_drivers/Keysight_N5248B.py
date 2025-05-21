

from qcodes.instrument_drivers.Keysight.N5245A import N5245A
import logging
from plottr.data import datadict_storage as dds, datadict as dd
import numpy as np
from qcodes import (ArrayParameter, Instrument, VisaInstrument,
                    ManualParameter, MultiParameter,
                    validators as vals)
from typing import Any, Sequence, Union
from qcodes.instrument import find_or_create_instrument
try:
    import easygui
    EASYGUI = True
except ImportError:
    EASYGUI = False

import time
import re



def parse_meas_name(name):
    """
    Return (channel, trace_number) from a string such as 'CH5_GCSwp_12'.

    Only works if the pattern is exactly:  CH<digits>_<anything>_<digits>

    # example
        ch, tr = parse_meas_name("CH5_GCSwp_12")
        print(ch, tr)          # → 5  12

    """
    m = re.fullmatch(r"CH(\d+)_.+?_(\d+)", name, flags=re.IGNORECASE)
    if not m:
        raise ValueError("Name does not match CHx_…_tr# pattern")
    return int(m.group(1)), int(m.group(2))


def bits_to_bin(bits, width=14):
    """
    bits  – iterable of bit numbers (LSB = 0, next = 1, …)
    width – how many total bits to show (default 14)
    returns a left‑to‑right binary string, MSB first
    """
    value = sum(1 << b for b in bits)   # pack the bits
    return f"{value:0{width}b}"


def items_to_ch_in_bin(items):
    temp = []
    for i in range(0, len(items), 2):
        ch, tr = parse_meas_name(items[i])
        temp.append(tr)
    #value  = int(f"{bits_to_bin(temp)}",2)

    return temp

def get_bit_values_from_bit(binary_str, indices):
    """
    Get bit values starting from the 2nd bit (LSB + 1), ignoring the first bit.

    Parameters
    ----------
    binary_str : str
        e.g. '0b11111111111110'
    indices : list[int]
        1-based indices starting from the second bit from the right.
        For example: index=1 means second bit from right (real bit index 1),
                     index=2 means third bit from right (real bit index 2), etc.

    Returns
    -------
    list[int]
        List of 0 or 1 values at the specified indices.
    """
    bits = binary_str[2:]                # Remove '0b'
    bits = bits.zfill(max(indices) + 1)  # Pad to ensure index access


    return all(int(bits[-(i + 1)]) for i in indices)


def all_selected_bits_are_one(status_word: str, positions, width=14):
    """
    Return True only if *every* requested bit (plus 1) equals 1.

    Parameters
    ----------
    status_word : str          # e.g. '+14334' from STAT:OPER:AVER1:COND?
    positions   : iterable[int]# e.g. [1, 12, 13]            (0‑skip list)
    width       : int          # default 14 for Averaging registers
    """
    bin_val = bin(int(status_word))       # p = 1,12,13 ➜ test bits 2,13,14
    get_bit_values_from_bit(bin_val)
def wait_until_selected_bits_are_one(get_binary_str_fn, indices, timeout=10, poll_interval=0.1):
    """
    Waits until all selected bits (starting from 2nd bit) in a binary string are 1.

    Parameters
    ----------
    get_binary_str_fn : callable
        A function (e.g. lambda) that returns the latest binary string like '0b11111111111110'
    indices : list[int]
        1-based bit indices starting from the second bit (i.e., bit‑1 of the register)
    timeout : float
        Max time to wait (in seconds)
    poll_interval : float
        Time between checks (in seconds)

    Returns
    -------
    bool
        True if condition met before timeout, False otherwise.
    """
    start = time.time()
    print("waiting for averaging")
    while True:
        binary_str = get_binary_str_fn()
        bits = binary_str[2:].zfill(max(indices) + 1)
        if all(int(bits[-(i + 1)]) for i in indices):
            return True
        if time.time() - start > timeout:
            return False
        time.sleep(poll_interval)


class Hat_N5245A(N5245A):
    def __init__(self, name, address=None, **kwargs):

        '''
        Initializes the Keysight_P9374A, and communicates with the wrapper.

        Input:
          name (string)    : name of the instrument
          address (string) : GPIB address
          reset (bool)     : resets to default values, default=False
        '''
        if address == None:
            raise Exception('TCP IP address needed')
        logging.info(__name__ + ' : Initializing instrument Keysight PNA')

        super().__init__(name, address, **kwargs)   # terminator flows through only once

        if 'power' in self.parameters:
            del self.parameters['power']

        self.add_parameter('power',
            get_cmd=":SOUR1:POW?",
            set_cmd=":SOUR1:POW {}",
            unit='dBm',
            get_parser=float,
            vals=vals.Numbers(-85, 10)
        )
        self.add_parameter('fstart',
                           get_cmd=':SENS1:FREQ:STAR?',
                           set_cmd=':SENS1:FREQ:STAR {}',
                           vals=vals.Numbers(),
                           get_parser=float,
                           unit='Hz'
                           )
        self.add_parameter('fstop',
                           get_cmd=':SENS1:FREQ:STOP?',
                           set_cmd=':SENS1:FREQ:STOP {}',
                           vals=vals.Numbers(),
                           get_parser=float,
                           unit='Hz'
                           )
        self.add_parameter('fcenter',
                           get_cmd=':SENS1:FREQ:CENT?',
                           set_cmd=':SENS1:FREQ:CENT {}',
                           vals=vals.Numbers(),
                           get_parser=float,
                           unit='Hz'
                           )
        # self.add_parameter('fspan',
        #                    get_cmd=':SENS1:FREQ:SPAN?',
        #                    set_cmd=':SENS1:FREQ:SPAN {}',
        #                    vals=vals.Numbers(),
        #                    get_parser=float,
        #                    unit='Hz'
        #                    )
        self.add_parameter(
            'fspan',
            get_cmd=lambda: self.ask(f':SENS{self.channel}:FREQ:SPAN?'),
            set_cmd=lambda val: self.write(f':SENS{self.channel}:FREQ:SPAN {val}'),
            vals=vals.Numbers(),
            get_parser=float,
            unit='Hz'
        )
        self.add_parameter('averaging',
                           get_cmd=':SENS1:AVER?',
                           set_cmd=':SENS1:AVER {}',
                           get_parser=int,
                           vals=vals.Ints(0, 1)
                           )
        self.add_parameter('average_trigger',
                           get_cmd=':TRIG1:AVER?',
                           set_cmd=':TRIG1:AVER {}',
                           get_parser=int,
                           vals=vals.Ints(0, 1)
                           )
        self.add_parameter('avgnum',
                           get_cmd=':SENS1:AVER:COUN?',
                           set_cmd=':SENS1:AVER:COUN {}',
                           vals=vals.Ints(1),
                           get_parser=int
                           )
        self.add_parameter('rfout',
                           get_cmd=':OUTP?',
                           set_cmd=':OUTP {}',
                           vals=vals.Ints(0, 1),
                           get_parser=int
                           )
        self.add_parameter('trform',
                           get_cmd=':CALC1:FORM?',
                           set_cmd=':CALC1:FORM {}',
                           vals=vals.Enum('MLOG', 'PHAS',
                                          'GDEL',
                                          'SCOM', 'SMIT', 'SADM',
                                          'POL', 'MLIN',
                                          'SWR', 'REAL', 'IMAG',
                                          'UPH', 'PPH', 'SLIN', 'SLOG', )
                           )
        self.add_parameter('sweep_type',
                           get_cmd=':SENS1:SWE:TYPE?',
                           set_cmd=':SENS1:SWE:TYPE {}',
                           vals=vals.Enum('LIN', 'LOG', 'SEGM', 'POW')
                           )

        self.add_parameter('power_start',
                           get_cmd=':SOUR1:POW:STAR?',
                           set_cmd=':SOUR1:POW:STAR {}',
                           unit='dBm',
                           get_parser=float,
                           vals=vals.Numbers(-85, 10)
                           )
        self.add_parameter('power_stop',
                           get_cmd=':SOUR:POW:STOP?',
                           set_cmd=':SOUR1:POW:STOP {}',
                           unit='dBm',
                           get_parser=float,
                           vals=vals.Numbers(-85, 10)),
        self.add_parameter('num_points',
                           get_cmd=':SENS1:SWE:POIN?',
                           set_cmd=':SENS1:SWE:POIN {}',
                           vals=vals.Ints(1, 1601),
                           get_parser=int
                           )
        self.add_parameter('ifbw',
                           get_cmd=':SENS1:BWID?',
                           set_cmd=':SENS1:BWID {}',
                           vals=vals.Numbers(10, 1.5e6),
                           get_parser=float)
        self.add_parameter('smoothing',
                           get_cmd=':CALC1:SMO:STAT?',
                           set_cmd=':CALC1:SMO:STAT {}',
                           get_parser=float
                           )
        self.add_parameter('activate_tr',
                           get_cmd=':CALC:PAR:MNUM:SEL?',
                           set_cmd=':CALC:PAR:MNUM:SEL {}',
                           vals=vals.Ints(1, 15),
                           get_parser=int
                           )

    def turn_on_win(self, Window_num):
        self.write(f"DISP:WIND{Window_num}:STAT ON")

    def turn_off_win(self, Window_num):
        self.write(f"DISP:WIND{Window_num}:STAT OFF")

    def delete_all_set(self):
        self.write("SYST:FPR")

    def select_win_and_tr(self, win, tr):
        self.write(f'DISP:WIND{win}:TRAC{tr}:SEL')

    def set_active_channel(self, ch: int):
        self.write(f":SYST:ACT:CHAN {ch}")
        print(f"In channel {ch}")

    def getfdata(self):
        '''
        Gets freq stimulus data, returns array

        Input:
            None
        Output:
            freqvalues array (Hz)
        '''
        logging.info(__name__ + ' : get f stim data')
        strdata = str(self.ask(f':SENS1:FREQ:DATA?'))
        return np.array(list(map(float, strdata.split(','))))


    def gettrace(self, format = 'POL', ch = None, mnum = 1):
        '''
        Gets amp/phase stimulus data, returns 2 arrays
        Will go to polar coordiante to collect data more efficient, and go back to original trform after data is collected.
        Input:
            None
        Output:
            mags (dB) phases (rad)
        '''
        if ch == None:
            ch = self.current_ch()
        logging.info(__name__ + ' : get amp, phase stim data')

        print(f"Collecting data for Channel {ch}")

        self.write('FORM ASC')  # ASCII output
        self.write(f"CALC{ch}:PAR:MNUM:SEL")  # Select measurement number

        self.write(f"CALC{ch}:FORM {format}")  # Set to polar format

        strdata = str(self.ask(f':CALC{ch}:DATA? FDATA'))  # number after CALC indicate the channel we are measuring, we use 2 here because on the broad amp setting ch2 is the S21 value


        data = np.array(strdata.split(',')).astype(float)

        if len(data) % 2 == 0:
            print('reshaping data')
            data = data.reshape(int(len(data) / 2), 2)
            real = data[:, 0]
            imag = data[:, 1]
            mag = 20 * np.log10(np.sqrt(real ** 2 + imag ** 2))
            phs = np.arctan2(imag, real)
            #phs_unwrap = np.unwrap(phs)

            #phs_delay = (phs_unwrap + freqs * elec_delay  * 2 * np.pi) % (2 * np.pi)

            magAndPhase = np.zeros((2, len(real)))
            magAndPhase[0] = mag
            magAndPhase[1] = phs

            return magAndPhase
        else:
            return data  # .transpose() # mags, phase

    def average(self, number, format = 'POL', ch = None, timeout = 10):

        # setting averaging timeout, it takes 52.02s for 100 traces to average with 1601 points and 2kHz IFBW, so
        '''
        Sets the number of averages taken, waits until the averaging is done, then gets the trace
        '''
        if ch is None:
            ch = self.current_ch()

        self.set_active_channel(ch)
        cat = self.ask(f"CALC{ch}:PAR:CAT?")
        items = cat.strip('"').split(',')
        average_check = items_to_ch_in_bin(items)
        assert number > 0

        prev_trform = self.ask(f':CALC{ch}:FORM?')
        self.write(f"TRIG:SOUR IMM")  # Immediate triggerz
        self.write(f"CALC{ch}:MEAS:FORM {format}")  # change format to POL
        self.write(f"SENS{ch}:AVER ON")  # turn on aver
        self.write(f'SENS{ch}:AVER:COUN {number}')  # set ave to avgnum
        self.write(f'SENS{ch}:AVER:CLE') # restart ave




        get_status_bin = lambda: bin(int(self.ask(":STAT:OPER:AVER1:COND?")))

        # wait until bits 2, 13, 14 from right are all 1
        success = wait_until_selected_bits_are_one(get_status_bin, indices=average_check, timeout=timeout)

        if success:
            print("All selected bits are 1 — continue collecting.")
            # your processing code here
        else:
            print("Timeout reached before condition met.")
            return

        # sleep_time = float(self.ask(f'SENS{ch}:SWE:TIME?')) # determine sleeping time
        # print(f"Waiting {sleep_time}s for {number} averages...")
        # time.sleep(sleep_time)

        data = self.gettrace(ch = ch,format = format)

        self.write(f':CALC{ch}:FORM {prev_trform}')
        return data

    def average_restart(self):
        self.write('SENS1:AVER:CLE')


    def list_active_measurement(self,channel = 1):
        """
           Parses the response from CALC1:PAR:CAT? into (scpi_name, meas_type) pairs.

           Example input:
           '"CH1_S21_1,S21,CH1_CompIn21_12,CompIn21,CH1_DeltaGain21_13,DeltaGain21"'
           """
        # Strip quotes if present and split by comma
        strval = str(self.ask(f"CALC{channel}:PAR:CAT?"))

        items = strval.strip('"').split(',')

        # Group into (scpi_name, meas_type) pairs
        return [(items[i], items[i + 1]) for i in range(0, len(items), 2)]

    def get_active_channels(self, max_channels=8):
        """
        Return a list of channel numbers that have at least one measurement defined.
        """
        active_channels = []
        for ch in range(1, max_channels + 1):
            try:
                result = self.ask(f"CALC{ch}:PAR:CAT?").strip('"').strip()
                if result and result != "NO CATALOG":
                    active_channels.append(ch)
            except Exception:
                continue  # Channel doesn't exist or timed out
        return active_channels



    def set_to_manual(self, trform = 'PHAS'):
        self.rfout(1)
        self.averaging(1)
        self.avgnum(1)
        self.average_trigger(0)
        self.trform(trform)
        self.trigger_source('MAN')

    def auto_scale(self):
        self.write(':DISP:WIND1:TRAC1:Y:AUTO')


    def getSweepData(self):
        '''
        Gets stimulus data in displayed range of active measurement, returns array
        Will return different data depending on sweep type.

        For example:
            power sweep: 1xN array  of powers in dBm
            frequency sweep: 1xN array of freqs in Hz
        Input:
            None
        Output:
            sweep_values (Hz, dBm, etc...)
        '''
        self.write('FORM ASC')  # or 'FORMat:DATA ASCii'

        logging.info(__name__ + ' : get stim data')
        strdata = str(self.ask(':SENS1:X:VAL?'))
        return np.array(list(map(float, strdata.split(','))))


    def savetrace(self, directory, name, avgnum=10, ch = None):
        if ch == None:
            ch = self.current_ch()
        data = dd.DataDict(
            frequency=dict(unit='Hz'),
            power=dict(axes=['frequency'], unit='dB'),
            phase=dict(axes=['frequency'], unit='Degrees'),
        )

        prev_trform = self.trform()
        self.write(f'FORM ASC')
        with dds.DDH5Writer(directory, data, name=name) as writer:
            # get x axis
            strdata = str(self.ask(f':SENS{ch}:X:VAL?'))
            freqs = np.array(list(map(float, strdata.split(','))))  # 1XN array, N in [1601,1000]
            vnadata = np.array(self.average(avgnum, ch))  # 2xN array, N in [1601, 1000]
            vnadata[1] = vnadata[1] *180 / np.pi
            writer.add_data(
                frequency=freqs,
                power= vnadata[0] ,
                phase=vnadata[1]
            )
            # self.filepath = writer.filepath

        self.trform(prev_trform)
        #self.set_to_manual()

        return directory + '\\' + name, prev_trform



    def list_all_active_measurements(self, max_channels=8):
        """
        Return a dictionary {channel_number: [(scpi_name, meas_type), ...]}
        for all active channels with measurements.
        """
        active = {}

        for ch in range(1, max_channels + 1):
            try:
                cat = self.ask(f"CALC{ch}:PAR:CAT?").strip('"').strip()
                if not cat or cat == "NO CATALOG":
                    continue

                items = cat.split(',')
                meas_list = [(items[i], items[i + 1]) for i in range(0, len(items), 2)]
                active[ch] = meas_list

            except Exception as e:
                continue  # skip if the channel query fails

        # Optional: print in readable format
        for ch, measurements in active.items():
            print(f"Channel {ch}:")
            for name, mtype in measurements:
                print(f"  {name} → {mtype}")
            #print()

        return active
    def current_ch(self):
        """
            Queries the instrument for the currently active channel
            and returns it as an integer.
            """
        resp = self.ask(":SYST:ACT:CHAN?")
        return int(resp.strip())

    def activate_msmt(self):
        "activate the msmt with in the channel"
        ch = self.current_ch()
        return self.ask(f"CALC{ch}:PAR:CAT?")

    def get_all_traces(self, ch=None):
        if ch is None:
            ch = self.current_ch()
        raw = self.ask(f":CALC{ch}:PAR:CAT?").strip()
        trace_info = raw.strip('"').split(',')
        trace_names = trace_info[::2]  # every other item is the trace name
        return trace_names

    def save_all_traces(self, directory, name, channel=None, avgnum=10):
        if channel is None:
            channel = self.current_ch()
        # not working yet
        """
        Save all active measurements in the same format as savetrace().
        Each trace will be saved as <base_name>_<measname>.h5
        """
        from plottr.data import datadict as dd
        from plottr.data.datadict_storage import DDH5Writer
        import numpy as np
        import os

        cat = self.ask(f"CALC{channel}:PAR:CAT?")
        items = cat.strip('"').split(',')

        prev_trform = self.trform()

        self.write(f'FORM{channel} ASC')  # or 'FORMat:DATA ASCii'



        logging.info(__name__ + ' : get stim data')
        strdata = str(self.ask(f':SENS{channel}:X:VAL?'))
        freqs = np.array(list(map(float, strdata.split(','))))



        for i in range(0, len(items), 2):
            scpi_name = items[i]
            sparam = items[i + 1]
            #print(f"Saving: {scpi_name} ({sparam})")

            self.write(f"CALC{channel}:PAR:MNUM:SEL")
            # Select the TRIG  mode
            self.write("TRIG:SOUR IMM")
            self.write(f"SENS{channel}:AVER ON")
            # Select the trace by name
            self.write(f"CALC{channel}:PAR:SEL '{scpi_name}'")
            # POL coord
            self.write(f"CALC:MEAS{channel}:FORM POL")
            # restart ave
            self.write(f'SENS{channel}:AVER:CLE')
            # set ave to avgnum
            self.write(f'SENS{channel}:AVER:COUN {avgnum}')
            sleep_time = float(self.ask(f'SENS{channel}:SWE:TIME?'))*avgnum
            print(f"Waiting {sleep_time}s for {avgnum} averages...")
            time.sleep(sleep_time)

            self.write("FORM ASC")

            # Average and convert to complex
            raw = self.ask(f"CALC{channel}:DATA? FDATA")
            data = np.array(raw.split(',')).astype(float)
            print('reshaping data')
            data = data.reshape(int(len(data) / 2), 2)
            real = data[:, 0]
            imag = data[:, 1]
            mag = 20 * np.log10(np.sqrt(real ** 2 + imag ** 2))

            phs = np.arctan2(imag, real)
            phs = phs * 180 / np.pi
            print(scpi_name)

            # Define DataDict
            data = dd.DataDict(
                frequency=dict(unit='Hz'),
                power=dict(axes=['frequency'], unit='dB'),
                phase=dict(axes=['frequency'], unit='Degrees'),
            )

            filename = f"{name}_{sparam}_ch{channel}"
            filepath = os.path.join(directory, filename)

            with DDH5Writer(directory, data, name=filename) as writer:
                writer.add_data(
                    frequency=freqs,
                    power=mag,
                    phase=phs,
                )

            self.trform(prev_trform)
        #self.set_to_manual()

        return f"Saved all traces to {directory}"

    def save_all_traces_one_file(self, directory, name, channel=None, avgnum=10):
        """input the channel you want to collect the data from, and all the traces will be saved in one ddh5 file
           TO make the code be able to measure all channel, I use SCPC commend instead of the function I defined.
           Could visit here for more SCPI on VNA: https://helpfiles.keysight.com/csg/N52xxB/help.htm?#t=Programming%2FGPIB_Example_Programs%2FSCPI_Example_Programs.htm
        """
        if channel is None:
            channel = self.current_ch()

        from plottr.data import datadict as dd
        from plottr.data.datadict_storage import DDH5Writer
        import numpy as np
        import os
        import time

        cat = self.ask(f"CALC{channel}:PAR:CAT?")
        items = cat.strip('"').split(',')


        self.write(f'FORM ASC')

        logging.info(__name__ + ' : get stim data')
        strdata = str(self.ask(f':SENS{channel}:X:VAL?'))
        freqs = np.array(list(map(float, strdata.split(','))))

        # Build DataDict structure
        datadict_args = {
            'frequency': dict(unit='Hz')
        }

        all_data = {
            'frequency': freqs
        }
        self.write("TRIG:SOUR IMM")  # set trigger source to internal
        self.write(f'SENS{channel}:AVER:COUN {avgnum}')
        self.write(f"SENS{channel}:AVER ON")  # turn on aver
        self.write(f'SENS{channel}:AVER:CLE')  # restart aveg

        for i in range(0, len(items), 2):
            scpi_name = items[i]
            ch, tr = parse_meas_name(items[i])
            sparam = items[i + 1]
            prev_trform = self.ask(f"CALC{channel}:MEAS{tr}:FORM?")  # identify the current format
            self.write(f"CALC{channel}:PAR:SEL '{scpi_name}'")   # select the desire trace
            self.write(f"CALC{channel}:MEAS{tr}:FORM POL")  # change format to POL


            # sleep_time = float(self.ask(f'SENS{channel}:SWE:TIME?'))*avgnum # estimate the average time
            # print(f"Waiting {sleep_time}s for {avgnum} averages...")
            #
            # time.sleep(sleep_time)

            raw = self.ask(f"CALC{channel}:DATA? FDATA")  # get data from selected trace
            data = np.array(raw.split(',')).astype(float)
            data = data.reshape(int(len(data) / 2), 2)
            real = data[:, 0]
            imag = data[:, 1]
            mag = 20 * np.log10(np.sqrt(real ** 2 + imag ** 2))

            phs = np.arctan2(imag, real)
            phs = phs * 180 / np.pi
            # Add this trace's data to dict
            mag_key = f"power_{scpi_name}"
            phs_key = f"phase_{scpi_name}"

            datadict_args[mag_key] = dict(axes=['frequency'], unit='dB')
            datadict_args[phs_key] = dict(axes=['frequency'], unit='Degrees')

            all_data[mag_key] = mag
            all_data[phs_key] = phs

            self.write(f"CALC{channel}:MEAS{tr}:FORM {prev_trform}")   # change format back to prev_trform
        data_dict = dd.DataDict(**datadict_args)
        data_dict.validate()  # Optional check

        filename = f"{name}_ch{channel}_avg_{avgnum}"
        filepath = os.path.join(directory, filename)

        with DDH5Writer(directory, data_dict, name=filename) as writer:
            writer.add_data(**all_data)


        return f"Saved all traces to {filepath}"

    def save_all_traces_one_file_new_ave(self, directory, name, format = 'POL', channel=None, avgnum=10,time_out = 10):
        """input the channel you want to collect the data from, and all the traces will be saved in one ddh5 file
           TO make the code be able to measure all channel, I use SCPC commend instead of the function I defined.
           Could visit here for more SCPI on VNA: https://helpfiles.keysight.com/csg/N52xxB/help.htm?#t=Programming%2FGPIB_Example_Programs%2FSCPI_Example_Programs.htm
           Format : the format we use to store the data, for S para, we use POL could extract data more efficient, for delay we use "GDEL

        """
        if channel is None:
            channel = self.current_ch()

        from plottr.data import datadict as dd
        from plottr.data.datadict_storage import DDH5Writer
        import numpy as np
        import os
        import time
        self.set_active_channel(channel)
        cat = self.ask(f"CALC{channel}:PAR:CAT?")
        items = cat.strip('"').split(',')
        average_check = items_to_ch_in_bin(items)
        startfreq = self.fstart()

        self.write(f'FORM ASC')

        logging.info(__name__ + ' : get stim data')
        strdata = str(self.ask(f':SENS{channel}:X:VAL?'))
        freqs = np.array(list(map(float, strdata.split(','))))

        # Build DataDict structure
        datadict_args = {
            'frequency': dict(unit='Hz')
        }

        all_data = {
            'frequency': freqs
        }
        self.write("TRIG:SOUR IMM")  # set trigger source to internal
        self.write(f"SENS{channel}:AVER ON")  # turn on aver
        self.write(f'SENS{channel}:AVER:CLE')  # restart aveg
        self.write(f'SENS{channel}:AVER:COUN {avgnum}')

        # check if average is done

        get_status_bin = lambda: bin(int(self.ask(":STAT:OPER:AVER1:COND?")))

        # wait until bits 2, 13, 14 from right are all 1
        success = wait_until_selected_bits_are_one(get_status_bin, indices=average_check, timeout=time_out)

        if success:
            print("All selected bits are 1 — continue collecting.")
            # your processing code here
        else:
            print("Timeout reached before condition met.")
            return

        for i in range(0, len(items), 2):
            scpi_name = items[i]
            ch, tr = parse_meas_name(items[i])
            sparam = items[i + 1]
            prev_trform = self.ask(f"CALC{channel}:MEAS{tr}:FORM?")  # identify the current format
            self.write(f"CALC{channel}:PAR:SEL '{scpi_name}'")  # select the desire trace

            self.write(f"CALC{channel}:MEAS{tr}:FORM {format}")  # change format to "format"

            if format == 'POL':

                # sleep_time = float(self.ask(f'SENS{channel}:SWE:TIME?')) * avgnum  # estimate the average time
                # print(f"Waiting {sleep_time}s for {avgnum} averages...")
                #
                # time.sleep(sleep_time)


                # data collection and transformation
                raw = self.ask(f"CALC{channel}:DATA? FDATA")  # get data from selected trace
                data = np.array(raw.split(',')).astype(float)
                data = data.reshape(int(len(data) / 2), 2)
                real = data[:, 0]
                imag = data[:, 1]
                mag = 20 * np.log10(np.sqrt(real ** 2 + imag ** 2))

                phs = np.arctan2(imag, real)
                phs = phs * 180 / np.pi
                # Add this trace's data to dict
                mag_key = f"power_{scpi_name}"
                phs_key = f"phase_{scpi_name}"

                datadict_args[mag_key] = dict(axes=['frequency'], unit='dB')
                datadict_args[phs_key] = dict(axes=['frequency'], unit='Degrees')

                all_data[mag_key] = mag
                all_data[phs_key] = phs
            else:
                if format == 'MLOG':
                    unit = 'dB'
                elif format in ['PHAS', 'UPH']:
                    unit = 'degrees'
                elif format == 'GDEL':
                    unit = 'seconds'
                elif format in ['POL', 'COMP']:
                    unit = 'real/imag pairs'
                else:
                    unit = 'unitless'

                raw = self.ask(f"CALC{channel}:DATA? FDATA")  # get data from selected trace
                data = np.array(raw.split(',')).astype(float)

                # Add this trace's data to dict
                mag_key = f"group_delay_{scpi_name}"

                datadict_args[mag_key] = dict(axes=['frequency'], unit=unit)

                all_data[mag_key] = data

            self.write(f"CALC{channel}:MEAS{tr}:FORM {prev_trform}")  # change format back to prev_trform
        data_dict = dd.DataDict(**datadict_args)
        data_dict.validate()  # Optional check

        filename = f"{name}_ch{channel}_avg_{avgnum}_for_{format}"
        filepath = os.path.join(directory, filename)

        with DDH5Writer(directory, data_dict, name=filename) as writer:
            writer.add_data(**all_data)

        return f"Saved all traces to {filepath}"

    def save_all_traces_one_file_new_ave_group_phase(self, directory, name, channel=None, avgnum=10,time_out = 10):
        """input the channel you want to collect the data from, and all the traces will be saved in one ddh5 file
           TO make the code be able to measure all channel, I use SCPC commend instead of the function I defined.
           Could visit here for more SCPI on VNA: https://helpfiles.keysight.com/csg/N52xxB/help.htm?#t=Programming%2FGPIB_Example_Programs%2FSCPI_Example_Programs.htm


        """
        if channel is None:
            channel = self.current_ch()

        from plottr.data import datadict as dd
        from plottr.data.datadict_storage import DDH5Writer
        import numpy as np
        import os
        import time
        self.set_active_channel(channel)
        cat = self.ask(f"CALC{channel}:PAR:CAT?")
        items = cat.strip('"').split(',')
        average_check = items_to_ch_in_bin(items)


        self.write(f'FORM ASC')

        logging.info(__name__ + ' : get stim data')
        strdata = str(self.ask(f':SENS{channel}:X:VAL?'))
        freqs = np.array(list(map(float, strdata.split(','))))

        # Build DataDict structure
        datadict_args = {
            'frequency': dict(unit='Hz')
        }

        all_data = {
            'frequency': freqs
        }
        self.write("TRIG:SOUR IMM")  # set trigger source to internal
        self.write(f"SENS{channel}:AVER ON")  # turn on aver
        self.write(f'SENS{channel}:AVER:CLE')  # restart aveg

        self.write(f'SENS{channel}:AVER:COUN {avgnum}')
        # check if average is done

        get_status_bin = lambda: bin(int(self.ask(":STAT:OPER:AVER1:COND?")))

        # wait until bits 2, 13, 14 from right are all 1
        success = wait_until_selected_bits_are_one(get_status_bin, indices=average_check, timeout=time_out)

        if success:
            print("All selected bits are 1 — continue collecting.")
            # your processing code here
        else:
            print("Timeout reached before condition met.")
            return

        for i in range(0, len(items), 2):
            scpi_name = items[i]
            ch, tr = parse_meas_name(items[i])
            sparam = items[i + 1]
            prev_trform = self.ask(f"CALC{channel}:MEAS{tr}:FORM?")  # identify the current format
            self.write(f"CALC{channel}:PAR:SEL '{scpi_name}'")  # select the desire trace
            self.write(f"CALC{channel}:MEAS{tr}:FORM GDEL")  # change format to GDEL


            # sleep_time = float(self.ask(f'SENS{channel}:SWE:TIME?')) * avgnum  # estimate the average time
            # print(f"Waiting {sleep_time}s for {avgnum} averages...")
            #
            # time.sleep(sleep_time)


            # data collection and transformation
            raw = self.ask(f"CALC{channel}:DATA? FDATA")  # get data from selected trace
            data = np.array(raw.split(',')).astype(float)

            # Add this trace's data to dict
            mag_key = f"group_delay_{scpi_name}"


            datadict_args[mag_key] = dict(axes=['frequency'], unit='Sec')


            all_data[mag_key] = data


            self.write(f"CALC{channel}:MEAS{tr}:FORM {prev_trform}")  # change format back to prev_trform
        data_dict = dd.DataDict(**datadict_args)
        data_dict.validate()  # Optional check

        filename = f"{name}_ch{channel}_avg_{avgnum}"
        filepath = os.path.join(directory, filename)

        with DDH5Writer(directory, data_dict, name=filename) as writer:
            writer.add_data(**all_data)

        return f"Saved all traces to {filepath}"

        # Command to preset the instrument and deletes the default trace, measurement, and window



if __name__ == "__main__":
    pnax = find_or_create_instrument(Hat_N5245A, "PNAX", address = f"TCPIP0::192.168.3.26::INSTR", timeout = 30)

    #pnax.set_active_channel(2)
    #pnax.visa_handle.timeout = 3000  # 3 seconds in milliseconds

    #pnax.rfout(1)
    filename = r"SVC_RCF_group_delay"
    dir = r"Y:\data\NIST2024_data005\20250503_TxCooldown\SVC_RCF"
    # dir = r"C:\Users\PXIe1\Documents\test"
    #
    filepath = dir +"\\ " + filename
    pnax.power(-40)
    print("Saving...")


    #ENA
    # fp, trace = pnax.savetrace(dir, filename, avgnum=3)
    #pnax.set_to_manual()
    print("Complete!")
    #print("Path: ", fp)
    #pnax.rfout(0)
    # pnax.visa_handle.read_raw()

    #all_active_measurement = pnax.list_all_active_measurements()



