# ----- Daten Synchronisation Lokal zwischen 2 Ordnern

from dirsync import sync
source_path = 'Ordner1'
target_path = 'Ordner2'

sync(source_path, target_path, 'sync') #for syncing one way
sync(target_path, source_path, 'sync') #for syncing the opposite way

##########################################################################################

# ---- webdav3 Bibliothek könnte so die Dateien auf dem Server synchronisieren, ob es klappt weiß ich nicht

import os
from webdav3.client import Client

# Konfigurieren Sie die ownCloud WEBDAV-Client-Optionen
optionen = {
 'webdav_hostname': "https://OWNCLOUD_SERVER/webdav",  # ownCloud Server-URL
 'webdav_login':    "BENUTZERNAME",  # Benutzername
 'webdav_password': "PASSWORT"  # Passwort
}

client = Client(optionen)

# Lokaler Ordner zur Synchronisation
lokaler_ordner = "/pfad/zum/lokalen/ordner"

# Durchlauf aller Dateien im lokalen Ordner
for dateiname in os.listdir(lokaler_ordner):
    lokaler_pfad = os.path.join(lokaler_ordner, dateiname)
    remote_pfad = f"/pfad/zum/remote/ordner/{dateiname}"  # Ordner Pfad auf dem Server

    # Hochladen der Datei auf den ownCloud-Server
    client.upload_sync(remote_path=remote_pfad, local_path=lokaler_pfad)
