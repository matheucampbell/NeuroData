import brainflow
from brainflow.board_shim import BoardShim, BrainFlowInputParams
from datetime import datetime
from time import ctime
from threading import Thread
from DataGUI import DataCollectionGUI, CollectionSession
from PyQt5.QtWidgets import QApplication

import json
import os
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
            "BufferSize": "100000"
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
        
        cached_info['Date'] = datetime.now().strftime("%m-%d-%y")
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
        with open(cache) as c:
            cached_info = json.loads(c.read())
    
    suffix = datetime.now().strftime("%m-%d-%y") + "_" + ctime()[-13:-8].replace(":", "")
    os.makedirs(os.path.join(os.getcwd(), f"session_{suffix}"), exist_ok=True, mode=0o777)
    shutil.copyfile(cache, os.path.join(os.getcwd(), os.path.join(f"session_{suffix}"), "info.json"))

    print("Board setup...")
    while (com := input("Which serial port is the board connected to? ")) == "":
        print("Invalid.")
    while (bid := input("Cyton (0) or CytonDaisy (2)? ")) not in ["0", "2"]:
        print("Invalid.")

    return (os.path.join(os.getcwd(), os.path.join(f"session_{suffix}")), com, int(bid),
            int(cached_info['HardwareParams']['BufferSize']))


def start_collection_gui(ipath, sflags, eflags):
    app = QApplication([])
    gui = DataCollectionGUI(ipath, sflags, eflags)
    app.exec_()


if __name__ == "__main__":
    sesdir, serial, bid, buffsize = prepare_session()
    infopath = os.path.join(sesdir, "info.json")
    with open(os.path.join(sesdir, "info.json"), 'r') as f:
        info = json.loads(f.read())

    params = BrainFlowInputParams()
    params.serial_port = serial  # check device manager on Windows

    try:
        board = BoardShim(bid, params)
    except brainflow.BrainFlowError as E:
        print(f"Error creating BoardShim object. Check serial port and board ID.\n{E}")
        sys.exit()

    session = CollectionSession(board, sesdir, buffsize)
    flag_list = session.get_flags()
    gui = Thread(target=start_collection_gui, args=(infopath, flag_list[0], flag_list[1]), name="GUI-Thread")
    session.start()
    gui.start()
