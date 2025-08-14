# Google Sheets Dropdown Fix

## Problem
The Google Sheets connector modal was showing "No options available" in the spreadsheet dropdown, even though users had Google Sheets in their Drive and authentication was working.

## Root Cause
The issue was with OAuth scopes. The connector was using:
- `https://www.googleapis.com/auth/spreadsheets` (correct)
- `https://www.googleapis.com/auth/drive.file` (insufficient)

The `drive.file` scope only allows access to files that the app has created or that the user has explicitly opened with the app. It doesn't allow listing all spreadsheets in the user's Drive.

## Solution
Updated the OAuth scopes to:
- `https://www.googleapis.com/auth/spreadsheets` (for spreadsheet operations)
- `https://www.googleapis.com/auth/drive.readonly` (for listing all files in Drive)

## Files Modified

### Backend
1. **`backend/app/api/auth.py`** - Updated OAuth scope configuration
2. **`backend/app/connectors/core/google_sheets_connector.py`** - Updated connector scope requirements
3. **`backend/app/api/connector_fields.py`** - Enhanced error handling and logging

### Frontend
1. **`frontend/components/connectors/google_sheets/GoogleSheetsConnectorModal.tsx`** - Updated scope configuration

### Core OAuth
1. **`backend/app/core/oauth.py`** - Added drive.readonly scope to global configuration

## Enhanced Error Handling
Added comprehensive error handling to the `_fetch_google_spreadsheets` function:
- Token validity testing before API calls
- Detailed logging of API responses
- Better error messages for users
- Fallback checks to determine if user has any files in Drive

## Testing
Created test scripts to verify the fix:
- `backend/test_google_sheets_scope_fix.py` - Test scope validation
- `backend/test_google_sheets_simple.py` - Create test spreadsheet if needed
- `backend/debug_google_sheets_dropdown.py` - Comprehensive debugging

## User Action Required
**Important**: Users who previously authenticated with Google Sheets will need to re-authenticate to get the new scopes:

1. Open the Google Sheets connector modal
2. Go to the Authentication tab
3. Click "Disconnect" if already connected
4. Click "Connect with Google" to re-authenticate with new scopes

## Verification
After re-authentication, users should see:
- Their existing Google Sheets in the dropdown
- Proper error messages if no sheets exist
- Successful API calls with detailed logging

## Scope Comparison

### Before (Insufficient)
```
https://www.googleapis.com/auth/spreadsheets
https://www.googleapis.com/auth/drive.file
```

### After (Correct)
```
https://www.googleapis.com/auth/spreadsheets
https://www.googleapis.com/auth/drive.readonly
```

The `drive.readonly` scope allows the app to see and download all files in the user's Drive, which is necessary for listing spreadsheets in the dropdown.