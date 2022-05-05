# TODO: instantiate qccodes.instrument abstract class
# TODO: use info from original YROKO_Client.py to make work like other drivers in the lab
# TOOD: python multithread, mutex yroko
# -*- coding: utf-8 -*-

"""
A driver to control the Modular DAC using Qtlab
@author: Hatlab - Ryan Kaufman, Evan McKinney
"""

import logging
import random

# from instrument import Instrument
import socket
import sys
import time
import tkinter as tk
import tkinter.font as tkFont

import qcodes.utils.validators as vals
from qcodes import Instrument, InstrumentChannel, Parameter

import numpy as np

""""
Reference: https://qcodes.github.io/Qcodes/examples/writing_drivers/Creating-Instrument-Drivers.html#VisaInstrument:-a-more-involved-example
"""


class YrokoChannel(InstrumentChannel):
    """
    Class to hold the 4 yroko channels
    """

    def __init__(self, parent: Instrument, name: str, channel: int) -> None:
        """
        Args:
            parent: The Instrument instance to which the channel is
                to be attached.
            name: The 'colloquial' name of the channel
            channel: The channel int specifir
        """

        # this is an offset that was tuned to make sure that there was no jumping when you plug in the magnet.
        # TODO: this should be a dictionary, and different channels will be different on different instruments
        true_zero_list = [-0.00106811e-3, -0.00106811e-3, 0, 0]
        self.true_zero = true_zero_list[channel]
        self.resistance = 1000

        super().__init__(parent, name)

        self.current = Parameter(
            "current",
            get_cmd=self.get_current,
            get_parser=float,
            set_cmd=self.set_current,
            label="Current",
            unit="A",
            instrument=self,
            vals=vals.Numbers(-10 / self.resistance, 10 / self.resistance),
        )

        self.channel = channel

    def get_current(self):
        data = self.parent.TCP_Exchange(f"GET_DAC, {self.channel}")
        voltage = np.frombuffer(data, np.float32)[0]
        return voltage / self.resistance

    def set_current(self, new_current, ramp_rate=None):
        if ramp_rate is not None:
            # XXX will need to calculate a new ramp rate V/s using SPI frequency
            raise NotImplementedError

        old_current = self.current()
        old_voltage = old_current * self.resistance
        new_voltage = (new_current * self.resistance) - self.true_zero

        # NOTE: I believe self.vals is qcode native way for input validation but needs to be tested
        # if abs(new_voltage) > 10:
        #     raise Exception(
        #         "This device can't deliver more than 10mA in either direction"
        #     )

        min_precision_value = 0.156e-3  # Volts - from data sheet of EVAL board

        # "Seconds between successive discrete voltage changes, its a digital system so it's non-continuous,
        # i.e. this value is set so that for any deltaV,the step is the max precision of 15.25 mv and ramps at 0.1V/s, then with an added 2% safety zone"
        # time_step = 1.02 * min_precision_value / ramp_rate

        # int truncates, which in numbers > 0 is rounding dowm, so it will be slightly less precise
        # num_steps = int(abs(new_voltage - old_voltage) / min_precision_value)

        message = f"RAMP, {self.channel}, {old_voltage}, {new_voltage}"
        # ,{num_steps}, {time_step*1e6}

        # time_estimate = time_step * num_steps
        # print(
        #     "Time to ramp channel "
        #     + str(self.channel)
        #     + " to "
        #     + str(new_current * 1000)
        #     + " mA: "
        #     + str(time_estimate)
        #     + "s"
        # )
        print("Sending command and awaiting ramp completion...")

        # This would ideally send back RAMP_FINISHED
        ramp_conf = self.parent.TCP_Exchange(message)

        # TODO: clean up below, should verify RAMP_FINISHED
        # print(f"Ramp_Confirmation: {ramp_conf}")
        # print("Updating current value... ")
        time.sleep(0.01)  # give the server-side time to reset the feedback variable
        new_current = self.get_current()
        print("Verified current: " + str(new_current) + "mA")
        return new_current


class YrokoInstrument(Instrument):
    """
    This is the qcodes driver for the Yroko2.0
    Yroko Instrument class is primarily responisble for TCP exchanges to the yroko raspberry pi
    Yroko InstrumentChannel class is responsible for wrapping get and set methods into the TCP exchanges.
    """

    def __init__(self, name: str) -> None:
        """
        Args:
            name: Name to use internally in QCoDeS
            Name refers to the box of yrokos, Channel refers to each DAC board
        """
        super().__init__(name)

        # match given name to IP lookup table
        IP_dict = {"yroko_0": "169.254.6.22"}
        print(name)
        if name not in IP_dict.keys():
            raise Exception("Instrument name unknown")
        self.IP = IP_dict[name]

        # Add all the channels to the instrument
        valid_channels = [0, 1]  # ,2, 3]
        for ch in range(2):
            ch_name = f"channel_{ch}"
            channel = YrokoChannel(self, ch_name, ch)
            self.add_submodule(ch_name, channel)

        # display parameter, not sure what this does
        # Parameters NOT specific to a channel still belong on the Instrument object
        # In this case, the Parameter controls the text on the display
        # self.display_settext = Parameter(
        #     "display_settext",
        #     set_cmd=self._display_settext,
        #     vals=vals.Strings(),
        #     instrument=self,
        # )

        self.TCP_Connect()

        # set all channels to true zero, and confirm with a GET
        for channel_name, channel_ref in self.submodules.items():
            channel_ref.set_current(channel_ref.true_zero)
            print(
                "YROKO channel "
                + str(channel_name)
                + " current: "
                + str(channel_ref.current() * 1000)
                + "mA"
            )
        # print("Initialization Process Complete\n")
        self.connect_message()

    def TCP_Connect(self):
        # Create a TCP/IP connection
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 8888
        # Connect the socket to the port where the server is listening
        server_address = (
            self.IP,
            port,
        )
        print("Connecting to " + str(server_address[0]) + " port " + str(port))

        # 5 second timeout in case connection fails
        self.sock.settimeout(5)

        try:
            self.sock.connect(server_address)
        except socket.error:
            print("Caught exception socket.error, failed to connect")
            raise Exception(
                "TCP connect failed. You should verify that the raspberry pi is currently running yroko_board.py"
            )
            return 0

        print("Connection successful")
        return 1

    def TCP_Exchange(self, message, wait=True):
        """framework for sending a message and waiting for a response"""
        # TODO: rewrite, should have a timeout?
        print("Sending: " + message)
        acknowledgment = False
        attempts = 0
        while not acknowledgment and attempts < 3:
            try:
                self.sock.settimeout(3)
                self.sock.sendall(bytes(message, "utf-8"))
                self.sock.recv(1)
                acknowledgment = True
            except socket.timeout:
                attempts += 1
                continue
        if not acknowledgment:
            raise Exception("TCP exchange unable to recieve acknowledgment")
        # the system will wait until it receives something. So the server must send something for the client to be able to respond
        if wait:
            print("recieved acknolowedgment now waiting...")
            self.sock.settimeout(None)
            feedback = self.sock.recv(64)
            # send acknowledmgent
            self.sock.sendall("A".encode())
        else:
            feedback = b""
        print("raw feedback from server: ", feedback)
        return feedback  # don't str(feedback), let caller handle formatting

    def close(self):
        # as a final command, always 0 out current:
        try:
            print("begin zeroing all channels")
            for channel_ref in self.submodules.values():
                channel_ref.set_current(0)
        finally:
            self.sock.close()
            print("shutdown complete")
            super.close()
