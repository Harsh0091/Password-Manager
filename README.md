## Google Drive Integration Setup

To enable the Google Drive integration in this project, you need to generate your own `credentials.json` file. Follow these steps:

### 1. Enable Google Drive API
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing project.
3. Navigate to **APIs & Services** > **Library**.
4. Search for "Google Drive API" and click **Enable**.

### 2. Create Credentials
1. After enabling the API, go to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** and select **OAuth 2.0 Client IDs**.
3. Follow the prompts to configure the credentials. 
4. Download the `credentials.json` file and save it in the **Utils** directory of this project.

### 3. Set Up Your Environment
Make sure the `credentials.json` file is placed correctly for the application to use. If required, set the environment variable to the path of the credentials file:
You can use **key.py** to generate your own master key.
