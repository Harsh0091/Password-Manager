
import sqlite3
from cryptography.fernet import Fernet
import hashlib
import base64
import secrets
import string
from PyQt5.QtWidgets import QApplication, QMainWindow, QInputDialog, QLineEdit, QMessageBox, QPushButton
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
from google.auth.transport.requests import Request
import sys

class MainUI(QMainWindow):
    def __init__(self):
        super(MainUI, self).__init__()
        self.master_password = None
        self.password_manager = None
        self.get_master_password()
        if not self.master_password:
            QApplication.quit()
        loadUi("Password Manager\\gui.ui", self)

        # Connect buttons to methods
        self.pushButton.clicked.connect(self.store_password)
        self.pushButton_2.clicked.connect(self.retrieve_password)
        self.pushButton_3.clicked.connect(self.generate_password)
        self.pushButton_4.clicked.connect(self.list_services)
        self.pushButton_6.clicked.connect(self.delete_service)
        self.pushButton_5.clicked.connect(self.exit_application)
        self.pushButton_7.clicked.connect(self.upload_to_drive)  
        self.pushButton_8.clicked.connect(self.download_from_drive)

        self.password_manager = PasswordManager(self.master_password)

    def get_master_password(self):
        self.setWindowIcon(QIcon("Password Manager\\images\\main.png"))
        master_password, ok = QInputDialog.getText(self, 'Password Manager', 'Enter your Secret Key:', QLineEdit.Password)
        self.master_password = master_password if ok else None
        
    def display_message(self, message, password=None):
        msg_box = QMessageBox(self)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        if password:
            copy_button = QPushButton("Copy Password")
            msg_box.addButton(copy_button, QMessageBox.ActionRole)
            copy_button.clicked.connect(lambda: QApplication.clipboard().setText(password))

        msg_box.exec_()

    def store_password(self):
        service, ok = QInputDialog.getText(self, 'Enter Service', 'Enter the service:')
        if ok:
            password, ok = QInputDialog.getText(self, 'Enter Password', 'Enter the password:', QLineEdit.Password)
            if ok:
                self.password_manager.store_password(service, password)
                self.display_message("Password stored successfully!")

    def retrieve_password(self):
        service, ok = QInputDialog.getText(self, 'Enter Service', 'Enter the service to retrieve the password:')
        if ok:
            retrieved_password = self.password_manager.get_password(service)
            if retrieved_password:
                self.display_message(f"The password for {service} is: {retrieved_password}", retrieved_password)
            else:
                self.display_message(f"No password found for {service}")

    def generate_password(self):
        generated_password = self.password_manager.gen_password()
        self.display_message(f"Generated Password: {generated_password}", generated_password)


    def list_services(self):
        services = self.password_manager.list_password()
        if services:
            services_text = "\n".join(services)
            self.display_message(f"List of Services:\n{services_text}")
        else:
            self.display_message("No services found.")

    def delete_service(self):
        service, ok = QInputDialog.getText(self, 'Enter Service', 'Enter the service to delete:')
        if ok:
            self.password_manager.delete_service(service)
            self.display_message(f"Service '{service}' deleted successfully!")

    def exit_application(self):
        self.password_manager.connection.close()
        QApplication.quit()

    def upload_to_drive(self):
        self.password_manager.upload_to_drive()
        self.display_message("Database uploaded to Google Drive.")

    def download_from_drive(self):
        self.password_manager.download_from_drive()
        self.display_message("Database downloaded from Google Drive.")

class PasswordManager:
    def __init__(self, master_password, database_name='Password Manager\\Utils\\passwords.db'):
        self.database_name = database_name
        self.master_key = hashlib.sha256(master_password.encode()).digest()
        self.key = base64.urlsafe_b64encode(self.master_key[:32])  # Ensure the key is 32 bytes
        self.cipher_suite = Fernet(self.key)
        self.connection = self.create_database()
        self.passwords = {}

    def create_database(self):
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()

        # Create a table to store passwords
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS passwords (
                service TEXT PRIMARY KEY,
                encrypted_password TEXT NOT NULL
            )
        ''')

        connection.commit()
        return connection

    def encrypt_password(self, password):
        encrypted_password = self.cipher_suite.encrypt(password.encode())
        return encrypted_password

    def decrypt_password(self, encrypted_password):
        decrypted_password = self.cipher_suite.decrypt(encrypted_password).decode()
        return decrypted_password

    def store_password(self, service, password):
        encrypted_password = self.encrypt_password(password)
        
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO passwords (service, encrypted_password)
                VALUES (?, ?)
            ''', (service, encrypted_password))

    def get_password(self, service):
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT encrypted_password FROM passwords
                WHERE service = ?
            ''', (service,))
            result = cursor.fetchone()

        if result:
            encrypted_password = result[0]
            return self.decrypt_password(encrypted_password)
        else:
            return None
    
    def generate_password(self, length=12):
        characters = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(characters) for _ in range(length))
        return password

    def gen_password(self):
        generated_password = self.generate_password()
        return generated_password

    def list_password(self):
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT service FROM passwords
            ''')
            results = cursor.fetchall()

        if results:
            services = [result[0] for result in results]
            return services
        else:
            return None

    def delete_service(self, service):
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute('''
                DELETE FROM passwords
                WHERE service = ?
            ''', (service,))

    def upload_to_drive(self, database_name='Password Manager\\Utils\\passwords.db'):
        credentials = self.get_drive_credentials()
        service = build('drive', 'v3', credentials=credentials)

        # Retrieve all files and filter locally based on the file name
        files = service.files().list().execute().get('files', [])
        matching_files = [file for file in files if file['name'] == database_name]

        if matching_files:
            # File with the same name already exists, get the fileId of the first match
            file_id = matching_files[0]['id']
            media_body = MediaFileUpload(database_name, mimetype='application/octet-stream', resumable=True)
            request = service.files().update(fileId=file_id, media_body=media_body)
            request.execute()
        else:
            # File doesn't exist, create a new one
            media_body = MediaFileUpload(database_name, mimetype='application/octet-stream', resumable=True)
            request = service.files().create(media_body=media_body, body={'name': database_name})
            request.execute()

    def download_from_drive(self, database_name='Password Manager\\Utils\\passwords.db'):
        credentials = self.get_drive_credentials()
        service = build('drive', 'v3', credentials=credentials)

        files = service.files().list().execute().get('files', [])
        matching_files = [file for file in files if file['name'] == database_name]

        if not matching_files:
            print(f"Database '{database_name}' not found on Google Drive.")
            return

        file_id = matching_files[0]['id']
        request = service.files().get_media(fileId=file_id)

        with io.FileIO(database_name, 'wb') as file:
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                _, done = downloader.next_chunk()

        print(f"Database '{database_name}' downloaded from Google Drive.")

    def get_drive_credentials(self):
        creds = None
        token_path = 'Password Manager\\Utils\\token.json'

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'Password Manager\\Utils\\credentials.json', ['https://www.googleapis.com/auth/drive']
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        return creds

if __name__ == "__main__":
    app = QApplication([])
    ui = MainUI()
    ui.show()
    sys.exit(app.exec_())
