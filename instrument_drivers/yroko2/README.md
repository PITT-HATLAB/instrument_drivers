# yroko2.0
To ready the raspberry pi, run the `yroko2_board` python file. On success, the pi should print that it is listening on its TCP port.
```
pi@YROKO:~/Desktop/yroko2.0 $ python3 yroko2_board.py 
INFO:root:Listening...
```

Next, instantiate the instrument on your own computer - although you need a connection to the Texas switch. (This might be already done in a higher level import statement)
```python
from yroko2_driver import YrokoInstrument
yroko = YrokoInstrument(name="yroko_0")
```

During setup, the DAC board should set all output currents to 0A, then the instrument driver will set all output current to a true-zero offset.

Each channel contains a *current* `Parameter` object which binds to get/set methods, provides descriptive attributes (e.g. units), and validates input.

To use the get method
```python
yroko.channel_0.current()
```

To use the set method
```python
yroko.channel_0.current(.0001)
```

Additional info:
Status: Get and Set yroko_0 on channels 0 and 1 are operational. A handful of optimization TODOs left for cleanup.

`yroko_board.py` runs continuously on the raspberry pi. This initalizes a SPI connection to the DAC board and a TCP connection to the qCode driver. In a forever loop, accepts a message from qCode driver, either a get or set (RAMP) request, and sends SPI message to DAC to execute accordingly.

`yroko_driver.py` contains yroko instantiation of qCode `Instrument` abstract class. `Instrument` class initializes TCP connection and contains reference to submodules `InstrumentChannel` which represent each of the 4 DAC boards in a yroko box. This class wraps getters/setters in a dynamic `Parameter` attribute bound to functions, which get/set by constructing strings sent over the TCP to the raspberry pi.

Evan - known issues a) TCP crash then rpi says port already in use. b) if instrument crash, name "yroko_0' already in use needs to close or del(w/ gc). c) init needs a set all channels to 0

