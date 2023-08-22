import argparse
import redivis
import simplejson as json
import os
import sys

from datetime import datetime, timedelta

DATASET = "neurotechxcolumbia dataset"
INFO_TABLE = f"matheu_campbell.neurotechxcolumbia_dataset.info_table:rx53"
DATA_TABLE = "data_table"
HPARAMS = ("SampleRate", "HeadsetConfiguration", "HeadsetModel", "BufferSize")
SPARAMS = ("ProjectName", "SubjectName", "ResponseType", "StimulusType",
           "BlockLength", "BlockCount", "StimCycle")


def listify(annotations):
    """Convert annotation json to list"""
    dct = json.loads(annotations)
    out = []
    for key, val in dct.items():
        out.append((key, val))
    return out


def reconstruct_info(row):
    out = {'HardwareParams': {}, 'SessionParams': {}}
    for key, val in row.items():
        if key == 'Annotations':
            out[key] = listify(val)
        elif key in HPARAMS:
            out['HardwareParams'][key] = val
        elif key in SPARAMS:
            out['SessionParams'][key] = val
        elif key[0] == ("_"):
            continue
        else:
            out[key] = val
    return out


def gen_exp(parsed):
    def fieldmatch(field, val):
        return f"{field.title().replace('_', '')} = \"{val}\""

    query = f"""SELECT * from `{INFO_TABLE}`\nWHERE """
    query += " AND ".join([fieldmatch(f, v) for f, v in vars(parsed).items() if v and f != "after_date" and f != "before_date"])
    return query


def query_criteria(parsed):
    ret = f"Project: {parsed.project_name}\n" if parsed.project_name else ""
    ret += f"Subject: {parsed.subject_name}\n" if parsed.subject_name else ""
    ret += f"Response Type: {parsed.response_type}\n" if parsed.response_type else ""
    ret += f"Stimulus Type: {parsed.stimulus_type}\n" if parsed.stimulus_type else ""
    ret += f"Headset Configuration: {parsed.headset_configuration}\n" if parsed.headset_configuration else ""
    ret += f"Headset Model: {parsed.headset_model}\n" if parsed.headset_model else ""
    ret += f"Collected before: {parsed.before_date}\n" if parsed.before_date else ""
    ret += f"Collected after: {parsed.after_date}\n" if parsed.after_date else ""
    return ret


parser = argparse.ArgumentParser(
    prog='retrieve.py',
    description='Queries revidis for relevant data sessions and downloads folder' +
                ' of results.',
    formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('-p', '--project-name', help="Project name")
parser.add_argument('-n', '--subject-name', help="The name of a particular data collection subject")
parser.add_argument('-r', '--response-type', help="EEG Response Type (SSVEP|ERP|other)")
parser.add_argument('-s', '--stimulus-type', help="Stimulus type (visual|audio|other)")
parser.add_argument('-c', '--headset-configuration', help="Headset configuration (standard|occipital|other)")
parser.add_argument('-m', '--headset-model', help="Headset model (CytonDaisy|Cyton)")
parser.add_argument('-b', '--before-date', help="include data collected before this date (MM-DD-YYYY) (inclusive); defaults to now")
parser.add_argument('-a', '--after-date', help="include data collected after this date (MM-DD-YYYY) (inclusive); defaults to 10 years ago")

args = parser.parse_args()
qstring = query_criteria(args)
if not qstring and input("No search criteria provided. Download all available data? (y/N) ") != "y":
    print("Exiting")
    sys.exit()

print("Searching for sessions by the following criteria: \n" + qstring)

# Query for sessions
qexp = gen_exp(args)
query = redivis.query(qexp)

rows = query.list_rows()

if args.before_date or args.after_date:
    try:
        bdate = datetime.strptime(args.before_date, "%m-%d-%Y") if args.before_date else datetime.now() - timedelta(days=3650)
        adate = datetime.strptime(args.after_date, "%m-%d-%Y") if args.after_date else datetime.now()
    except ValueError:
        print("Error: Incorrect date format; should be MM-DD-YYYY")

    to_remove = []
    for row in rows:
        rdate = datetime.strptime(row.Date, "%Y-%m-%d")
        if not adate <= rdate <= bdate:
            to_remove.append(row)
    for r in to_remove:
        rows.remove(r)

count = len(rows)
print(f"{count} session found." if count == 1 else
      f"{count} sessions found.\n")

if not count:
    print("Try again with different criteria.")
    sys.exit()

print("Project\t\tSubject\t\t\tLength\t\tDate")
print("------------------------------------------------------------------")
for session in rows:
    print(session.ProjectName + "\t\t" + session.SubjectName + "\t\t" + str(int(session.BlockLength)*int(session.BlockCount))+"s" + "\t\t" + session.Date)

if input("\nDownload all found sessions and their associated info JSON? (y/N) ") == "y":
    outpath = os.path.abspath("datapackage")
    os.makedirs(outpath, exist_ok=True)
    with open(os.path.join(outpath, "query.txt"), 'w+') as file:
        file.write("Query Criteria\n")
        file.write(qstring)

    for num, session in enumerate(rows):
        folder = os.path.join(outpath, session._UPLOAD_NAME)
        os.makedirs(folder, exist_ok=True, mode=0o700)
        with open(os.path.join(folder, "info.json"), 'w') as file:
            json.dump(reconstruct_info(session), file, indent=4, ensure_ascii=False)

        file = redivis.file(session.FileID)
        try:
            file.download(os.path.join(folder, "data.csv"))
        except Exception as E:
            print(f"Error: {E}")

        print(f"Created {folder}")
else:
    print("Exiting.")
    sys.exit()

print("Downloaded requested files.")
