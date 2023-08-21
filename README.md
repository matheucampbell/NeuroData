# NeuroData
## Scripts for neural data collection, cloud storage, and retrieval
This repo contains documentation and utility scripts for data collection, cloud storage, and retrieval.

### **Workflows**

### Data collection workflow:
1. Design your data collection session. Prepare a stimulus script and location. You may need at two laptops (one for data collection and one to provide stimulus).
2. Define session info JSON via collection script CLI. See ObjectInfo.md for more about info JSON files.
    - Session parameters: subject name, response type, stimulus type, block length, block count, and stim cycle
    - Hardware parameters: sampling rate, headset configuration, buffer size
    - Project name
    - Description
    - Date
    - Time
3. Proceed to collection. When complete, there will be a session folder containing the newly generated .csv file, its accompanying info file, and session log file.
4. Supply info json and session .csv to the upload script (upload_session.py) to store data on Columbia Data Platform.

### Data retrieval:
1. Use retrieval script (retrieve.py) to query Columbia Data Platform (Redivis). Data will be downloaded into a datapackage folder with the following structure.

```
datapackage/
    ├─ packageinfo.txt
    ├─ 24601/
    │  ├─ 24601_11-12-23.csv
    │  └─ info.json
    └─ 10025/
       ├─ 10024_11-13-25.csv
       └─ info.json
```

### **Functions**

### Database Functions:
1. Data retrieval by
    - project name
    - subject name
    - stimulus type
    - session date
    - response type
    - any combination of the above

### Storage Structure
## Session Table
Stores sessions in rows whose columns are object info fields, including one for FileID

## Data Table
Stores all sessions as files with file IDs that correspond to a row in session table.
