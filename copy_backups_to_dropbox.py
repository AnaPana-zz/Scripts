#! /usr/bin/python
import os
import dropbox

BACKUP_PATH = '/home/user/itblog-backups'
DROPBOX_PATH = '/'

client = dropbox.client.DropboxClient('token_here')

all_backups = set([b for b in os.listdir(BACKUP_PATH) if b[0].isdigit()])
uploaded_backups = set([c['path'].replace(DROPBOX_PATH, '') for c in client.metadata('/')['contents']])
backups_for_uploading = set(all_backups).difference(uploaded_backups)

if backups_for_uploading:
    print "Uploading %s files..." % len(backups_for_uploading)

    for backup in backups_for_uploading:
        f = open(os.path.join(BACKUP_PATH, backup), 'rb')
        response = client.put_file(os.path.join(DROPBOX_PATH,  backup), f)
        print 'Sucsessfuly uploaded: %s' % response['path']

else:
    print "Nothing to upload. Exiting."
