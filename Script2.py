from webdav3.client import Client

uname = "OC_User_1" 
passwd = 'S0vrpkQ/jItB}u1O6"@<Kh'
url = f"http://52.164.245.91/remote.php/dav/files/{uname}"

options = {
    'webdav_hostname': url,
    'webdav_login': uname,
    'webdav_password': passwd
}

client = Client(options)

files = client.list()
print(files)