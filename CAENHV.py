#!/usr/bin/env python3
"""
Python script to call CAEN HV Wrapper and contorl CAEN HV modules
Check CAEN HV Wrapper Library for more info

Tao Huang, 2025 March
"""

from caen_libs import caenhvwrapper as hvwrapper

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

# Parse arguments
parser = ArgumentParser(
    description=__doc__,
    formatter_class=ArgumentDefaultsHelpFormatter,
)

import time
try:
    from tabulate import tabulate
    has_tabulate = True
except ModuleNotFoundError:
    print ("Package `tabulate` not found.")
    has_tabulate = False

from math import ceil

def auto_connect_disconnect(func):
    def wrapper(self, *args, **kwargs):
        try:
            self.reconnect()
        except RuntimeError as e:
            if "Already connected." in str(e):  # Check the specific error message
                #print("Connection already established. Skipping reconnection.")
                pass
            elif "CAENHV_InitSystem failed:" in str(e):
                raise("Failed to connect to the CAEN HV device. Please check the connection.")
            else:
                raise("Failed to connect to the CAEN HV device for unknow reason: ", str(e))  # Re-raise unexpected errors
        finally:
            result = func(self, *args, **kwargs)
            self.disconnect()
            
        return result
    return wrapper



class CAENHV():
    
    def __init__(self, systemtype='SY4527', linktype='TCPIP', param='192.168.0.1', usrname='admin', password='rice2024', verbose=False):
        self.systemtype = systemtype
        self.linktype = linktype 
        self.ip = param
        self.usrname = usrname
        self.password = password
        self.verbose = verbose
        self.device = None
        self.slots = []
        self.sys_props = []
        
        allSystemType = [i.name for i in hvwrapper.SystemType]
        allLinkType = [i.name for i in hvwrapper.LinkType]
        if systemtype not in allSystemType:
            raise KeyError(f"systemtype of CAENHV is not correct: {systemtype}; only available choices: ", allSystemType)

        if linktype not in allLinkType:
            raise KeyError(f"linktype of CAENHV is not correct: {linktype}; only available choices: ", allLinkType)
        try:
            self.device = hvwrapper.Device.open(hvwrapper.SystemType[self.systemtype], hvwrapper.LinkType[self.linktype], self.ip, usrname, password)
            self.slots = self.device.get_crate_map() # initialize internal stuff
            self.sys_props = self.device.get_sys_prop_list()
            print("Successfully initialized the CAEN HV Controller: ", self.device)
            if self.verbose:
                self.print_system_info()
        except hvwrapper.Error as e:
            # color helper removed — print plain message
            print("Failed to connect to the CAEN HV device. Please check the connection.")
            self.device = None
        
    
    def reconfig(self):
        self.device = hvwrapper.Device.open(hvwrapper.SystemType[self.systemtype], hvwrapper.LinkType[self.linktype], self.ip, self.usrname, self.password)
        self.slots = self.device.get_crate_map()
        
    def disconnect(self):
        try:
            self.device.close()
            if self.verbose:
                print("trying to temperarily disconnect HV system")
        except hvwrapper.Error as e:
            if "CAENHV_InitSystem failed:" in str(e):
                print("Failed to connect to the CAEN HV device. Please check the connection.")
            elif "NOTCONNECTED" in str(e) and "Connection failed " in str(e):
                if self.verbose:
                    print("system already disconnected")
                pass
        
    def reconnect(self):
        self.device.connect()
        self.slots = self.device.get_crate_map()
        if self.verbose:
            print("Successfully reconnected the CAEN HV Controller: ", self.device)
        
    #@auto_connect_disconnect
    def print_system_info(self):
        sys_params = self.device.get_sys_prop_list()
        table = []
        for param_name in sys_params:
            param_value = self.device.get_sys_prop(param_name)
            table.append([param_name, param_value])
        if has_tabulate:
            print(tabulate(table, headers=['param_name', 'param_value'], tablefmt="simple_outline"))
        else:
            print("System information: ", table)
        
    #@auto_connect_disconnect
    def print_board_info(self, slot, param_list=[]):
        bd_params = self.device.get_bd_param_info(slot)
        table = []
        if len(param_list) == 0:
            param_list = bd_params
        #headers = ["slot", "param_name", "value", "type", "mode"]
        
        for param_name in param_list:
            param_prop = self.device.get_bd_param_prop(slot, param_name)
            #print('BD_PARAM', slot, param_name, param_prop.type.name)
            if param_prop.mode is not hvwrapper.ParamMode.WRONLY:
                param_value = self.device.get_bd_param([slot], param_name)[0]
                table.append([slot, param_name, param_value, param_prop.type.name, param_prop.mode])      
        
        if has_tabulate:
            print(tabulate(table, headers=param_list, tablefmt="simple_outline"))
        else:
            print("Board information: ", '/'.join(map(str, param_list)), table)
        
    #@auto_connect_disconnect
    def print_crate_info(self, slotlist=[], chlist=[],  param_list=[]):
        
        #print("all slots ", list(enumerate(self.slots)))
        for slot, board in enumerate(self.slots):
            if board is None:
                continue
            if len(slotlist) > 0 and slot not in slotlist:
                continue 
            
            bd_params = self.device.get_bd_param_info(slot)
            #board_info_str = f"Board info in slot {slot}:"
            board_info_str = "Baord info in slot {}: ".format(slot)
            for param_name in bd_params:
                param_prop = self.device.get_bd_param_prop(slot, param_name)
                #print('BD_PARAM', slot, param_name, param_prop.type.name)
                if param_prop.mode is not hvwrapper.ParamMode.WRONLY:
                    param_value = self.device.get_bd_param([slot], param_name)[0]
                    board_info_str += " {}:{};".format(param_name, param_value)
                    #board_info_str += f" {param_name}:{param_value};"
                    #print('VALUE', param_value)
                    #device.subscribe_board_params(slot, [param_name])
            table = []
            headers = []
            for ch in range(board.n_channel):
                if len(chlist) > 0 and ch not in chlist:
                    continue
                ch_params = self.device.get_ch_param_info(slot, ch)
                if len(param_list) > 0:
                    ch_params = param_list
                headers = ['Ch', *ch_params]
                #print("all ch params ", ch_params)
                values = [ch]
                for param_name in ch_params:
                    #print("param_name ", param_name, " type ", type(param_name))
                    param_prop = self.device.get_ch_param_prop(slot, ch, param_name)
                    #print('CH_PARAM', slot, ch, param_name, param_prop.type.name)
                    if param_prop.mode is not hvwrapper.ParamMode.WRONLY:
                        param_value = self.device.get_ch_param(slot, [ch], param_name)[0]
                        values.append(param_value)
                        #print('VALUE', param_value)
                        #device.subscribe_channel_params(slot, ch, [param_name])
                table.append(values)
            print(board_info_str)
            if has_tabulate:
                print(tabulate(table, headers=headers, tablefmt="simple_outline"))
            else:
                print("Channel information: ", '/'.join(map(str, headers)), table)
            
        
    #@auto_connect_disconnect
    def print_channel_info(self, slot, ch, param_list=['V0Set', 'I0Set', 'VMon','IMon','Status','Pw','Temp']):
        ch_params = self.device.get_ch_param_info(slot, ch)
        if len(param_list) == 0: 
            param_list = ch_params
        table = []
        values = []
        for param_name in param_list:
            #print("param_name ", param_name, " type ", type(param_name))
            param_prop = self.device.get_ch_param_prop(slot, ch, param_name)
            #print('CH_PARAM', slot, ch, param_name, param_prop.type.name)
            if param_prop.mode is not hvwrapper.ParamMode.WRONLY:
                param_value = self.device.get_ch_param(slot, [ch], param_name)[0]
                values.append(param_value)
                #print('VALUE', param_value)
                #device.subscribe_channel_params(slot, ch, [param_name])
        table.append(values)
        if has_tabulate:
            print(tabulate(table, headers=param_list, tablefmt="simple_outline"))
        else:
            print("Channel information: ", '/'.join(map(str, param_list)), table)
            
        
    #@auto_connect_disconnect
    def read_channel_param(self, slot, ch, param):
        """
        parameters: more detail in CAEN UM2463 doc
         V0Set,   I0Set,  V1Set ,   I1Set ,  RUp ,   RDWn,   Trip,   SVMax,   VMon,   IMon,   Status 
         Temp,    Pw,   POn ,  PDwn ,  TripInt ,  TripExt ,  ImRange ,  ZCDetect ,  ZCAdjust ,  EnCtr
        VMon: voltage monitor, namely current value of HV
        IMon: current monitor
        Status: channel status
        """
        
        if param not in self.device.get_ch_param_info(slot, ch):
            raise KeyError(f"param for HVCANE is not in system parameter list: {param}; list: {self.sys_props}")
        param_prop = self.device.get_ch_param_prop(slot, ch, param)
        if param_prop.mode is not hvwrapper.ParamMode.WRONLY:
            return round(self.device.get_ch_param(slot, [ch], param)[0], 2)
        else:
            raise KeyError(f"mode of this parameter {param} in Slot {slot} Ch {ch} is wrong; Failed to set value in set_channel_param()")
        
    
    #@auto_connect_disconnect
    def set_channel_param(self, slot, ch, param, value):
        """
         V0Set ,  I0Set ,  V1Set ,  I1Set ,  RUp ,  RDWn ,  Trip ,  SVMax ,  VMon ,  IMon ,  Status ,  
         Temp ,  Pw ,  POn ,  PDwn ,  TripInt ,  TripExt ,  ImRange ,  ZCDetect ,  ZCAdjust ,  EnCtr
        V0Set: float, V0 voltage limit of channel, targeted HV value
        I0Set: float, current limit of channel
        V1Set/I1Set: float, second voltage/current limit
        RUp/RDwn: flaot, ramp-up/ramp-down rate, step size during ramp-up/ramp-down
        Trip: set trip time
        Pw: Power On/Off
        Pon: Power ON options
        PDwn: Power off options
        """
        if param not in self.device.get_ch_param_info(slot, ch):
            raise KeyError(f"param for HVCANE is not in system parameter list: {param}; list: {self.sys_props}")
        param_prop = self.device.get_ch_param_prop(slot, ch, param)
        if param_prop.mode is not hvwrapper.ParamMode.WRONLY:
            self.device.set_ch_param(slot, [ch], param, value)
        else:
            raise KeyError(f"mode of this parameter {param} in Slot {slot} Ch {ch} is wrong; Failed to set value in set_channel_param()")
    
    ####@auto_connect_disconnect
    def set_channel_HV(self, slot, ch, hv_value):
        status = self.read_channel_param(slot, ch, 'Status')
        if status == 255:
            print(f"Error: Channel {ch} in slot {slot} is not in operating status: {status}, only updating V0Set")
            self.set_channel_param(slot, ch, 'V0Set', hv_value)
            return
        current_hv = self.read_channel_param(slot, ch, 'VMon')
        ramp_up = self.read_channel_param(slot, ch, 'RUp')
        ramp_down = self.read_channel_param(slot, ch, 'RDWn')
        nsecond = 0.0
        division_factor = 1.0
        if hv_value > current_hv:
            nsecond = ceil((hv_value - current_hv) / (ramp_up * division_factor))
        else:
            nsecond = ceil((current_hv - hv_value) / (ramp_down * division_factor))
            
        self.set_channel_param(slot, ch, 'V0Set', hv_value) # set the value for channel
        if status & 0x1 == 0: ## channel is off
            self.set_channel_param(slot, ch, 'Pw', True) # enable the channel
        print(f"Setting and Enabling HV of slot{slot} ch{ch} to {hv_value} V.... waiting for {nsecond} seconds...")
        time.sleep(nsecond+2) ## wait for ~10 seconds
        #param_list = ['V0Set', 'I0Set', 'VMon','IMon','Status','Pw','Temp']
        if self.verbose:
            self.print_channel_info(slot, ch)
        #print(f"Status HV of slot{slot} ch{ch}: ", self.read_channel_param(slot, ch, 'VMon'))
    
    ####@auto_connect_disconnect
    def power_down_channel(self, slot, ch):
        self.set_channel_param(slot, ch, 'Pw', False)
        print(f"Power down channel {ch} in slot {slot}...")
        time.sleep(2)
        if self.verbose:
            self.print_channel_info(slot, ch)
    
    ###@auto_connect_disconnect
    def power_on_channel(self, slot, ch):   
        self.set_channel_param(slot, ch, 'Pw', True)
        print(f"Power on channel {ch} in slot {slot}...")
        time.sleep(2)
        if self.verbose:
            self.print_channel_info(slot, ch)

    def power_down_all_channels(self):
        for slot, board in enumerate(self.slots):
            if board is None:
                continue
            for ch in range(board.n_channel):
                status = self.read_channel_param(slot, ch, 'Status')
                if status & 0x1 == 1: ## channel is on
                    self.set_channel_param(slot, ch, 'Pw', False)
        time.sleep(2)
        if self.verbose:
            self.print_crate_info([], [], ['V0Set', 'I0Set', 'VMon','IMon','Status','Pw','Temp'])
    
    ####@auto_connect_disconnect
    def config_channel(self, slot, ch, V0Set, I0Set, V1Set=0, I1Set=1010, POn=False, PDwn=False, RampUp=20, RampDown=20, TripTime=10, SVMax=1000, ImRange=0, ZCDetect=True, ZCAdjust=False):
       
        self.set_channel_param(slot, ch, 'V0Set', V0Set) # set the V0 value for channel
        self.set_channel_param(slot, ch, 'I0Set', I0Set) # set the current limit for channel
        self.set_channel_param(slot, ch, 'V1Set', V1Set)
        self.set_channel_param(slot, ch, 'I1Set', I1Set)
        self.set_channel_param(slot, ch, 'POn', POn) # ramp up to previous value / off when create is power-on/restarted
        self.set_channel_param(slot, ch, 'PDwn', PDwn) # ramp down/kill when tripped 
        self.set_channel_param(slot, ch, 'RUp', RampUp)
        self.set_channel_param(slot, ch, 'RDWn', RampDown)
        self.set_channel_param(slot, ch, 'Trip', TripTime)
        self.set_channel_param(slot, ch, 'SVMax', SVMax)
        self.set_channel_param(slot, ch, 'ImRange', ImRange)
        self.set_channel_param(slot, ch, 'ZCDetect', ZCDetect)
        self.set_channel_param(slot, ch, 'ZCAdjust', ZCAdjust)
        print(f"Configured channel {ch} in slot {slot} with HV V0={V0Set} V and current I0={I0Set} uA")
        time.sleep(2)
        self.print_channel_info(slot, ch, [])
        
    
    

if __name__ == '__main__':
    # Shared parser for subcommands
    #parser.add_argument('-s', '--systemtype', type=str, help='system type', required=True, choices=tuple(i.name for i in hvwrapper.SystemType))
    #parser.add_argument('-l', '--linktype', type=str, help='system type', required=True, choices=tuple(i.name for i in hvwrapper.LinkType))
    #parser.add_argument('-a', '--arg', type=str, help='connection argument (depending on systemtype and linktype)', required=True)
    #parser.add_argument('-u', '--username', type=str, help='username', default='admin')
    #parser.add_argument('-p', '--password', type=str, help='password', default='rice2024')
    #args = parser.parse_args()
    
    print('------------------------------------------------------------------------------------')
    print(f'CAEN HV Wrapper binding loaded (lib version {hvwrapper.lib.sw_release()})')
    print('------------------------------------------------------------------------------------')
    
    
    hvcontroller = CAENHV()
    if hvcontroller.device is None:
        print("Failed to connect to the CAEN HV device. Please check the connection.")
        exit(1)
    hvcontroller.power_on_channel(4, 0)
    hvcontroller.print_crate_info([], [], ['V0Set', 'I0Set', 'VMon','IMon','Status','Pw','Temp'])
    hvcontroller.power_down_all_channels()
    #hvcontroller.disconnect()