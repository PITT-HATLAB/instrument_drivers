# yroko2.0
To ready the raspberry pi, run the `yroko2_board` python file. On success, the pi should print that it is listening on its TCP port.
To run python file in terminal, simply open terminal, and use command:
```shell
./yroko_run.sh
```
Or manually using:
```shell
pi@YROKO:~/Desktop/yroko2.0 $ python3 yroko2_board.py 
INFO:root:Waiting for connection...
```

Next, instantiate the instrument on your own computer - although you need a connection to the Texas switch. (This might be already done in a higher level import statement)
```python
from qcodes.instrument import find_or_create_instrument
yroko = find_or_create_instrument(YrokoInstrument, "yroko_0", recreate=True)
```
On success, all output channels will be initalized to 0A, and raspberry-pi will display `INFO:root:Listening...` to indicate it is ready for commands from the driver. Each channel contains a *current* `Parameter` object which binds to get/set methods, provides descriptive attributes (e.g. units), and validates input.

## Exaple usage:
```python
#GET from a single channel
ch0_current = yroko.channel_0.current()
```
```
INFO:root:GET channel 0 current: 0.4999542236328125 mA
```

```python
#iterate over GETs
for channel in yroko.submodules.values():
    curret_value = channel.current()
```
```
INFO:root:GET channel 0 current: 0.4999542236328125 mA\
INFO:root:GET channel 1 current: 0.4999542236328125 mA
```

```python
#set a single channel
yroko.channel_0.current(.0001)
```
```
INFO:root:GET channel 0 current: 0.4999542236328125 mA\
INFO:root:Sending command and awaiting ramp completion...\
INFO:root:GET channel 0 current: 0.099945068359375 mA\
INFO:root:Verify channel 0 SET current: 0.099945068359375 mA
```

```python
#iterate over SETs
for index, channel in enumerate(yroko.submodules.values()):
    channel.current((1+index)*.0005)
```
```
INFO:root:GET channel 0 current: 0.0 mA\
INFO:root:Sending command and awaiting ramp completion...\
INFO:root:GET channel 0 current: 0.4999542236328125 mA\
INFO:root:Verify channel 0 SET current: 0.4999542236328125 mA\
INFO:root:GET channel 1 current: 0.4999542236328125 mA\
INFO:root:Sending command and awaiting ramp completion...\
INFO:root:GET channel 1 current: 0.9999847412109375 mA\
INFO:root:Verify channel 1 SET current: 0.9999847412109375 mA
```

## Additional info:
Status: Get and Set yroko_0 on channels 0 and 1 are operational. Some minor TODOs left for Evan to cleanup. I also think that TCP communication protocols still need to be changed to accomdate for the touchscreen or other computers acting as drivers simultaneously. Either needs multiple ports to communicate on, or to have driver end and restart connection after every request.

`yroko_board.py` runs on the raspberry pi. This initalizes a SPI connection to the DAC board and a TCP connection to the qCode driver. In a forever loop, accepts a message from qCode driver, either a get or set (RAMP) request, and sends SPI message to DAC to execute accordingly.

`yroko_driver.py` contains yroko instantiation of qCode `Instrument` abstract class. `Instrument` class initializes TCP connection and contains reference to submodules `InstrumentChannel` which represent each of the 4 DAC boards in a yroko box. This class wraps getters/setters in a dynamic `Parameter` attribute bound to functions, which get/set by constructing strings sent over the TCP to the raspberry pi.

### Setup
![image](https://user-images.githubusercontent.com/47376937/210861028-2fa0e0fd-e9b7-4eba-9c59-a9b2903891a5.png)

```python
 def _configure_control(self, channel: int):
        """The DAC is removed from tristate by clearing the DACTRI bit,
        set BIN/2sC to 1 to treat D as nonsigned binary number (default is 2s complement),
        and the output clamp is removed by clearing the OPGND bit.
        """

        # logging.debug(f"read channel {channel} control register before doing update")
        # self._read_control(channel)

        # set binary encoding
        configuration_string = [0x20, 0x00, 0x16]
        self._write_inputShiftRegister(channel, configuration_string)

        # make sure DAC starts at 0
        self.set_voltage(channel, 0)

        # remove clamp
        configuration_string = [0x20, 0x00, 0x12]
        self._write_inputShiftRegister(channel, configuration_string)
```

### Synchronous DAC Update
In this mode, LDAC is held low while data is being clocked into the input shift register. The DAC output is updated on the rising edge of SYNC
- SDI, Data is clocked into the register on the falling edge of the serial clock input.
- CLK, Data can be transferred at rates of up to 35 MHz.
![yroko](https://github.com/PITT-HATLAB/instrument_drivers/assets/59108967/30a7d286-47e6-4313-bd1b-e9faa3dfc146)


### LCD Support
`yroko2_board_withlcd.py` now supports an LCD J204 display depicting the current output status of 
the yroko.

The PI must have the [RPLCD](https://rplcd.readthedocs.io/en/stable/) library and the i2c bus 
enabled. The `__init__`method initialises the LCD, where configuration of the address and the 
i2c_expander is required. the address can be found using `sudo i2cdetect -y 1` from the package 
`i2c-tools`.

![img_1.png](img_1.png)