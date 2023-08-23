# NeuroData
## Scripts for neural data collection, cloud storage, and retrieval
This repo contains documentation and utility scripts for data collection, cloud storage, and retrieval.

[Dataset Link](https://redivis.com/workspace/datasets/5e8n-ctqvm09q7)

### **Workflows**

### Data collection workflow:
1. Design your data collection session. Prepare a stimulus script, location, and time. You may need at two laptops (one for data collection and one to provide stimulus).
2. Define session info JSON via collection GUI. See ObjectInfo.md for more about info JSON files.
    - Session parameters: subject name, project name, response type, stimulus type, block length, block count, and stim cycle
    - Hardware parameters: sampling rate, buffer size, headset configuration, headset model
    - Description
    - Date
    - Time
3. Proceed to collection. When complete, there will be a session folder containing the newly generated .csv file, its accompanying info file, and session log file.
4. Supply session directory to upload script (upload_session.py) to store data on Columbia Data Platform.

### Data retrieval:
1. Decide which parameters are relevant.
1. Use retrieval script (retrieve.py) to query Columbia Data Platform (Redivis) for sessions with your desired criteria. Data will be downloaded into a datapackage folder with the following structure.

```
datapackage/
    ├─ query.txt
    ├─ session_08_11_10_62625/
    │  ├─ data_14_36.csv
    │  └─ info.json
    └─ session_09_10_11_10592/
       ├─ data_13_25.csv
       └─ info.json
```

### Database Features
1. Data retrieval by
    - project name
    - subject name
    - response type
    - stimulus type
    - headset configuration
    - headset model
    - collection date
    - any combination of the above

## Database Structure
### Session Table
Stores sessions in rows whose columns are object info fields, including one for FileID

### Data Table
Stores all sessions as files with file IDs that correspond to a row in session table.
