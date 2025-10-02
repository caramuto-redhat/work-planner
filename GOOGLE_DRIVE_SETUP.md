# Google Drive Integration Setup

This guide explains how to set up Google Drive integration for the scheduled Slack data collection workflow.

## 🔧 Setup Steps

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Google Drive API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"

### 2. Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Fill in details:
   - **Name**: `slack-data-collector`
   - **Description**: `Service account for Slack data collection`
4. Click "Create and Continue"
5. Skip role assignment (click "Continue")
6. Click "Done"

### 3. Generate Service Account Key

1. Find your service account in the credentials list
2. Click on the service account email
3. Go to "Keys" tab
4. Click "Add Key" → "Create new key"
5. Select "JSON" format
6. Click "Create"
7. **Save the JSON file securely** - this contains your credentials

### 4. Create Google Drive Folder

1. Go to [Google Drive](https://drive.google.com/)
2. Create a new folder: `Slack Data Dumps`
3. Right-click the folder → "Share"
4. Add your service account email (from step 2)
5. Give "Editor" permissions
6. Copy the **Folder ID** from the URL:
   ```
   https://drive.google.com/drive/folders/FOLDER_ID_HERE
   ```

### 5. Configure GitHub Secrets

Add these secrets to your GitHub repository:

1. Go to your repo → "Settings" → "Secrets and variables" → "Actions"
2. Add these repository secrets:

#### `GOOGLE_DRIVE_CREDENTIALS`
- **Value**: The entire JSON content from step 3
- **Example**:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "slack-data-collector@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

#### `GOOGLE_DRIVE_FOLDER_ID`
- **Value**: The folder ID from step 4
- **Example**: `1ABC123DEF456GHI789JKL`

## 🎯 How It Works

1. **Workflow runs** - Collects Slack data from all configured channels
2. **Creates zip file** - Bundles all dump files with timestamp
3. **Uploads to Drive** - Uses service account to upload to your folder
4. **Cleans up** - Removes local zip file after upload

## 📁 File Organization

Files are uploaded with this naming pattern:
```
slack-dumps-YYYYMMDD-HHMMSS.zip
```

Example: `slack-dumps-20241002-143022.zip`

## 🔒 Security Notes

- **Service account** has minimal permissions (only Drive access)
- **Credentials** are stored securely in GitHub secrets
- **No Slack notifications** - Silent operation as requested
- **Automatic cleanup** - Local files are removed after upload

## 🧪 Testing

1. Run the workflow manually from GitHub Actions
2. Check your Google Drive folder for the uploaded zip file
3. Verify the zip contains all your Slack dump files

## 🚨 Troubleshooting

### Common Issues:

1. **"Permission denied"** - Make sure service account has access to the folder
2. **"Invalid credentials"** - Check JSON format in GitHub secret
3. **"Folder not found"** - Verify folder ID is correct
4. **"API not enabled"** - Ensure Google Drive API is enabled

### Debug Steps:

1. Check GitHub Actions logs for detailed error messages
2. Verify all secrets are set correctly
3. Test service account permissions manually
4. Ensure folder ID is from the correct Google account
