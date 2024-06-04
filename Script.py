import requests
import requests.auth
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as BS
import pandas as pd
from datetime import datetime, timedelta
import os
import pytz
import tzlocal
import warnings
import time

warnings.filterwarnings("ignore", category=FutureWarning, message=".*DataFrame concatenation with empty or all-NA entries.*")

uname = "OC_User_1" 
passwd = 'S0vrpkQ/jItB}u1O6"@<Kh'
url = f"http://52.164.245.91/remote.php/dav/files/{uname}"
auth = requests.auth.HTTPBasicAuth(uname, passwd)
localPath = "testdir/"
clientTZ = tzlocal.get_localzone()
timeTol = 20 # Time tolerance in seconds

def getRemoteFiles(url, auth):
    """Sends PROPFIND request to WebDAV-Server to retrieve
    server directories and files. Returns pandas DataFrame.
    Structure: ['Path', 'LastMod', 'Type', 'Size']"""

    tempDF = pd.DataFrame(columns=['Path', 'LastMod', 'Type', 'Size'])
    headers = {'Depth': '50'} # Setting headers for the PROPFIND request
    answer = requests.request('PROPFIND', url, auth=auth, headers=headers)

    if answer.status_code == 207:
        print(f"Remote connection to {url} established. Getting files...")
        data = answer.text
        soup = BS(data, features="xml")
        # Getting all file events
        responses = soup.find_all('d:response')
        index = 0
        format_str = '%a, %d %b %Y %H:%M:%S %Z'
        
        # Looping through all returned files to retrieve relevant information
        for response in responses:
            path = response.find('href').text
            path = path.replace('/remote.php/dav/files/OC_User_1/', "")
            lastModStr = response.find('getlastmodified').text


            # Checks whether entry is a Directory or a file
            if response.find('collection') != None:
                size = response.find('quota-used-bytes').text
                resType = 'Directory'
                lastMod = None
            else:
                size = response.find('getcontentlength').text
                resType = 'File'
                lastModStr = response.find('getlastmodified').text
                lastMod = datetime.strptime(lastModStr, format_str)
                lastMod = lastMod.replace(tzinfo=pytz.UTC)

            # Adding file information to DataFrame 'tempDF'
            tempDF.loc[index] = [path, lastMod, resType, size]
            index = index + 1
        print("Remote files successfully processed.")
        return tempDF
    
    else:
        print(f'Request to {url} failed with code {response.status_code}.')

def getLocalFiles(localPath=str, clientTZ=any):
    """Uses os.walk to to gather information about files and subdirectories in 
    local directory. Returns pandas DataFrame. Structure: ['Path', 'LastMod', 'Type', 'Size']."""

    tempDF = pd.DataFrame(columns=['Path', 'LastMod', 'Type', 'Size'])
    index = 0

    print(f"Gathering files and directories from directory {localPath} ...")
    for dirpath, dirnames, filenames in os.walk(localPath):
        # Process directories
        for dirname in dirnames:
            full_dir_path = os.path.join(dirpath, dirname)
            size = None
            path = full_dir_path.replace("\\", "/")
            path = path + "/"
            path = path[len(localPath):]
            lastMod = None
            resType = 'Directory'
            tempDF.loc[index] = [path, lastMod, resType, size]
            index += 1

        # Process files
        for filename in filenames:
            full_file_path = os.path.join(dirpath, filename)
            size = None
            path = full_file_path.replace("\\", "/")
            path = path[len(localPath):]
            lastMod = datetime.fromtimestamp(os.path.getmtime(full_file_path)).replace(tzinfo=clientTZ)
            resType = 'File'
            tempDF.loc[index] = [path, lastMod, resType, size]
            index += 1
    print("Files and directories successfully processed.")
    return tempDF

def syncToCloud(remoteFiles=pd.DataFrame, localFiles=pd.DataFrame, localPath=str, auth=any, url=str):
    """Synchronizes WebDAV server with local files using pandas DataFrames.
    Uploads missing files to WebDAV server. Deletes files not found
    in local directory from server."""

    toUpload = pd.DataFrame(columns=['Path', 'LastMod', 'Type', 'Size'])
    toDelete = pd.DataFrame(columns=['Path', 'LastMod', 'Type', 'Size'])
    print(f'Syncing to WebDAV server {url}...')
    # Checking which files to upload
    for index, row in localFiles.iterrows():
        path = row['Path']

        if path in remoteFiles['Path'].values:
            localLastMod = row['LastMod']
            if isinstance(localLastMod, pd.Series):
                localLastMod = localLastMod.iloc[0]
            remoteLastMod = remoteFiles.loc[remoteFiles['Path'] == path, 'LastMod']
            if isinstance(remoteLastMod, pd.Series):
                remoteLastMod = remoteLastMod.iloc[0]
            timeDiff = localLastMod - remoteLastMod
            # Something's not quite working with the time diff
            if timeDiff > timedelta(seconds=timeTol):
                toUpload = pd.concat([toUpload, pd.DataFrame([row])], ignore_index=True)
                
        else:
            print(f"{path} not found on Server. (row {index})")
            toUpload = pd.concat([toUpload, pd.DataFrame([row])], ignore_index=True)

    # Sorting DataFrame to upload in correct order
    sortedIndex = toUpload['Path'].str.len().sort_values().index
    toUpload = toUpload.reindex(sortedIndex)

    # Creating directories on WebDAV-Server
    for index, row in toUpload[toUpload['Type'] == 'Directory'].iterrows():
        Directory =  url + "/" + row['Path'] + "/"
        print(f"Creating {row['Path']}")
        response = requests.request("MKCOL", Directory, auth=auth)
        if response.status_code == 201:
            print(f"{row['Path']} created successfully. (201)")
        elif response.status_code == 405:
            print(f"{row['Path']} already exists.") 
        else: 
            print(f"Failed to create {row['Path']}. Status code: {response.status_code}")

    # Uploading files to WebDAV-Server
    if not toUpload[toUpload['Type'] == 'File'].empty:
        for index, row in toUpload[toUpload['Type'] == 'File'].iterrows():
            path = row['Path']
            with open(localPath + path, 'rb') as file:
                print(f"Uploading {path}")
                response = requests.put(url + "/" + path, data=file, auth=auth)
                if response.status_code == 201:
                    print(f"{path} uploaded successfully. (201)")
                elif response.status_code == 204:
                    print(f"{path} updated successfully. (204)")
                else: 
                    print(f"Failed to upload {path}. Status code: {response.status_code}")
    
    # Finding files to delete
    for index, row in remoteFiles.iterrows():
        path = row['Path']
        if path not in localFiles['Path'].values and path != "":
            toDelete = pd.concat([toDelete, pd.DataFrame([row])], ignore_index=True)
    
    # Deleting files from server
    # 1. Files need to be deleted first to avoid orphans
    # 2. Files are to be deleted longest path first
    # 3. Directories are to be deleted longest path first
    if not toDelete.empty:
        sortedIndex = toDelete['Path'].str.len().sort_values(ascending=False).index
        toDelete = toDelete.reindex(sortedIndex)
        # print(filesToDelete['Path'])
        for index, row in toDelete.iterrows():
            path = row['Path']
            print(path)
            print(f"Deleting {path} from webserver.")
            response = requests.delete(url + "/" + path, auth=auth)
            if response.status_code == 204:
                print(f"{row['Type']} deleted successfully: {path}")
            else:
                print(f"Error deleting {row['Type']}: {path} - Status code: {response.status_code}")

def syncToDesktop(remoteFiles=pd.DataFrame, localFiles=pd.DataFrame, localPath=str, auth=any, url=str):
    """Synchronizes local files with WebDAV server using pandas DataFrames.
    Uploads missing files to device. Deletes files not found
    on server from local device."""
    # 1. Check whether files exist in both DFs
    toDownload = pd.DataFrame(columns=['Path', 'LastMod', 'Type', 'Size'])
    toDelete = pd.DataFrame(columns=['Path', 'LastMod', 'Type', 'Size'])
    print(f'Syncing from WebDAV server {url}...')
    for index, row in remoteFiles.iterrows():
        path = row['Path']
        
        if path in localFiles['Path'].values:
            if row['Type'] == 'File':
                remoteLastMod = row['LastMod']
                if isinstance(remoteLastMod, pd.Series):
                    remoteLastMod = remoteLastMod.iloc[0]
                localLastMod = localFiles.loc[localFiles['Path'] == path, 'LastMod']
                if isinstance(localLastMod, pd.Series):
                    localLastMod = localLastMod.iloc[0]
                timeDiff = remoteLastMod - localLastMod
                if timeDiff > timedelta(seconds=timeTol):
                    print()
                    toDownload = pd.concat([toDownload, pd.DataFrame([row])], ignore_index=True)

        else:
            print(f"{path} not found on device. (row {index})")
            toDownload = pd.concat([toDownload, pd.DataFrame([row])], ignore_index=True)

    # Sorting DataFrame to download in correct order
    sortedIndex = toDownload['Path'].str.len().sort_values().index
    toDownload = toDownload.reindex(sortedIndex)

    print(toDownload)
    # Creating directories on device
    for index, row in toDownload[toDownload['Type'] == 'Directory'].iterrows():
        Directory = localPath + row['Path']
        print(f"Creating directory {row['Path']}")
        try:
            os.mkdir(Directory)
        except FileExistsError:
            print(f"Directory {Directory} already exists.")

    # Downloading files
    for index, row in toDownload[toDownload['Type'] == 'File'].iterrows():
        path = row['Path']
        response = requests.get(url + "/" + path, auth=auth)
        content = response.content
        if response.status_code == 200:
            with open(localPath + path, "wb") as file:
                file.write(content)
            print(f"File {path} downloaded successfully.")
        else:
            print(f"Failed to downlaod file {path} - Status code: {response.status_code}")

    # Finding files to delete
    for index, row in localFiles.iterrows():
        path = row['Path']
        if path not in remoteFiles['Path'].values and path != "":
            toDelete = pd.concat([toDelete, pd.DataFrame([row])], ignore_index=True)

    # Deleting files from device
    if not toDelete.empty:
        sortedIndex = toDelete['Path'].str.len().sort_values(ascending=False).index
        toDelete = toDelete.reindex(sortedIndex)

        for index, row in toDelete.iterrows():
            path = row['Path']
            print(path)
            print(f"Deleting {path} from device.")
            if row['Type'] == "File":
                try:
                    os.remove(localPath + path)
                    print(f"Deleted file {path} successfully.")
                except FileNotFoundError:
                    print(f"File {path} not found.")
                except PermissionError:
                    print(f"Permission denied to delete file {path}")
            elif row['Type'] == "Directory":
                try:   
                    os.rmdir(localPath + path)
                    print(f"Deleted directory {path} successfully.")
                except FileNotFoundError:
                    print(f"Directory {path} not found.")
                except PermissionError:
                    print(f"Permission denied to delete directory {path}")
        
    print('Syncing to desktop completed.')

localFiles = getLocalFiles(localPath, clientTZ)
remoteFiles = getRemoteFiles(url, auth)

while True:
    lastRemoteChange = remoteFiles['LastMod'].max()
    print(f"Last remote change: {remoteFiles.loc[remoteFiles['LastMod'].idxmax()]}")
    # print("Last remote change:")
    # print(remoteFiles[remoteFiles['LastMod'] == remoteFiles['LastMod'].max()])
    lastLocalChange = localFiles['LastMod'].max()
    print(f"Last local change: {localFiles.loc[localFiles['LastMod'].idxmax()]}")
    # print("Last local change:")
    # print(localFiles[localFiles['LastMod'] == localFiles['LastMod'].max()])
    # # lastLocalChange = int(localFiles['LastMod'].max().timestamp())

    # print(lastRemoteChange)
    # print(lastLocalChange)

    syncCheck = lastRemoteChange - lastLocalChange

    print(f"Time stamp difference: {syncCheck}")
    # If the local files are more than 10 seconds older than the server files
    if syncCheck > timedelta(seconds=timeTol):
        print("Local files out of date.")
        syncToDesktop(remoteFiles, localFiles, localPath, auth, url)
        localFiles = getLocalFiles(localPath, clientTZ)
    # If the server files are more than 10 second older than the local files
    elif syncCheck < timedelta(seconds=-timeTol):
        print("Remote files out of date.")
        syncToCloud(remoteFiles, localFiles, localPath, auth, url)
        remoteFiles = getRemoteFiles(url, auth)
    # If the timestamps on server or client are within +-10 seconds of each other
    elif syncCheck < timedelta(seconds=timeTol) and syncCheck > timedelta(seconds=-timeTol):
        # If the remoteFiles had a change in the last 10 seconds
        if not remoteFiles.equals(getRemoteFiles(url, auth)):
            remoteFiles = getRemoteFiles(url, auth)
            syncToDesktop(remoteFiles, localFiles, localPath, auth, url)
            localFiles = getLocalFiles(localPath, clientTZ)
        
        # If the localFiles had a change in the last 10 seconds
        elif not localFiles.equals(getLocalFiles(localPath, clientTZ)):
            localFiles = getLocalFiles(localPath, clientTZ)
            syncToCloud(remoteFiles, localFiles, localPath, auth, url)
            remoteFiles = getRemoteFiles(url, auth)
        else:
            print("Files in sync.")
    else:
        print("An error occured in determining syncCheck.")
    print("----------------------------------------------------------------------------------")
    time.sleep(10)

print("Exiting.")
# syncToCloud(remoteFiles, localFiles, auth)
# for index, row in localFiles.iterrows():
#     print(f"Row {index}: {row.to_dict()}")

# for index, row in remoteFiles.iterrows():
#     print(f"Row {index}: {row.to_dict()}")

