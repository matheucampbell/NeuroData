''' Upload new data session and associated info.json to Redivis.
    -s --session-path: Path to directory containing a properly formatted info.json and data.csv files.. '''

import argparse
import simplejson as json
import os
import redivis
import sys
from uuid import uuid4

DATASET = "neurotechxcolumbia dataset"
INFO_TABLE = "info_table"
SESSION_TABLE = "session_table"
USER_NAME = "matheu_campbell"
HPARAMS = ("SampleRate", "HeadsetConfiguration", "HeadsetModel", "BufferSize")
SPARAMS = ("ProjectName", "SubjectName", "ResponseType", "StimulusType",
           "BlockLength", "BlockCount", "StimCycle")

def verify_json(json: dict):
    valid = True
    req = ['SessionParams', 'HardwareParams', 'Description',
           'Annotations', 'Date', 'Time', 'FileID']

    for field in req:
        if field not in json:
            print(f"Info JSON missing field: '{field}'.")
            valid = False
            
    req2 = ['SubjectName', 'ProjectName', 'ResponseType', 'StimulusType',
            'BlockLength', 'BlockCount', 'StimCycle']
    for field in req2:
        if field not in json.get('SessionParams'):
            print(f"SessionParams field missing subfield: '{field}'.")
            valid = False
        
    req3 = ['SampleRate', 'HeadsetConfiguration', 'HeadsetModel', 'BufferSize']
    for field in req3:
        if field not in json.get('HardwareParams'):
            print(f"HardwareParams field missing subfield: '{field}'.")
            valid = False

    return valid


def dictify(annotations):
    """Convert annotation list to json formatted string."""
    out = {}
    for a in annotations:
        out[str(a[0])] = a[1]
    
    return out

def listify(annotations):
    """Convert annotation json to list"""
    dct = json.loads(annotations)
    out = []
    for key, val in dct.items():
        out.append((key, val))
    return out

def flatten(dct):
    flat = {}
    for key, val in dct.items():
        if isinstance(val, dict):
            for k, v in flatten(val).items():
                flat[k] = v
        elif isinstance(val, list):
            flat[key] = str(dictify(val)).replace("'", '"')
        else:
            flat[key] = val
    return flat

def unflatten(dct):
    """Convert from Redivis format to normal."""
    out = {}
    out['HardwareParams'] = {}
    out['SessionParams'] = {}
    hparams = ("SampleRate", "HeadsetConfiguration", "HeadsetModel", "BufferSize")
    sparams = ("ProjectName", "SubjectName", "ResponseType", "StimulusType",
               "BlockLength", "BlockCount", "StimCycle")
    for key, val in dct.items():
        if key == 'Annotations':
            out[key] = listify(val)
        elif key in hparams:
            out['HardwareParams'][key] = val
        elif key in sparams:
            out['SessionParams'][key] = val
        else:
            out[key] = val
    return out


def info_upload(ds_name, table_name, username, infodct):
    dataset = redivis.user(username).dataset(ds_name)
    table = dataset.table(table_name)
    flat = [flatten(infodct)]
    upload = table.upload("info.json").create(str(flat), type="json")

    return upload


parser = argparse.ArgumentParser(prog='SessionUploader',
                                 description='Uploads data session to Redivis')
parser.add_argument('-s', '--session-path', required=True)

args = parser.parse_args()
args.session_path = os.path.abspath(args.session_path)
info_path = os.path.join(args.session_path, "info.json")
data_path = os.path.join(args.session_path, "data.csv")

if not os.path.isdir(args.session_path):
    print(f"Error: Session path '{args.session_path}' invalid.")
    sys.exit()

if not os.path.exists(info_path):
    print(f"Error: Info file not found in session directory.")
    sys.exit()

if not os.path.exists(data_path):
    print(f"Error: Data file not found in session directory.")
    sys.exit()

with open(info_path) as fileinfo:
    info = json.loads(fileinfo.read())

# Confirm info JSON contains the right fields.
if not verify_json(info):
    sys.exit()

# Upload info JSON to Redivis
fileID = str(uuid4())

resp = info_upload(DATASET, INFO_TABLE, USER_NAME, info)
print(resp)

# if resp.get('ResponseMetadata').get('HTTPStatusCode') == 200:
#     print(f"Info JSON uploaded to {INFO_TABLE}.\n" + 
#           f"Session CSV uploaded to {SESSION_TABLE}.")
# else:
#     print("An error occurred.")
#     print(json.dumps(resp, ensure_ascii=True, indent=4))
