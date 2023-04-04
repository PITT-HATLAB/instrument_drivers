# -*- coding: utf-8 -*-
"""
Created on Tue Dec  8 16:31:55 2020

@author: Ryan Kaufman

purpose: add additional functionality to PNA driver without adding bulk to base driver
"""
from instrument_drivers.base_drivers.Keysight_P9374A import Keysight_P9374A
import numpy as np
import time
from plottr.data import datadict_storage as dds, datadict as dd
from data_processing.fitting.QFit import fit, plotRes, getData_from_datadict, reflectionFunc, rounder
import inspect

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
        
    def average(self, number, avg_over_freq = False): 
        #setting averaging timeout, it takes 52.02s for 100 traces to average with 1601 points and 2kHz IFBW
        '''
        Sets the number of averages taken, waits until the averaging is done, then gets the trace
        '''
        assert number > 0
        prev_trform = self.trform()
        self.trform('POL')
        time.sleep(self.del_time)
        self.average_type("POIN")
        time.sleep(self.del_time)
        self.trigger_source("MAN")
        time.sleep(self.del_time)
        total_time = self.sweep_time()*number+10
        #200ms window, if you need data faster talk to YR
        time.sleep(self.del_time)
        self.avgnum(number)
        time.sleep(self.del_time)
        self.timeout(total_time)
        time.sleep(self.del_time)
        print(f"Waiting {np.round(total_time, 1)}s for {number} averages...")
        self.last_msmt_msg = self.ask('ABORT; INITIATE:IMMEDIATE; *OPC?')
        time.sleep(self.del_time)
        if not avg_over_freq: 
            return self.gettrace()
        else: 
            return np.average(self.gettrace(), axis = 1).reshape((2,1))
    
    def savetrace(self, avgnum = 10, savedir, name): 
        # if savedir == None:
        #     savedir = easygui.diropenbox("Choose file location: ")
        #     assert savedir != None
        # if name == None: 
        #     name = easygui.enterbox("Enter Trace Name: ")
        #     assert name != None
            
        if savedir == "previous": 
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
            self.filepath = writer.file_path

        self.trform(prev_trform)
        self.previous_save = savedir
        self.set_to_manual()
        
        return self.filepath
    
    def fit_mode_onscreen(self, avgnum = 10, savedir = None, name = None, QextGuess = 200, QintGuess = 2000, ltrim = 0, rtrim = 1, magBackGuess = 0.01):
        
        filepath = self.savetrace(avgnum = avgnum, savedir = savedir, name = name)

        (freq, real, imag, mag, phase) = getData_from_datadict(filepath, plot_data=0)
        freq = freq[ltrim:-rtrim]
        real = real[ltrim:-rtrim]
        imag = imag[ltrim:-rtrim]
        mag = mag[ltrim:-rtrim]
        phase = phase[ltrim:-rtrim]
        
        popt, pcov = fit(freq, real, imag, mag, phase, Qguess=(QextGuess, QintGuess), magBackGuess=magBackGuess, phaseGuess = 0)  #(ext, int)   
    
        print(f'f (Hz): {rounder(popt[2]/2/np.pi)}', )
        fitting_params = list(inspect.signature(reflectionFunc).parameters.keys())[1:]
        for i in range(2):
            print(f'{fitting_params[i]}: {rounder(popt[i])} +- {rounder(np.sqrt(pcov[i, i]))}')
        Qtot = popt[0] * popt[1] / (popt[0] + popt[1])
        print('Q_tot: ', rounder(Qtot), '\nT1 (s):', rounder(Qtot/popt[2]), f"Kappa: {rounder(popt[2]/2/np.pi/Qtot)}", )
        plotRes(freq, real, imag, mag, phase, popt)
        
        
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
        self.trigger_source('IMM')
        self.average_type('SWE')
        
        
    def renormalize(self, num_avgs, pwr_bump = 0): 
        self.power(self.power()+pwr_bump)
        self.average(num_avgs)
        self.data_to_mem()
        self.math('DIV')
        self.electrical_delay(0)
        self.power(self.power()-pwr_bump)
        self.set_to_manual()
        
    def scattering_mtx_pair(self, datadir, fcenter1, fcenter2, fspan, SWT_info, avgnum = 5, MX = ''): 
        [SWT, name1in, name2in, name1out, name2out] = SWT_info
        
        #S11
        SWT.set_mode_dict(name1in)
        SWT.set_mode_dict(name1out)
        self.fcenter(fcenter1)
        self.fspan(fspan)
        
        self.savetrace(savedir = datadir, name = 'S11', avgnum = avgnum)
        
        #S22
        SWT.set_mode_dict(name2in)
        SWT.set_mode_dict(name2out)
        self.fcenter(fcenter2)
        self.fspan(fspan)
        
        self.savetrace(savedir = datadir, name = 'S22', avgnum = avgnum)
        
        #S12
        SWT.set_mode_dict(name2in)
        SWT.set_mode_dict(name1out+MX)
        #needs a mixer set to the gain frequency
        self.fcenter(fcenter2)
        self.fspan(fspan)
        
        self.savetrace(savedir = datadir, name = 'S12', avgnum = avgnum)
        
        #S21
        SWT.set_mode_dict(name1in)
        SWT.set_mode_dict(name2out+MX)
        #needs a mixer set to the gain frequency
        self.fcenter(fcenter1)
        self.fspan(fspan)
        
        self.savetrace(savedir = datadir, name = 'S21', avgnum = avgnum)
    def print_setup(self): 
        return self.fstart(), self.fstop()
    
    def fit_gain(self, gen, avgnum = 10,plot = False): 
        from scipy.optimize import curve_fit
        gen.output_status(0)
        self.power(self.power()+10)
        self.renormalize(avgnum*2)
        self.power(self.power()-10)
        gen.output_status(1)
        gain_func = lambda x, G, f, bw: G/(1+((x-f)/bw)**2)
        [mag, phase] = self.average(avgnum)
        freqs = self.getSweepData()
        popt, pcov = curve_fit(gain_func, freqs, 10**(mag/10), p0 = [100, np.average(freqs), np.average(freqs)/10])
        G, f, bw = popt
        if plot: 
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ax.plot((freqs-f)/1e6, mag, label = 'data')
            ax.plot((freqs-f)/1e6, 10*np.log10(gain_func(freqs, *popt)), label = 'Lorentzian Fit')
            ax.set_xlabel("Frequency Detuning (MHz)")
            ax.set_ylabel("Gain (dB)")
            ax.legend()
            ax.grid(b = 1)
        self.set_to_manual()
        return 10*np.log10(G), f/1e9, np.abs(2*bw/1e6), popt, gain_func
    
    def scan(self, start, stop, step, ifbw = 3000, avgnum = 1, savedir = None, name = None): 
        
        if savedir == None:
            savedir = easygui.diropenbox("Choose file location: ")
            assert savedir != None
        if name == None: 
            name = easygui.enterbox("Enter Trace Name: ")
            assert name != None
            
        elif savedir == "previous": 
            savedir = self.previous_save
            assert savedir != None
        
        freqs_arr = []
        mag_arr = []
        phase_arr = []
        center_points = np.arange(start, stop, step)
        
        for center in center_points: 
            self.fcenter(center)
            freqs = self.getSweepData()
            mag, phase = self.average(avgnum)
            np.append(freqs_arr, freqs)
            np.append(mag_arr, mag)
            np.append(phase_arr, phase)
        
        data = dd.DataDict(
            frequency = dict(unit='Hz'),
            power = dict(axes=['frequency'], unit = 'dB'), 
            phase = dict(axes=['frequency'], unit = 'Degrees'),
        )

        with dds.DDH5Writer(savedir, data, name=name) as writer:
            writer.add_data(
                    frequency = freqs_arr,
                    power = mag_arr,
                    phase = phase_arr
                )
            self.filepath = writer.file_path
        self.set_to_manual()
        
        return self.filepath