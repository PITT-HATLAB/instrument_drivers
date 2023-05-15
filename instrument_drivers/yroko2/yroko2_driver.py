# -*- coding: utf-8 -*-
"""
A driver to control the Modular DAC using Qtlab
@author: Hatlab - Ryan Kaufman, Evan McKinney
"""

import logging
import random
import socket
import sys
import time
import numpy as np
import qcodes.utils.validators as vals
from qcodes import Instrument, InstrumentChannel, Parameter

""""
Example for reference: https://qcodes.github.io/Qcodes/examples/writing_drivers/Creating-Instrument-Drivers.html#VisaInstrument:-a-more-involved-example
"""

logging.basicConfig(level=logging.INFO)


class _YrokoChannel(InstrumentChannel):
    """
    Channel class represents each of the 4 DAC boards controlled by a raspberry pi
    https://qcodes.github.io/Qcodes/api/instrument/channel.html?highlight=channel#module-qcodes.instrument.channel
    """

    def __init__(self, parent: Instrument, name: str, channel: int) -> None:
        """
        Args:
            parent: The Instrument instance to which the channel is
                to be attached.
            name: The 'colloquial' name of the channel
            channel: The channel int specifier
        """
        super().__init__(parent, name)

        # this is an offset that was tuned to make sure that there was no jumping when you plug in the magnet.
        # TODO: this should be a dictionary, and different channels will be different on different instruments,
        # for now this is fine as is but needs to be modified as channels are expanded
        true_zero_list = [-0.00106811e-3, -0.00106811e-3, 0, 0]
        self.true_zero = true_zero_list[channel]
        self.resistance = 1000

        # https://qcodes.github.io/Qcodes/examples/Parameters/Parameters.html
        self.current = Parameter(
            "current",
            get_cmd=self._get_current,
            get_parser=float,
            set_cmd=self._set_current,
            label="Current",
            unit="A",
            instrument=self,
            vals=vals.Numbers(-10 / self.resistance, 10 / self.resistance),
        )

        self.channel = channel

    def _get_current(self) -> float:
        """GET method for channel's current"""
        data = self.parent.TCP_Exchange(f"GET_DAC, {self.channel}")
        # index data buffer by 0 since is a bytearray
        voltage = np.frombuffer(data, np.float32)[0]
        new_current = voltage / self.resistance
        logging.info(f"GET channel {self.channel} current: {1000 * new_current} mA")
        return new_current

    def _set_current(self, new_current, ramp_rate=None) -> float:
        """SET method for channel's current

        Args:
            new_current: current value in mA
            ramp_rate: not yet implemented
        Returns:
            new_current as confirmed by GET method
        """

        # NOTE: supposedely qcodes stores previous set in a buffer,
        # I'm not sure if self.current() actually calls GET or not
        old_current = self.current()  # GET method
        old_voltage = old_current * self.resistance
        new_voltage = (new_current * self.resistance) - self.true_zero

        if ramp_rate is not None:
            # XXX will need to calculate a new ramp rate V/s using SPI frequency
            raise NotImplementedError

            # min_precision_value = 0.156e-3  # Volts - from data sheet of EVAL board

            # "Seconds between successive discrete voltage changes, its a digital system so it's non-continuous,
            # i.e. this value is set so that for any deltaV,the step is the max precision of 15.25 mv and ramps at 0.1V/s, then with an added 2% safety zone"
            # time_step = 1.02 * min_precision_value / ramp_rate

            # int truncates, which in numbers > 0 is rounding dowm, so it will be slightly less precise
            # num_steps = int(abs(new_voltage - old_voltage) / min_precision_value)

        message = f"RAMP, {self.channel}, {old_voltage}, {new_voltage}"
        # ,{num_steps}, {time_step*1e6}

        # time_estimate = time_step * num_steps

        logging.info("Sending command and awaiting ramp completion...")
        ramp_conf = self.parent.TCP_Exchange(message)
        if ramp_conf != b"RAMP_FINISHED":
            raise Exception("RAMP FAILED")

        # verify using GET
        new_current = self.current()
        logging.info(
            f"Verify channel {self.channel} SET current: {1000 * new_current} mA"
        )
        return new_current


class YrokoInstrument(Instrument):
    """
    Instrument class abstracts connection to raspberry pi controlling a set of 4 DAC boards
    Yroko Instrument class is primarily responisble for TCP exchanges whereas the channels construct the message in the GET and SET methods
    """

    def __init__(self, name: str) -> None:
        """
        Args:
            name: name acts as a reference for IP address, e.g. yroko_0, yroko_1, ...
        """
        super().__init__(name)

        # match given name to IP lookup table
        IP_dict = {"yroko_0": "192.168.6.94"}
        if name not in IP_dict.keys():
            raise Exception("Instrument name not given IP address")
        self.IP = IP_dict[name]

        # Add all the channels to the instrument
        # TODO: each raspberry pi should have 4, current there are only 2
        valid_channels = [0, 1]  # ,2, 3]
        for ch in range(2):
            ch_name = f"channel_{ch}"
            channel = _YrokoChannel(self, ch_name, ch)
            self.add_submodule(ch_name, channel)

        self.TCP_Connect()

        # set all channels to true zero
        for channel_name, channel_ref in self.submodules.items():
            channel_ref.current(channel_ref.true_zero)
            logging.info(
                f"YROKO channel {channel_name} current: {1000*channel_ref.current()} mA"
            )

        self.connect_message()

    def TCP_Connect(self):
        """Create a TCP/IP connection"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 8888

        # Connect the socket to the port where the server is listening
        server_address = (self.IP, port)
        logging.info(f"Connecting to {str(server_address[0])} port {str(port)}...")

        # 5 second timeout before initial connection fails
        self.sock.settimeout(5)

        try:
            self.sock.connect(server_address)
        except socket.error:
            raise Exception(
                "TCP connect failed. You should verify that the raspberry pi is currently running yroko_board.py"
            )
            self.TCP_Disconnect()
            return 0

        logging.info("Initial connection successful")
        return 1

    def TCP_Disconnect(self):
        self.sock.close()

    def TCP_Exchange(self, message, wait=True):
        """Framework for sending and recieving over TCP with acknowledgments

        Args:
            message: string to be sent to pi
            wait: boolean for whether to wait for RAMP completition, to be safe leave as true
        """
        # NOTE: I believe python's socket package should already be doing acknowledgments, I have added it here because sometimes the TCP's were still never going through
        # TCP is failing when Instrument gets disconnected without the raspberry pi knowing connection was broken
        # rewriting this should make the need for this unnecessary

        logging.debug(f"Sending: {message}")

        acknowledgment = False
        attempts = 0
        while not acknowledgment and attempts < 1:
            try:
                self.sock.settimeout(3)
                self.sock.sendall(bytes(message, "utf-8"))

                # wait for ack
                self.sock.recv(1)
                acknowledgment = True
            except socket.timeout:
                attempts += 1
                continue
        if not acknowledgment:
            raise Exception(
                "TCP exchange unable to receive acknowledgment, raspPi and Insturment got disconnected without them realizing, restart board.py and try again."
            )

        # recieved an ack, life is good :)
        if wait:
            logging.debug(
                "Initial acknowledgment recieved, waiting for data response..."
            )

            # because ack was success, can disable timeout for a long RAMP completition wait
            self.sock.settimeout(None)
            feedback = self.sock.recv(64)

            # send back an acknowledmgent
            self.sock.sendall("A".encode())

        else:
            feedback = b""
        logging.debug("Raw feedback from server: ", feedback)

        # Let caller handle formatting, return as raw bytearray
        return feedback

    def close(self):
        """Shutown command. Zeros as channels and closes TCP"""
        try:
            # set all channels to true zero
            for channel_name, channel_ref in self.submodules.items():
                channel_ref.current(channel_ref.true_zero)
                logging.info(
                    f"YROKO channel {channel_name} current: {1000*channel_ref.current()} mA"
                )
        finally:
            self.TCP_Disconnect()
            logging.info("Shutdown complete!")
            super().close()
