from webdav3.client import Client
import time
import os

uname = "OC_User_1" 
passwd = 'S0vrpkQ/jItB}u1O6"@<Kh'
url = f"http://52.164.245.91/remote.php/dav/files/{uname}"

options = {
    'webdav_hostname': url,
    'webdav_login': uname,
    'webdav_password': passwd
}

client = Client(options)

remote_files = client.list()
print(remote_files)
# file_info = client.info(remote_files[0])


def get_remote_files(client):
    """Return a dictionary with remote file paths and their modification times."""
    remote_files = {}
    items = client.list()
    for item in items:
        if client.check(item):
            continue  # Skip directories
        info = client.info(item)
        mod_time = info.get('getlastmodified')
        mod_time = time.mktime(time.strptime(mod_time, '%a, %d %b %Y %H:%M:%S %Z'))
        relative_path = os.path.relpath(item)
        remote_files[relative_path] = mod_time
    return remote_files

print(get_remote_files(client))