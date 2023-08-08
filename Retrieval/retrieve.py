import argparse
import boto3
import simplejson as json
import os

from boto3.dynamodb.types import TypeDeserializer

def generate_expressions(parsed):
    key_conditions = "#p = :pname and SessionID BETWEEN :min AND :max"
    filter_exp = ""
    exp_attrs = {":pname": {"S": parsed.project_name},
                 ":min":   {"N": "10000"},
                 ":max":   {"N": "99999"}}
    # #p included because db.query() does not accept empty dict, 
    # but exp_names is required if filtering by Time attribute
    exp_names = {"#p": "ProjectName"}
    if parsed.subject_name:
        filter_exp += f"SessionParams.SubjectName=:sname"
        exp_attrs[':sname'] = {"S": parsed.subject_name}
    if parsed.response_type:
        if len(filter_exp): filter_exp += " and "
        filter_exp += f"SessionParams.ResponseType=:rtype"
        exp_attrs[':rtype'] = {"S": parsed.response_type}
    if parsed.stimulus_type:
        if len(filter_exp): filter_exp += " and "
        filter_exp += f"SessionParams.StimulusType=:stype"
        exp_attrs[':stype'] = {"S": parsed.stimulus_type}
    if parsed.headset_configuration:
        if len(filter_exp): filter_exp += " and "
        filter_exp += f"HardwareParams.HeadsetConfiguration=:hconfig"
        exp_attrs[':hconfig'] = {"S": parsed.headset_configuration}
    if parsed.headset_model:
        if len(filter_exp): filter_exp += " and "
        filter_exp += f"HardwareParams.HeadsetModel=:hmodel"
        exp_attrs[':hmodel'] = {"S": parsed.headset_model}

    return (key_conditions, filter_exp, exp_attrs, exp_names)

def query_criteria(parsed):
    ret =  f"Project: {parsed.project_name}\n"
    ret += f"Subject: {parsed.subject_name}\n" if parsed.subject_name else ""
    ret += f"Response Type: {parsed.response_type}\n" if parsed.response_type else ""
    ret += f"Stimulus Type: {parsed.stimulus_type}\n" if parsed.stimulus_type else ""
    ret += f"Headset Configuation: {parsed.headset_configuration}\n" if parsed.headset_configuration else ""
    ret += f"Headset Model: {parsed.headset_model}\n" if parsed.headset_model else ""
    return ret
    
def deserialize(dct):
    tds = TypeDeserializer()
    return {
        key: tds.deserialize(val)
        for key, val in dct.items()
    }

parser = argparse.ArgumentParser(
    prog='DataRetriever',
    description='Queries DynamoDB and S3 for relevant data sessions and returns .zip' +
                ' of results.',
    formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('-p', '--project-name', help="Project name", required=True)
parser.add_argument('-n', '--subject-name', help="The name of a particular data collection subject")
parser.add_argument('-r', '--response-type', help="EEG Response Type (SSVEP|ERP|other)")
parser.add_argument('-s', '--stimulus-type', help="Stimulus type (visual|audio|other)")
parser.add_argument('-c', '--headset-configuration', help="Headset configuration (standard|occipital|other)")
parser.add_argument('-m', '--headset-model', help="Headset model (CytonDaisy|Cyton)")

# TODO Add support for a specific date, a date range, or date max/min

args = parser.parse_args()
qstring = query_criteria(args)
print("Searching for sessions by the following criteria: \n" + qstring)
table_name = 'neuro-projects'
bucket_name = 'neuro-session-bucket'
db = boto3.client('dynamodb')

exps = generate_expressions(args)
resp = db.query(TableName=table_name,
                KeyConditionExpression=exps[0],
                FilterExpression=exps[1],
                ExpressionAttributeValues=exps[2],
                ExpressionAttributeNames=exps[3])
count = int(resp['Count'])
print(f"{count} session found." if int(count) == 1 else
      f"{count} sessions found.")

items = resp['Items']
print("Session ID\tS3 Path")
for item in items:
    print(item['SessionID']['N'] + "\t\t" + item['S3Path']['S'])

outpath = "../datapackage"
os.makedirs(outpath, exist_ok=True)
if input("\nDownload all found sessions and their associated info JSON? (y/N) ") == "y":
    s3 = boto3.client('s3')
    with open(f"{outpath}/packageinfo.txt", 'w+') as file:
        file.write("Query Criteria\n")
        file.write(qstring)

    for session in items:
        dsed = deserialize(session)
        folder = outpath + f"/{dsed['SessionID']}"
        os.makedirs(folder, exist_ok=True)
        with open(f"{folder}/info.json", 'w') as file:
            json.dump(dsed, file, ensure_ascii=False, indent=4)
        
        fname = dsed['S3Path'].split('/')[-1]
        s3.download_file(bucket_name, fname, f"{folder}/{fname}")

print("Downloaded requested files.")
