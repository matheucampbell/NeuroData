''' Upload new data session to S3 and save associated info JSON on DynamoDB.
    -i --info-path: Path to a complete and properly formatted JSON object. All fields should be
                    filled out except S3Path and SessionID.
    -s --session-path: Path to .csv containing data session. '''

import argparse
import boto3
import simplejson as json
import os
import random
import sys

from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

TABLE = "neuro-projects"
PROJECT_ENTRY = ("ProjectList", 0)
SUBJECT_ENTRY = ("SubjectList", 1)

def verify_json(json: dict):
    valid = True
    req = ['SessionParams', 'HardwareParams', 'ProjectName', 'Description',
           'Annotations', 'Date', 'Time', 'S3Path', 'SessionID']

    for field in req:
        if field not in json:
            print(f"Info JSON missing field: '{field}'.")
            valid = False
            
    req2 = ['SubjectName', 'ResponseType', 'StimulusType',
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

def serialize(dct):
    tds = TypeSerializer()
    return {
        key: tds.serialize(val)
        for key, val in dct.items()
    }

def deserialize(dct):
    tds = TypeDeserializer()
    return {
        key: tds.deserialize(val)
        for key, val in dct.items()
    }

def dynamo_upload(db_client, s3_client, table, bucket, info, sesID, ses_path):
    info['SessionID'] = sesID
    info['S3Path'] = f"s3://{bucket}/{sesID}_{info['Date']}.csv"
    item_dict = serialize(info)

    try:
        resp = db_client.put_item(
            TableName=table,
            Item=item_dict,
            ConditionExpression='attribute_not_exists(SessionID)')

        s3_client.put_object(Bucket='neuro-session-bucket', Key=f"{sesID}_{info['Date']}.csv",
                             Body=ses_path)

        return resp

    except ClientError as E:  # Session with ID may already exist
        if E['Error']['Code'] =='ConditionalCheckFailedException':
            sesID = random.randint(10000, 99999)
            return dynamo_upload(db_client, s3_client, table, bucket, info, sesID, ses_path)
        return

def check_list(db_client, target_list, target):
    if target_list == "Projects":
        key = {"ProjectName": PROJECT_ENTRY[0], "SessionID": PROJECT_ENTRY[1]}
    elif target_list == "Subjects":
        key = {"ProjectName": SUBJECT_ENTRY[0], "SessionID": SUBJECT_ENTRY[1]}

    resp = db_client.get_item(TableName=TABLE, Key=serialize(key))
    entry = deserialize(resp['Item'])

    return target in entry[target_list]

def add_subject(db_path, name):
    with open(db_path, 'a') as file:
        file.write('\n' + name)
    return

def add_project(db_path, name):
    with open(db_path, 'a') as file:
        file.write('\n' + name)
    return


parser = argparse.ArgumentParser(prog='SessionUploader',
                                 description='Uploads data session to S3 and Dynamo')
parser.add_argument('-s', '--session-path', required=True)
parser.add_argument('-i', '--info-path', required=True)

args = parser.parse_args()

if os.path.splitext(args.session_path)[1] != '.csv':
    print("Error: Session path must be a CSV file.")
    sys.exit()

if os.path.splitext(args.info_path)[1] != '.json':
    print("Error: Info path must be a JSON file.")
    sys.exit()

if not os.path.exists(args.session_path):
    print(f"Error: Session path '{args.session_path}' invalid.")
    sys.exit()
    
if not os.path.exists(args.info_path):
    print(f"Error: Info path '{args.info_path}' invalid.")
    sys.exit()

with open(args.info_path) as fileinfo:
    info = json.loads(fileinfo.read())

# Confirm info JSON contains the right fields.
if not verify_json(info):
    sys.exit()

# Upload info JSON to DynamoDB
ID = random.randint(10000, 99999)
db = boto3.client('dynamodb')
s3 = boto3.client('s3')
bucket = "neuro-session-bucket"
table = "neuro-projects"

proj = info.get('ProjectName')
if not check_list(db, 'Projects', proj):
    if input(f"Subject \"{proj}\" not found. Add new project? (y/N) ") == "y":
        add_project(proj)

sub = info.get('SessionParams').get('SubjectName')
if not check_list(db, 'Subjects', sub):
    if input(f"Subject \"{sub}\" not found. Add new subject? (y/N) ") == "y":
        add_subject(sub)

resp = dynamo_upload(db, s3, table, bucket, info, ID, args.session_path)

if resp.get('ResponseMetadata').get('HTTPStatusCode') == 200:
    print(f"Info JSON uploaded to {table}.\n" + 
          f"Session CSV uploaded to {bucket}.")
else:
    print("An error occurred.")
    print(json.dumps(resp, ensure_ascii=True, indent=4))
