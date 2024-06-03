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
            lastMod = datetime.strptime(lastModStr, format_str)
            lastMod = lastMod.replace(tzinfo=pytz.UTC)

            # Checks whether entry is a Directory or a file
            if response.find('collection') != None:
                size = response.find('quota-used-bytes').text
                resType = 'Directory'
            else:
                size = response.find('getcontentlength').text
                resType = 'File'

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
            lastMod = datetime.fromtimestamp(os.path.getmtime(full_dir_path)).replace(tzinfo=clientTZ)
            resType = 'Directory'
            tempDF.loc[index] = [path, lastMod, resType, size]
            index += 1

        # Process files
        for filename in filenames:
            full_file_path = os.path.join(dirpath, filename)
            size = None
            path = full_file_path.replace("\\", "/")
            lastMod = datetime.fromtimestamp(os.path.getmtime(full_file_path)).replace(tzinfo=clientTZ)
            resType = 'File'
            tempDF.loc[index] = [path, lastMod, resType, size]
            index += 1
    print("Files and directories successfully processed.")
    return tempDF

def syncToCloud(remoteFiles=pd.DataFrame, localFiles=pd.DataFrame, auth=any, url=str):
    """Synchronizes WebDAV server with local files using pandas DataFrames.
    Uploads missing files to WebDAV server. Deletes files not found
    in local directory from server."""

    toUpload = pd.DataFrame(columns=['Path', 'LastMod', 'Type', 'Size'])
    toDelete = pd.DataFrame(columns=['Path', 'LastMod', 'Type', 'Size'])
    print(f'Syncing to WebDAV server {url}...')
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
            if timeDiff > timedelta(seconds=10):
                toUpload = pd.concat([toUpload, pd.DataFrame([row])], ignore_index=True)
                
        else:
            print(f"{path} not found on Server. (row {index})")
            toUpload = pd.concat([toUpload, pd.DataFrame([row])], ignore_index=True)

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
            with open(path, 'rb') as file:
                print(f"Uploading {path}")
                response = requests.put(url + "/" + path, data=file, auth=auth)
                if response.status_code == 201:
                    print(f"{path} uploaded successfully. (201)")
                elif response.status_code == 204:
                    print(f"{path} updated successfully. (204)")
                else: 
                    print(f"Failed to upload {path}. Status code: {response.status_code}")
    
    # Add delete algorithm
    for index, row in remoteFiles.iterrows():
        path = row['Path']
        if path not in localFiles['Path'].values and path != "":
            toDelete = pd.concat([toDelete, pd.DataFrame([row])], ignore_index=True)
    
    if not toDelete.empty:
        for index, row in toDelete.iterrows():
            path = row['Path']
            print(path)

def syncToDesktop(remoteFiles=pd.DataFrame, localFiles=pd.DataFrame, auth=any, url=str):
    """Synchronizes local files with WebDAV server using pandas DataFrames.
    Uploads missing files to device. Deletes files not found
    on server from local device."""
    # 1. Check whether files exist in both DFs
    print('syncToDesktop currently WIP.')

localFiles = getLocalFiles(localPath, clientTZ)
remoteFiles = getRemoteFiles(url, auth)

while True:
    lastRemoteChange = remoteFiles['LastMod'].max()
    lastLocalChange = localFiles['LastMod'].max()
    # lastLocalChange = int(localFiles['LastMod'].max().timestamp())

    # print(lastRemoteChange)
    # print(lastLocalChange)

    syncCheck = lastRemoteChange - lastLocalChange

    print(f"Time stamp difference: {syncCheck}")
    if syncCheck > timedelta(seconds=10):
        print("Local files out of date.")
        syncToDesktop(remoteFiles, localFiles, auth, url)
    elif syncCheck < timedelta(seconds=-10):
        print("Remote files out of date.")
        syncToCloud(remoteFiles, localFiles, auth, url)
    elif syncCheck < timedelta(seconds=10) and syncCheck > timedelta(seconds=-10):
        if remoteFiles != getRemoteFiles(url, auth):
            remoteFiles = getRemoteFiles(url, auth)
            syncToDesktop(remoteFiles, localFiles, auth, url)
        
        if localFiles != getLocalFiles(localPath, clientTZ):
            localFiles = getLocalFiles(localPath, clientTZ)
            syncToCloud(remoteFiles, localFiles, auth, url)
            remoteFiles = getRemoteFiles(url, auth)
    else:
        print("An error occured in determining syncCheck.")
    time.sleep(10)

print("Exiting.")
# syncToCloud(remoteFiles, localFiles, auth)
# for index, row in localFiles.iterrows():
#     print(f"Row {index}: {row.to_dict()}")

# for index, row in remoteFiles.iterrows():
#     print(f"Row {index}: {row.to_dict()}")

