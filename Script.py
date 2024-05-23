import requests
import requests.auth
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as BS

uname = "OC_User_1" 
passwd = 'S0vrpkQ/jItB}u1O6"@<Kh'

url = f"http://52.164.245.91/remote.php/dav/files/{uname}"

def authenticate(url, auth):
    headers = {'Depth': '1'} # Setting headers for the PROPFIND request
    try:
        response = requests.request('PROPFIND', url, auth=auth, headers=headers)
        # print(response.status_code)
        if response.status_code == 207:
            # print(response.text)
            data = response.text
            soup = BS(data, features="xml")
            hrefs = soup.find_all('d:href')
            for href in hrefs:
                print(href)
        else:
            print(f'Request failed with code {response.status_code}.')
            # print(response.text)
    except Exception as e:
        print(f'An error occured {e}')
        

auth = requests.auth.HTTPBasicAuth(uname, passwd)
authenticate(url, auth)
