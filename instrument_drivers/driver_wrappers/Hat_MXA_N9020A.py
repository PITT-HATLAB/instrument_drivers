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
