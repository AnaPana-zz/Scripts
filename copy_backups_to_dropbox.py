#! /usr/bin/python
import os
import datetime
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys

import dropbox

from credentials import DROPBOX_KEY, MAIL_ADDRESS, MAIL_PASSWORD, MAIL_SERVER, MAIL_PORT


BACKUP_NAME = '_'.join([datetime.date.today().strftime("%d_%m_%Y"), os.environ['OPENSHIFT_GEAR_NAME']]) + '.sql'
BACKUP_PATH = os.path.join(os.environ['OPENSHIFT_REPO_DIR'], 'data')
DROPBOX_PATH = '/'


def create_backup():
    print "Running backup command."
    cmd = subprocess.Popen("mysqldump --password=%s -u %s -h %s -P %s %s > %s" % \
                               (
                                   os.environ['OPENSHIFT_MYSQL_DB_PASSWORD'],
                                   os.environ['OPENSHIFT_MYSQL_DB_USERNAME'],
                                   os.environ['OPENSHIFT_MYSQL_DB_HOST'],
                                   os.environ['OPENSHIFT_MYSQL_DB_PORT'],
                                   os.environ['OPENSHIFT_GEAR_NAME'],
                                   os.path.join(BACKUP_PATH, BACKUP_NAME),
                               ),
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    stdout, stderr = cmd.communicate()
    retcode = cmd.returncode
    if retcode:
        mail_subject = "[IT-BLOG BACKUP] Failed"
        mail_body = "Can't create backup %s. Got the following error %s." % (os.path.join(BACKUP_NAME, BACKUP_PATH),
                                                                             stderr)
        _send_mail_to_admin(mail_subject, mail_body)
        sys.exit(1)
    else:
        print "Backup was successfully created: %s." % (os.path.join(BACKUP_PATH, BACKUP_NAME))


def copy_to_dropbox():

    deleted_backups = []
    client = dropbox.client.DropboxClient(DROPBOX_KEY)

    all_backups = set([b for b in os.listdir(BACKUP_PATH) if b[0].isdigit()])
    uploaded_backups = set([c['path'].replace(DROPBOX_PATH, '') for c in client.metadata('/')['contents']])
    backups_for_uploading = set(all_backups).difference(uploaded_backups)

    today = datetime.datetime.now().date()

    if len(all_backups) >= 1: # remove backups only if at least one is present
        for c in client.metadata('/')['contents']:
            c_modified_date = datetime.datetime.strptime(c['modified'], "%a, %d %b %Y %H:%M:%S +%f").date()
            c_age = (today-c_modified_date).days
            if c_age > 7:
                client.file_delete(c['path'])
                deleted_backups.append(c['path'])

    if backups_for_uploading:
        print "Uploading %s files..." % len(backups_for_uploading)

        for backup in backups_for_uploading:
            f = open(os.path.join(BACKUP_PATH, backup), 'rb')
            response = client.put_file(os.path.join(DROPBOX_PATH,  backup), f)
            print 'Sucsessfuly uploaded: %s' % response['path']

    else:
        print "Nothing to upload. Exiting."

    mail_subject = "[IT-BLOG BACKUP] Successfully uploaded"
    mail_body = "Backups were uploaded: %s\nBackups were deleted: %s\n" % \
                (', '.join(backups_for_uploading), ', '.join(deleted_backups))
    _send_mail_to_admin(mail_subject, mail_body)


def _send_mail_to_admin(subject, body):
    admin_mail = MAIL_ADDRESS
    receiver_mail = 'back_admin@mail.ru'
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = admin_mail
    msg['To'] = receiver_mail
    message_body = MIMEText(body, 'plain')
    msg.attach(message_body)

    username = admin_mail
    password = MAIL_PASSWORD

    server = smtplib.SMTP('%s:%s' % (MAIL_SERVER, MAIL_PORT))
    server.starttls()
    server.login(username,password)
    server.sendmail(admin_mail, receiver_mail, msg.as_string())
    server.quit()

if __name__ == '__main__':
    create_backup()
    copy_to_dropbox()
