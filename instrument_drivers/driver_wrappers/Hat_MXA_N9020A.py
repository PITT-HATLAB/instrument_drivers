from instrument_drivers.base_drivers.Keysight_MXA_N9020A import Keysight_MXA_N9020A
import numpy as np
from plottr.data import datadict as dd
from plottr.data import datadict_storage as dds 

class Hat_MXA_N9020A(Keysight_MXA_N9020A):
    
    def __init__(self,name: str, address: str = None, **kwargs):
        if address == None:
            raise Exception('TCPIP Address needed')
        super().__init__(name, address, **kwargs)
        
    def print_important_info(self): 
        print(f"Span: {self.fspan()}")
        print(f"RBW: {self.RBW()}")
        print(f"VBW: {self.VBW()}")
        
    def plot_trace(self, avgnum = 1):
        import matplotlib.pyplot as plt
        SA_data = self.get_data(count = avgnum)
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Power(dBm)')
        ax.plot(SA_data[:,0]/1e9, SA_data[:,1])
        ax.grid()
        print(f"Max of trace: {np.max(SA_data[:, 1])}")
        self.print_important_info()
        return np.max(SA_data[:, 1])
    
    def savetrace(self, avgnum = 1, savedir = None, name = 'CXA_trace'): 
        if savedir == None:
            import easygui 
            savedir = easygui.diropenbox("Choose place to save trace information: ")
            assert savedir != None
        SA_data = self.get_data(count = avgnum)
        data = dd.DataDict(
            frequency = dict(unit='Hz'),
            power = dict(axes=['frequency'], unit = 'dBm'), 
        )
        with dds.DDH5Writer(savedir, data, name=name) as writer:
            writer.add_data(
                    frequency = SA_data[:,0],
                    power = SA_data[:,1]
                )
            
    def scattering_mtx_pair(self, datadir, fcenter1, fcenter2, fspan, SWT_info, avgnum = 500): 
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
        SWT.set_mode_dict(name1out+'_MX')
        #needs a mixer set to the gain frequency
        self.fcenter(fcenter2)
        self.fspan(fspan)
        
        self.savetrace(savedir = datadir, name = 'S12', avgnum = avgnum)
        
        #S21
        SWT.set_mode_dict(name1in)
        SWT.set_mode_dict(name2out+'_MX')
        #needs a mixer set to the gain frequency
        self.fcenter(fcenter1)
        self.fspan(fspan)
        
        self.savetrace(savedir = datadir, name = 'S21', avgnum = avgnum)
    def mirror(self, VNA): 
        self.fstart(VNA.fstart())
        self.fstop(VNA.fstop())
        