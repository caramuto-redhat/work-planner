# Email Integration Setup

This guide explains how to set up email integration for the scheduled Slack data collection workflow.

## 🔧 Setup Steps

### 1. Configure Email Credentials

The workflow uses Gmail SMTP to send emails with Slack data attachments.

#### Gmail App Password Setup

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to [Google Account Settings](https://myaccount.google.com/)
   - Click "Security" → "2-Step Verification"
   - Scroll down to "App passwords"
   - Select "Mail" and "Other (custom name)"
   - Enter: `Work Planner MCP`
   - Copy the generated password (16 characters)

### 2. Configure GitHub Secrets

Add these secrets to your GitHub repository:

1. Go to your repo → "Settings" → "Secrets and variables" → "Actions"
2. Add these repository secrets:

#### `EMAIL_USERNAME`
- **Value**: Your Gmail address
- **Example**: `pacaramu@redhat.com`

#### `EMAIL_TOKEN`
- **Value**: The 16-character app password from step 1
- **Example**: `gnisffrdallrdafo`

#### `EMAIL_FROM`
- **Value**: Your Gmail address (same as EMAIL_USERNAME)
- **Example**: `pacaramu@redhat.com`

## 🎯 How It Works

1. **Workflow runs** - Collects Slack data from all configured channels
2. **Creates zip file** - Bundles all dump files with timestamp
3. **Sends email** - Uses Gmail SMTP to send email with attachment
4. **Cleans up** - Removes local zip file after sending

## 📧 Email Content

Each email includes:

### **Subject**
```
Slack Data Collection - YYYY-MM-DD HH:MM
```

### **Body**
- Collection date and time
- GitHub run number and commit hash
- List of processed channels
- Description of attached files

### **Attachment**
- **Filename**: `slack-dumps-YYYYMMDD-HHMMSS.zip`
- **Contents**: All Slack dump files (raw and parsed)

## 🔒 Security Notes

- **App passwords** are more secure than regular passwords
- **SMTP over TLS** - Encrypted email transmission
- **No external dependencies** - Uses built-in Python email libraries
- **Automatic cleanup** - Local files are removed after sending

## 🧪 Testing

1. Run the workflow manually from GitHub Actions
2. Check your email for the Slack data collection report
3. Download and verify the attached zip file contains your Slack dumps

## 🚨 Troubleshooting

### Common Issues:

1. **"Authentication failed"** - Check app password is correct
2. **"SMTP connection failed"** - Verify Gmail SMTP settings
3. **"Email not received"** - Check spam folder
4. **"Attachment too large"** - Gmail has 25MB attachment limit

### Debug Steps:

1. Check GitHub Actions logs for detailed error messages
2. Verify all email secrets are set correctly
3. Test email credentials manually
4. Ensure 2FA is enabled on Gmail account

## 📋 Benefits

- ✅ **Simple setup** - No external APIs or complex permissions
- ✅ **Reliable delivery** - Gmail SMTP is very reliable
- ✅ **Easy access** - Files delivered directly to your inbox
- ✅ **Automatic organization** - Timestamped files
- ✅ **No storage limits** - Gmail provides plenty of space
