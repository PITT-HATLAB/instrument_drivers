# -*- coding: utf-8 -*-
"""
Created on Tue Dec  8 16:31:55 2020

@author: Ryan Kaufman

purpose: add additional functionality to PNA driver without adding bulk to base driver
"""
from instrument_drivers.base_drivers.Keysight_P9374A import Keysight_P9374A
import numpy as np
import easygui
import time
from plottr.data import datadict_storage as dds, datadict as dd

class Hat_P9374A(Keysight_P9374A): 
    
    def __init__(self,name: str, address: str = None, **kwargs):
        if address == None:
            raise Exception('TCPIP Address needed')
        super().__init__(name, address, **kwargs)
        self.averaging(1)
        self.ifbw(3000)
        self.avgnum(15)
        self.power(-43)
    
    def average_restart(self):
        self.write('SENS1:AVER:CLE')
        
    def average(self, number): 
        #setting averaging timeout, it takes 52.02s for 100 traces to average with 1601 points and 2kHz IFBW
        '''
        Sets the number of averages taken, waits until the averaging is done, then gets the trace
        '''
        assert number > 0
        
        prev_trform = self.trform()
        self.trform('POL')
        total_time = self.sweep_time()*number+0.5
        self.avgnum(number)
        self.average_restart()
        print(f"Waiting {total_time}s for {number} averages...")
        time.sleep(total_time)
        return self.gettrace()
    
    def savetrace(self, avgnum = 3, savedir = None, name = None): 
        if savedir == None:
            savedir = easygui.diropenbox("Choose file location: ")
            assert savedir != None
        if name == None: 
            name = easygui.enterbox("Enter Trace Name: ")
            assert name != None
            
        elif savedir == "previous": 
            savedir = self.previous_save
            assert savedir != None
            
        data = dd.DataDict(
            frequency = dict(unit='Hz'),
            power = dict(axes=['frequency'], unit = 'dB'), 
            phase = dict(axes=['frequency'], unit = 'Degrees'),
        )

        prev_trform = self.trform()

        with dds.DDH5Writer(savedir, data, name=name) as writer:
            freqs = self.getSweepData() #1XN array, N in [1601,1000]
            vnadata = np.array(self.average(avgnum)) #2xN array, N in [1601, 1000]
            writer.add_data(
                    frequency = freqs,
                    power = vnadata[0],
                    phase = vnadata[1]
                )

        self.trform(prev_trform)
        self.previous_save = savedir
    
    # def fit_mode_onscreen(self, avgnum = 3, savedir = None, name = None, coupling = None):
        
    #     self.savetrace(avgnum = avgnum, savedir = savedir, name = name)
        
        
        
    #     if coupling.lower() == 'over': 
            
    #     elif coupling.lower() == 'under': 
        
    #     elif coupling.lower() == 'critical': 
        
    #     else: 
    #         raise Exception('Coupling unsupported, user \'over\', \'under\', or \'critical\' ')
    def save_important_info(self, savedir = None):
        if savedir == None:
            import easygui 
            savedir = easygui.filesavebox("Choose where to save VNA info: ", default = savedir)
            assert savedir != None
        file = open(savedir+'.txt', 'w')
        file.write(self.name+'\n')
        file.write("Power: "+str(self.power())+'\n')
        file.write("Frequency: "+str(self.fcenter())+'\n')
        file.write("Span: "+str(self.fspan())+'\n')
        file.write("EDel: "+str(self.electrical_delay())+'\n')
        file.write("Num_Pts: "+str(self.num_points())+'\n')
        print("Power: "+str(self.power())+'\n'+"Frequency: "+str(self.fcenter())+'\n'+"Span: "+str(self.fspan())+'\n'+"EDel: "+str(self.electrical_delay())+'\n'+"Num_Pts: "+str(self.num_points())+'\n')
        file.close()
        return savedir
    
    def trigger(self): 
        self.write(':TRIG:SING')
        return None
    def set_to_manual(self): 
        self.rfout(1)
        self.averaging(1)
        self.avgnum(3)
        self.trform('MLOG')
        self.trigger_source('INT')
        
    def renormalize(self, num_avgs): 
        self.averaging(1)
        self.avgnum(num_avgs)
        self.prev_elec_delay = self.electrical_delay()
        s_per_trace = self.sweep_time()
        wait_time = s_per_trace*num_avgs*1.3 + 2
        print(f'Renormalizing, waiting {wait_time} seconds for averaging...')
        time.sleep(wait_time)
        self.data_to_mem()
        self.math('DIV')
        self.electrical_delay(0)
        self.set_to_manual()
    
