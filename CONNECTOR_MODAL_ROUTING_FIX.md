# Connector Modal Routing Fix

## Issue
Google Sheets and Perplexity connectors were showing the old generic configuration UI instead of their dedicated modal components with dynamic fields.

## Root Cause
The `TrueReActWorkflowBuilder.tsx` had its own switch statement for routing connector modals, but it was missing cases for `google_sheets` and `perplexity` connectors. This caused them to fall back to the generic `StringLikeConnectorModal` instead of using their specialized modals.

## Solution Applied

### 1. Updated TrueReActWorkflowBuilder.tsx

**Added Missing Imports:**
```typescript
import { GoogleSheetsConnectorModal } from '@/components/connectors/google_sheets';
import { PerplexityConnectorModal } from '@/components/connectors/perplexity';
```

**Added Missing Switch Cases:**
```typescript
switch (selectedConnector) {
  case 'notion':
    return <NotionConnectorModal {...modalProps} />;
  case 'google_drive':
    return <GoogleDriveConnectorModal {...modalProps} />;
  case 'google_sheets':  // ✅ ADDED
    return <GoogleSheetsConnectorModal {...modalProps} />;
  case 'youtube':
    return <YouTubeConnectorModal {...modalProps} />;
  case 'code':
    return <CodeConnectorModal {...modalProps} />;
  case 'airtable':
    return <AirtableConnectorModal {...modalProps} />;
  case 'gmail_connector':
    return <GmailConnectorModal {...modalProps} />;
  case 'perplexity':  // ✅ ADDED
    return <PerplexityConnectorModal {...modalProps} />;
  case 'google_translate':
    return <GoogleTranslateConnectorModal {...modalProps} />;
  default:
    return <StringLikeConnectorModal ... />;
}
```

### 2. Created Missing Index Files

**frontend/components/connectors/google_sheets/index.ts:**
```typescript
export { GoogleSheetsConnectorModal } from './GoogleSheetsConnectorModal';
```

**frontend/components/connectors/perplexity/index.ts:**
```typescript
export { PerplexityConnectorModal } from './PerplexityConnectorModal';
```

### 3. Updated ConnectorConfigModal.tsx (Already Done)

The `ConnectorConfigModal.tsx` was already updated with the correct routing for both connectors.

## Modal Routing Architecture

The system now has **two levels** of connector modal routing:

### Level 1: TrueReActWorkflowBuilder.tsx
- **Primary routing** for the main workflow builder
- Uses dedicated modal components directly
- Handles AI-generated parameters via `initialData` prop

### Level 2: ConnectorConfigModal.tsx  
- **Fallback routing** for other parts of the system
- Used by `StringLikeConnectorModal` and other generic components
- Also routes to the same dedicated modal components

## Result

Now when users configure Google Sheets or Perplexity connectors in the workflow builder, they will see:

✅ **Google Sheets**: 
- Dynamic spreadsheet selection from their Google Drive
- Dynamic sheet name selection based on chosen spreadsheet
- OAuth authentication flow
- Action-specific field configurations

✅ **Perplexity**:
- Dynamic model selection with descriptions
- API key authentication
- Chat vs Search action configurations
- Advanced parameter controls

Instead of the old generic form with manual ID entry.

## Verification

The fix ensures that:
1. **TrueReActWorkflowBuilder** (main workflow builder) uses the correct modals
2. **StringLikeWorkflowBuilder** routes through ConnectorConfigModal (already working)
3. **Other components** using ConnectorConfigModal get the correct modals
4. **AI-generated parameters** are properly passed to the specialized modals
5. **Authentication status** is checked and displayed correctly

All connector modals now provide the enhanced UX with dynamic field selection and real-time account data fetching.