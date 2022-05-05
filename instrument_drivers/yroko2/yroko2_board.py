import logging
import random
import socket
import sys
import time
from typing import List
import struct

import spidev
from gpiozero import DigitalOutputDevice

# TODO: need to rewrite RAMPing so doesn't use unnecessary reads and writes
# TODO: debug reset by peer error

"""@author Evan McKinney"""


class Yroko2Board:
    """Instantiating this class establishes a connection to Yroko2.0 boards

    Example with context manager:
    >>> yroko = Yroko2()
    >>> logging.basicConfig(level=logging.INFO)
    >>> with yroko as yk:
    >>>     #ramp up
    >>>     yk.ramp(channel=1, start_voltage=-.5, stop_voltage=0)
    >>>     #ramp down
    >>>     yk.ramp(channel=1, start_voltage=1, stop_voltage=-1)
    >>> print("done")

    Datasheet reference:
    https://www.analog.com/media/en/technical-documentation/data-sheets/ad5780.pdf
    """

    def __init__(self):
        # Serial Clock Input. Data is clocked into the input shift register on the falling edge of the serial clock input.
        # Data can be transferred at rates of up to 35 MHz
        # self.sclk = 11  # (gpio 11 -> pin 23) SPI0_SCLCK

        # Serial Data Input. This device has a 24-bit input shift register.
        # Data is clocked into the register on the falling edge of the serial clock input.
        # self.sdin = 10  # (gpio 10 -> pin 19) SPI0_MOSI

        # Serial Data Output. Data is clocked out on the rising edge of the serial clock input
        # self.sdout = -1

        # Level Triggered Control Input (Active Low). This is the frame synchronization signal for the input data.
        # When SYNC goes low, it enables the input shift register, and data is then transferred in on the falling edges
        # of the following clocks. The DAC is updated on the rising edge of SYNC.

        # Simple set up is to include for each eval-board its own GPIO pin to act as its enable bit
        # spidev has only 2 chip selects, but online suggestions indicate using arbitrary set of GPIO pins is perfectly fine
        # Make sure using GPIO pins not already reserved by spidev
        # nsync = 8 #(gpio 8  -> pin 24) SPI0_CEO_N
        self.channel_dict = {0: "GPIO6", 1: "GPIO12"}  # , 2: "GPIO16"}

        self.nsync = {
            channel: DigitalOutputDevice(gpio_pin)
            for channel, gpio_pin in self.channel_dict.items()
        }

        # Additional pins that can be moved from hardwired ground to board for additional hardware functionality
        # RESET, CLR, LDAC

        self.vrefp = 10
        self.vrefn = -10

    def __enter__(self):
        # open spi on 0,0 to use SPI0 MISO/MOSI pins
        self.spi = spidev.SpiDev(0, 0)
        # 35 MHz is max per datasheet but much higher than this value seems to break
        self.spi.max_speed_hz = 27777777
        # self.spi.max_speed_hz = 20000
        self.spi.bits_per_word = 8
        # SPI mode 3 for clock edges configuration
        self.spi.mode = 0b11
        # use our own GPIO pins for sync, lets have more than standard 2
        self.no_cs = True

        # power-on sequence
        logging.debug("Start power on sequence")
        for channel in self.channel_dict:
            self._configure_control(channel)

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        # Exception handling here
        self.spi.close()

    def _write_inputShiftRegister(self, channel: int, bytearray: List[int]):
        """The input shift register is 24 bits wide. Data is loaded into the device MSB first
        as a 24-bit word under the control of a serial clock input, SCLK
        Input Shift Register: DB23: W/R, DB22-DB20: Register Address, DB19-DB0: Register data"""
        if not channel in self.channel_dict:
            raise ValueError("Channel does not exist")

        # logging.debug(f"writing to SPI byte array {[bin(value)[2:].zfill(8) for value in bytearray]}")
        self.nsync[channel].off()
        self.spi.xfer2(bytearray)
        self.nsync[channel].on()

    def _configure_control(self, channel: int):
        """The DAC is removed from tristate by clearing the DACTRI bit,
        set BIN/2sC to 1 to treat D as nonsigned binary number (default is 2s complement),
        and the output clamp is removed by clearing the OPGND bit.
        """
        logging.debug(f"read channel {channel} control register before doing update")
        self._read_control(channel)

        configuration_string = [0x20, 0x00, 0x12]
        self._write_inputShiftRegister(channel, configuration_string)

    def _voltageToBytes(self, voltage_value: float):
        """:math:`V_{OUT} = \frac{(V_{REFP} - V_{REFN}) * D}{2^{18}} + V_{REFN}`"""
        # cap out of bounds values
        if voltage_value >= self.vrefp:
            # cap upper bound 1 bit less than vrefp, so fits in 18 bits
            voltage_value = (
                (self.vrefp - self.vrefn) * (2**18 - 1) / 2**18
            ) + self.vrefn
        if voltage_value < self.vrefn:
            voltage_value = self.vrefn

        # solve for d in transfer function equation
        d = ((voltage_value - self.vrefn) * 2**18) / (self.vrefp - self.vrefn)

        # float to int, may be lossy as determined by DAC resolution
        d = int(d)

        # convert to 24-bits of binary (18 bits with 6 leading 0s)
        # shift by 2, as DB0 and DB1 are don't cares
        voltage_binary = (bin(d << 2))[2:].zfill(24)

        # convert from bitstring to bytearray
        voltage_bytes = int(voltage_binary, 2).to_bytes(3, byteorder="big")

        return list(voltage_bytes)

    def _getDACValue(self, channel: int):
        """Reads and returns the D bitstring in DAC register"""
        dac_register_contents = self.read_dac(channel)
        d = [bin(v)[2:].zfill(8) for v in dac_register_contents]
        d = "".join([v for v in d])[4:-2]
        return d

    def _bytesToVoltage(self, d: str):
        return (self.vrefp - self.vrefn) * int(d, 2) / (2**18) + self.vrefn

    def set_voltage(self, channel: int, voltage_value: float):
        """writes to DAC register voltage_value as a byte array"""
        voltage_bytes = self._voltageToBytes(voltage_value)

        # write to DAC register
        configure_write_bytes = voltage_bytes
        dac_address = 0x10
        configure_write_bytes[0] += dac_address
        logging.debug(
            f"MOSI write to channel {channel} DAC: {[hex(value) for value in configure_write_bytes]}"
        )
        self._write_inputShiftRegister(channel, configure_write_bytes)

        # log the actual voltage value put in DAC
        logging.info(
            f"Set channel {channel} voltage to {self._bytesToVoltage(self._getDACValue(channel))}"
        )

    def getVoltageRange(self):
        """Returns operating range of output voltage as determined by VREP and VREFN supplies.
        If a voltage is set out of this range, it is capped to the max or min value"""
        return [self.vrefn, self.vrefp]

    def ramp(
        self,
        channel: int,
        start_voltage: float,
        stop_voltage: float,
        time_step: int = None,
    ):
        self.set_voltage(channel, start_voltage)
        if stop_voltage > start_voltage:
            step = self.increment_unit
        else:
            step = self.decrement_unit

        # call this function to match bit resolution
        stop_voltage = self._voltageToBytes(stop_voltage)
        stop_string = [bin(v)[2:].zfill(8) for v in stop_voltage]
        stop_string = "".join([v for v in stop_string])[4:-2]
        while self._getDACValue(channel) != stop_string:
            step(channel)

    def increment_unit(self, channel: int):
        """Increase voltage by single bit"""
        register_contents = self._getDACValue(channel)
        register_contents = int(register_contents, 2) + 1
        register_contents = bin(register_contents)[2:].zfill(18)
        new_voltage = self._bytesToVoltage(str(register_contents))
        self.set_voltage(channel, new_voltage)

    def decrement_unit(self, channel: int):
        """decrement voltage by single bit"""
        register_contents = self._getDACValue(channel)
        register_contents = int(register_contents, 2) - 1
        register_contents = bin(register_contents)[2:].zfill(18)
        new_voltage = self._bytesToVoltage(str(register_contents))
        self.set_voltage(channel, new_voltage)

    def blinker(self, channel: int, repeat: int):
        for r in range(repeat):
            self.set_voltage(channel, self.getVoltageRange()[1])
            time.sleep(3)
            self.set_voltage(channel, 0)

    def read_dac(self, channel: int):
        """The contents of all the on-chip registers can be read back via the SDO pin. Table 7 outlines how the registers are decoded.
        After a register has been addressed for a read, the next 24 clock cycles clock the data out on the SDO pin.
        The clocks must be applied while SYNC is low. When SYNC is returned high, the SDO pin is placed in tristate"""
        configure_read_bytes = [0x90, 0x00, 0x00]
        self._write_inputShiftRegister(channel, configure_read_bytes)

        # interpret the data from the MISO pin
        self.nsync[channel].off()
        register_contents = self.spi.readbytes(3)
        self.nsync[channel].on()

        logging.debug(
            f"MISO read from channel {channel} DAC contents: {[hex(value) for value in register_contents]}"
        )
        return register_contents

    def _read_control(self, channel: int):
        configure_read_bytes = [0xA0, 0x00, 0x00]
        self._write_inputShiftRegister(channel, configure_read_bytes)

        # interpret the data from the MISO pin
        self.nsync[channel].off()
        register_contents = self.spi.readbytes(3)
        self.nsync[channel].on()

        # logging.debug(f"MISO read channel {channel} control register contents: {[bin(value)[2:].zfill(8) for value in register_contents]}")
        logging.debug(
            f"MISO read from channel {channel} control contents: {[hex(value) for value in register_contents]}"
        )
        return register_contents


if __name__ == "__main__":
    """in main loop, recieve TCP messages from instrument driver"""
    yroko = Yroko2Board()
    # logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO)

    # #debug case
    # if True:
    #     with yroko as yk:
    #         yk.set_voltage(0, 2)
    #     quit()

    # set up socket
    BUFFER_SIZE = 64  # idk
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ("", 8888)  # socket.gethostname()
    # bind socket to this port
    sock.bind(server_address)
    # Listen for incoming connections
    sock.listen(1)

    # context manager handles SPI communication
    with yroko as yk:

        # iterate as instruments connect and disconnect
        while True:
            # wrap everything in try, so can close in finally case
            try:
                # wait for an incoming connection
                logging.info("Listening...")
                connection = None
                connection, client_address = sock.accept()
                logging.info(f"Connection established: {client_address}")

                # iterate over every tcp exchange
                while True:
                    # read_request()
                    data = connection.recv(BUFFER_SIZE)
                    connection.sendall(b"1")
                    # ignore empty init messages
                    if len(data) == 0:
                        continue

                    logging.info(f"TCP Recieved: {data}")

                    data_args = str(data, "utf-8").split(",")
                    channel = int(data_args[1])

                    if data_args[0] == "RAMP":
                        print("channel", channel)
                        print(float(data_args[1]), float(data_args[3]))
                        yk.ramp(
                            channel, float(data_args[2]), float(data_args[3])
                        )  # , data_args[4])
                        message = "RAMP_FINISHED".encode()

                    elif data_args[0] == "GET_DAC":
                        voltage = yk._bytesToVoltage(yk._getDACValue(channel))
                        message = bytearray(struct.pack("f", voltage))

                    else:
                        # fail, but won't be reachable
                        pass

                    # write_response()
                    logging.info(f"TCP sending: {message}")
                    acknowledgment = False
                    attempts = 0
                    while not acknowledgment and attempts < 3:
                        try:
                            sock.settimeout(3)
                            connection.sendall(message)
                            connection.recv(1)
                            acknowledgment = True
                        except socket.timeout:
                            attempts += 1
                            continue
                    if not acknowledgment:
                        raise Exception("TCP exchange unable to recieve acknowledgment")

            except ConnectionResetError:
                # driver forced closed, start listening again
                pass

            finally:
                # close_connection()
                logging.info("Close TCP")
                if connection is not None:
                    connection.close()

    # # ramp up
    # yk.ramp(channel=1, start_voltage=-0.5, stop_voltage=0)
    # # ramp down
    # yk.ramp(channel=1, start_voltage=1, stop_voltage=-1)
    # print("done")
