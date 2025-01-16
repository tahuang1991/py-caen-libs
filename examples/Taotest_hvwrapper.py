#!/usr/bin/env python3
"""
Python demo for CAEN HV Wrapper


The demo aims to show the user how to work with the CAEN HW Wrapper library in Python.
"""

__author__ = 'Giovanni Cerretani'
__copyright__ = 'Copyright (C) 2024 CAEN SpA'
__license__ = 'MIT-0'
# SPDX-License-Identifier: MIT-0
__contact__ = 'https://www.caen.it/'

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

from caen_libs import caenhvwrapper as hv

# Parse arguments
parser = ArgumentParser(
    description=__doc__,
    formatter_class=ArgumentDefaultsHelpFormatter,
)

import time


def printChStatus(device, slot, ch):
    """print out Vmon/Imon/Status/Pw/Temp"""
    values = []
    param_list = ['VMon','IMon','Status','Pw','Temp']
    for param_name in param_list:
        param_prop = device.get_ch_param_prop(slot, ch, param_name)
        if param_prop.mode is not hv.ParamMode.WRONLY:
            values.append(device.get_ch_param(slot, [ch], param_name))
    out = "Status of slot %d Ch %d: "%(slot, ch)
    for index, param_name in enumerate(param_list):
        if param_name == 'Pw':
            out = out + " Pw = %d; "%values[index][0]
        else:
            out = out + "%s = %.1f; "%(param_name, values[index][0])
    print(out)
    return 0

# Shared parser for subcommands
parser.add_argument('-s', '--systemtype', type=str, help='system type', required=True, choices=tuple(i.name for i in hv.SystemType))
parser.add_argument('-l', '--linktype', type=str, help='system type', required=True, choices=tuple(i.name for i in hv.LinkType))
parser.add_argument('-a', '--arg', type=str, help='connection argument (depending on systemtype and linktype)', required=True)
parser.add_argument('-u', '--username', type=str, help='username', default='admin')
parser.add_argument('-p', '--password', type=str, help='password', default='rice2024')

args = parser.parse_args()

print('------------------------------------------------------------------------------------')
print(f'CAEN HV Wrapper binding loaded (lib version {hv.lib.sw_release()})')
print('------------------------------------------------------------------------------------')

with hv.Device.open(hv.SystemType[args.systemtype], hv.LinkType[args.linktype], args.arg, args.username, args.password) as device:

    slots = device.get_crate_map()  # initialize internal stuff

    comm_list = device.get_exec_comm_list()
    print('EXEC_COMM_LIST', comm_list)

    sys_props = device.get_sys_prop_list()
    for prop_name in sys_props:
        prop_info = device.get_sys_prop_info(prop_name)
        print('SYSPROP', prop_name, prop_info.type.name)
        if prop_info.mode is not hv.SysPropMode.WRONLY:
            prop_value = device.get_sys_prop(prop_name)
            print('VALUE', prop_value)
            device.subscribe_system_params([prop_name])

    for slot, board in enumerate(slots):
        if board is None:
            continue
        bd_params = device.get_bd_param_info(slot)
        for param_name in bd_params:
            param_prop = device.get_bd_param_prop(slot, param_name)
            print('BD_PARAM', slot, param_name, param_prop.type.name)
            if param_prop.mode is not hv.ParamMode.WRONLY:
                param_value = device.get_bd_param([slot], param_name)
                print('VALUE', param_value)
                device.subscribe_board_params(slot, [param_name])
        for ch in range(board.n_channel):
            ch_params = device.get_ch_param_info(slot, ch)
            #print("all ch params ", ch_params)
            for param_name in ch_params:
                #print("param_name ", param_name, " type ", type(param_name))
                param_prop = device.get_ch_param_prop(slot, ch, param_name)
                print('CH_PARAM', slot, ch, param_name, param_prop.type.name)
                if param_prop.mode is not hv.ParamMode.WRONLY:
                    param_value = device.get_ch_param(slot, [ch], param_name)
                    print('VALUE', param_value)
                    device.subscribe_channel_params(slot, ch, [param_name])

    #printChStatus(device, 5, 6)
    #device.set_ch_param(5, [6], 'V0Set', 25.0)
    #device.set_ch_param(5, [6], 'Pw', True)
    #time.sleep(10.0) ### wait for 10 seconds 
    #printChStatus(device, 5, 6)
    #time.sleep(10.0) ### wait for 10 seconds 
    #printChStatus(device, 5, 6)
    #time.sleep(60.0) ### wait for 10 seconds 
    #device.set_ch_param(5, [6], 'Pw', False)
    #time.sleep(10.0) ### wait for 10 seconds 
    #printChStatus(device, 5, 6)
    #time.sleep(10.0) ### wait for 10 seconds 
    #printChStatus(device, 5, 6)

    ## set voltage=25V for board in slot 5, ch 6, and print Vmon/Imon/Status/Pw/Temp
    # Listen for events
    #for _ in range(10):
    #    evt_list, _ = device.get_event_data()
    #    for evt in evt_list:
    #        print(evt)
