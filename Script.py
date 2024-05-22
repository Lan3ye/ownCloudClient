import requests
import requests.auth
import xml.etree.ElementTree as ET

uname = "OC_User_1" 
passwd = 'S0vrpkQ/jItB}u1O6"@<Kh'

url = f"http://52.164.245.91/remote.php/dav/files/{uname}"

def authenticate(url, auth):
    headers = {'Depth': '1'} # Setting headers for the PROPFIND request
    response = requests.request('PROPFIND', url, auth=auth, headers=headers)
    print(response.status_code)
    
    if response.status_code == 207:
       print(response.text)
    # print(response.text)
    
    

auth = requests.auth.HTTPBasicAuth(uname, passwd)
print(authenticate(url, auth))
