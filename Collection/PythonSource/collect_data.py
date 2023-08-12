import brainflow
from brainflow.board_shim import BoardShim, BrainFlowInputParams
from datetime import datetime
from time import sleep, ctime
from threading import Thread, Event
from DataGUI import DataCollectionGUI, CollectionSession
from PyQt5.QtWidgets import QApplication

import json
import os
# import numpy as np
# import pandas as pd
import shutil
import sys

"""
Records a data collection session as one .csv file with an accompanying 
(incomplete) JSON file. Upload script (upload_session.py) completes info 
JSON by generating a session ID and S3Path.

Session file structure
current_dir
    ├─ session_10-10-23/
    │   ├─ session.csv
    │   └─ info.json
    ├─ collect_data.py
    └─ .cached.json
"""


def create_empty_info():
    return {
        "SessionParams": {
            "SubjectName": "",
            "ResponseType": "",
            "StimulusType": "",
            "BlockLength": 0,
            "BlockCount": 0,
            "StimCycle": 0
        },
        "HardwareParams": {
            "SampleRate": 0,
            "HeadsetConfiguration": "",
            "HeadsetModel": "",
            "BufferSize": ""
        },
        "ProjectName": "",
        "Description": "",
        "Annotations": [],
        "Date": datetime.now().strftime("%m-%d-%y"),
        "Time": datetime.now().strftime("%H:%M"),
        "S3Path": None,
        "SessionID": None
        }


def insert_timestamps(info):
    bcount = int(info.get('SessionParams').get('BlockCount'))
    blength = int(info.get('SessionParams').get('BlockLength'))
    info['Annotations'] = [(float(blength*k), f"Block{k}") for k in range(1, bcount+1)]


def update_cache(new=False, cachepath=None):
    exclude = ("Annotations", "S3Path", "SessionID")
    if new:
        info = create_empty_info()
        cachepath = os.path.join(os.getcwd(), ".cache.json")
    else:
        with open(cachepath, 'r') as f:
            info = json.loads(f.read())
    
    for key, val in info.items():
        if type(info[key]) == dict:
            for k, v in info[key].items():
                if k not in exclude and (newval := input(f"{k} ({v}): ")) != "":
                    info[key][k] = newval
            continue
        if key not in exclude and (newval := input(f"{key} ({val}): ")) != "" and key not in exclude:
            info[key] = newval
    
    insert_timestamps(info)
    with open(cachepath, 'w') as file:
        json.dump(info, file, ensure_ascii=False, indent=4)
    

def prepare_session():
    cache = os.path.join(os.getcwd(), ".cache.json")
    if os.path.exists(cache):
        with open(cache) as c:
            cached_info = json.loads(c.read())
            cached_info['Annotations'] = []
        
        cached_info['Date'] = datetime.now().strftime("%d-%m-%y")
        print("Previous info JSON found.\n")
        print(json.dumps(cached_info, indent=4))
        
        while (r := input("\nUse (u), Edit (e), or Create new (c): ")) not in ['u', 'e', 'c']:
            print("Invalid input.")
        if r == 'e':
            update_cache(new=False, cachepath=cache)
        elif r == 'c':
            update_cache(new=True)
    else:
        print("No info JSON found. Creating a new one.\n")
        update_cache(new=True)
    
    # suffix = datetime.now().strftime("%d-%m-%y") + "_" + ctime()[-13:-8].replace(":", "")
    suffix = datetime.now().strftime("%d-%m-%y")
    os.makedirs(os.path.join(os.getcwd(), f"session_{suffix}"), exist_ok=True)
    shutil.copyfile(cache, os.path.join(os.getcwd(), os.path.join(f"session_{suffix}"), "info.json"))

    print("Board setup...")
    while (com := input("Which serial port is the board connected to? ")) == "":
        print("Invalid.")
    while (bid := input("Cyton (0) or CytonDaisy (2)? ")) not in ["0", "2"]:
        print("Invalid.")

    return os.path.join(os.getcwd(), os.path.join(f"session_{suffix}")), com, int(bid)


def start_collection_gui(ipath, sflags, eflags):
    app = QApplication([])
    gui = DataCollectionGUI(ipath, sflags, eflags)
    app.exec_()


if __name__ == "__main__":
    sesdir, serial, bid = prepare_session()
    infopath = os.path.join(sesdir, "info.json")
    with open(os.path.join(sesdir, "info.json"), 'r') as f:
        info = json.loads(f.read())

    # collect_thread = Thread(target=start_collection, args=(serial, bid))
    # gui_thread = Thread(target=start_collection_gui, args=(infopath,))
    params = BrainFlowInputParams()
    params.serial_port = serial  # check device manager on Windows
    try:
        board = BoardShim(bid, params)
    except brainflow.BrainFlowError as E:
        print(f"Error creating BoardShim object. Check serial port and board ID.\n{E}")
        sys.exit()

    session = CollectionSession(board, sesdir)
    flag_list = session.get_flags()
    gui = Thread(target=start_collection_gui, args=(infopath, flag_list[0], flag_list[1]))
    session.start()
    gui.start()

'''# BrainFlow Parameters
params = BrainFlowInputParams()
params.serial_port = "COM3"  # check device manager on Windows
board_id = 2  # 0 for cyton, 2 for Cyton/Daisy, there is also an option for synthetic data

board = BoardShim(board_id, params)
board.disable_board_logger()
data_rows = board.get_eeg_channels(board_id)

board.prepare_session()
while not board.is_prepared():
    sleep(.5)
board.start_stream(buffer_size)
sleep(2)  # wait for stream to stabilize

"""
Data Collection Architecture

Thread 1: Collect data at regular intervals much smaller than buffer
while (total_samples < goal):
    get_board_data()
    sleep(interval)
save_file()

Thread 2: Event-based GUI. Keep track of timing and mark manual annotations.
          Change color to indicate block state.

"""

board.stop_stream()
board.release_session()

print("\nData collection complete.")'''