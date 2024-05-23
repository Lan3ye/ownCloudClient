import requests
import requests.auth
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as BS
import pandas as pd

uname = "OC_User_1" 
passwd = 'S0vrpkQ/jItB}u1O6"@<Kh'

url = f"http://52.164.245.91/remote.php/dav/files/{uname}"

def getRemoteFiles(url, auth):
    tempDF = pd.DataFrame(columns=['File', 'LastMod', 'Type', 'Size', 'Quota', 'ETag'])
    headers = {'Depth': '1'} # Setting headers for the PROPFIND request
    try:
        answer = requests.request('PROPFIND', url, auth=auth, headers=headers)
        # print(response.status_code)
        if answer.status_code == 207:
            # print(answer.text)
            data = answer.text
            soup = BS(data, features="xml")
            # Getting all file events
            responses = soup.find_all('d:response')
            index = 0
            for response in responses:
                # print(type(response))
                file = response.find('href').text
                lastMod = response.find('getlastmodified').text
                # type is really strange cause it doesn't have any text, 
                # it just contains another tag. I'll have a look another time.
                size = response.find('quota-used-bytes').text
                quota = response.find('quota-available-bytes').text
                eTag = response.find('getetag').text
                # type = response.find('resourcetype').text
                tempDF.loc[index] = [file, lastMod, None, size, quota, eTag]
                index = index + 1
                # print(eTag)
            # print(tempDF)
            return tempDF
        else:
            print(f'Request failed with code {response.status_code}.')
            # print(response.text)
    except Exception as e:
        print(f'An error occured {e}')

auth = requests.auth.HTTPBasicAuth(uname, passwd)
# answerDF = authenticate(url, auth)
Files = getRemoteFiles(url, auth)

print(Files)
