# Project Calendar Dashboard

A secure web application for managing project calendars and social media content planning.

## Features
- Password-protected access
- Project management
- Calendar entry management
- CSV export functionality
- Secure session handling

## Deployment on Render

### 1. Prerequisites
- A [Render](https://render.com) account
- Your project code in a Git repository (GitHub, GitLab, etc.)

### 2. Deployment Steps

1. Log in to your Render dashboard
2. Click "New +" and select "Web Service"
3. Connect your Git repository
4. Configure the service:
   - **Name**: Choose a name for your service
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free (or choose paid tier for production)

### 3. Environment Variables
Set the following environment variables in Render dashboard:
- Go to your web service → Environment
- Add the following variables:
```
SECRET_KEY=<generate_a_secure_random_key>
ADMIN_PASSWORD=<your_chosen_password>
```

### 4. Important Settings
In your Render dashboard:
1. Enable HTTPS (automatic with Render)
2. Set Python version to 3.9 or higher
3. Make sure all environment variables are set before deploying

### 5. Auto-Deploy
Render automatically deploys:
- When you push to your main/master branch
- When you manually trigger a deploy from dashboard

### 6. Monitoring
After deployment:
1. Check the deployment logs in Render dashboard
2. Verify the application is running by visiting your Render URL
3. Test the login functionality
4. Monitor the application logs for any issues

### Local Development
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export SECRET_KEY=your_random_secret_key
export ADMIN_PASSWORD=your_secure_password
```

3. Run the application:
```bash
python app.py
```

### Security Notes
- Change the default admin password
- Use HTTPS in production (automatic with Render)
- Keep environment variables secure
- Regular backup of data.json file

## Data Storage
All calendar data is stored in `data.json`. Ensure regular backups of this file.

## Troubleshooting
1. If the application fails to start:
   - Check the Render logs
   - Verify environment variables
   - Ensure requirements.txt is complete
   - Check Python version compatibility

2. If you can't log in:
   - Verify ADMIN_PASSWORD environment variable
   - Clear browser cache and cookies
   - Check application logs for auth errors

3. If changes don't deploy:
   - Manually trigger a deploy in Render dashboard
   - Check deployment logs for errors
   - Verify Git repository connection 