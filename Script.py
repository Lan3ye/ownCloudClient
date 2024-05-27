import requests
import requests.auth
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as BS
import pandas as pd
from datetime import datetime, timedelta
import os
import pytz
import tzlocal

uname = "OC_User_1" 
passwd = 'S0vrpkQ/jItB}u1O6"@<Kh'
url = f"http://52.164.245.91/remote.php/dav/files/{uname}"
localPath = "testdir/"
clientTZ = tzlocal.get_localzone()

def getRemoteFiles(url, auth):
    tempDF = pd.DataFrame(columns=['Path', 'LastMod', 'Type', 'Size']) #, 'Quota', 'ETag'])
    headers = {'Depth': '50'} # Setting headers for the PROPFIND request
    # try:
    answer = requests.request('PROPFIND', url, auth=auth, headers=headers)
    # print(answer.status_code)
    if answer.status_code == 207:
        # print(answer.text)
        data = answer.text
        soup = BS(data, features="xml")
        # Getting all file events
        responses = soup.find_all('d:response')
        index = 0
        format_str = '%a, %d %b %Y %H:%M:%S %Z'
        # print(responses)
        for response in responses:
            path = response.find('href').text
            path = path.replace('/remote.php/dav/files/OC_User_1', "")
            lastModStr = response.find('getlastmodified').text
            lastMod = datetime.strptime(lastModStr, format_str)
            lastMod = lastMod.replace(tzinfo=pytz.UTC)
            # eTag = response.find('getetag').text

            # Checks whether entry is a Directory or a file
            if response.find('collection') != None:
                size = response.find('quota-used-bytes').text
                # quota = response.find('quota-available-bytes').text
                resType = 'Directory'
                # print(resType)
            else:
                size = response.find('getcontentlength').text
                # quota = None
                resType = 'File'

            tempDF.loc[index] = [path, lastMod, resType, size] #, quota, eTag]
            index = index + 1

        # print(tempDF)
        return tempDF
    else:
        print(f'Request failed with code {response.status_code}.')
        # print(response.text)
    # except Exception as e:
        # print(f'An error occured {e}')

def getLocalFiles(localPath):
    tempDF = pd.DataFrame(columns=['Path', 'LastMod', 'Type', 'Size'])
    localFiles = os.listdir(localPath)
    index = 0
    for file in localFiles:
        fullPath = os.path.join(localPath, file)
        if os.path.isfile(fullPath):
            size = os.path.getsize(fullPath)
            path = fullPath
            lastMod = datetime.fromtimestamp(os.path.getmtime(fullPath))
            lastMod = lastMod.replace(tzinfo=clientTZ)
            resType = 'File'
            tempDF.loc[index] = [path, lastMod, resType, size]
            index = index + 1
        elif os.path.isdir(fullPath):
            size = os.path.getsize(fullPath)
            path = fullPath
            lastMod = datetime.fromtimestamp(os.path.getmtime(fullPath))
            lastMod = lastMod.replace(tzinfo=clientTZ)
            tempDF.loc[index] = [path, lastMod, resType, size]
            resType = 'Directory'
            index = index + 1
    
    return tempDF

def syncToCloud(remoteFiles, localFiles):
    print('syncToCloud')
def syncToDesktop(remoteFiles, localFiles):
    # 1. Check whether files exist in both DFs
    print('syncToDesktop')

auth = requests.auth.HTTPBasicAuth(uname, passwd)
remoteFiles = getRemoteFiles(url, auth)
localFiles = getLocalFiles(localPath)

lastRemoteChange = remoteFiles['LastMod'].max()
lastLocalChange = localFiles['LastMod'].max()
# lastLocalChange = int(localFiles['LastMod'].max().timestamp())

print(lastRemoteChange)
print(lastLocalChange)

syncCheck = lastRemoteChange - lastLocalChange


print(syncCheck)
if syncCheck > timedelta(seconds=10):
    syncToDesktop(remoteFiles, localFiles)
elif syncCheck < timedelta(seconds=-10):
    syncToCloud(remoteFiles, localFiles)

# # for index, row in remoteFiles.iterrows():
# #     print(f"Row {index}: {row.to_dict()}")


