# yroko2
`yroko_board.py` runs continuously on the raspberry pi. This initalizes a SPI connection to the DAC board and a TCP connection to the qCode driver. In a forever loop, accepts a message from qCode driver, either a get or set (RAMP) request, and sends SPI message to DAC to execute accordingly.

`yroko_driver.py` contains yroko instantiation of qCode Instrument abstract class. `Instrument` class initializes TCP connection and contains reference to submodules `InstrumentChannel` which represent each of the 4 DAC boards in a yroko box. This class wraps getters/setters in a dynamic `Parameter` attribute bound to functions which construct strings sent over the TCP to the raspberry pi.
