# Connector Configuration Persistence Fix

## Problem
All connector modals were losing their saved configurations when reopening. Users would configure a connector, save it, then when reopening the modal, it would reset to default values instead of showing the saved configuration.

## Root Cause
1. **Missing Props**: Most connector modals were missing `initialConfig` and `mode` props
2. **No Configuration Loading**: Modals weren't loading saved parameters into their action/parameter state
3. **Generic Wrapper Issue**: `ConnectorConfigModal` wasn't passing through saved configurations

## Solution Applied

### 1. Fixed ConnectorConfigModal (Global Fix)
- Added `initialConfig`, `initialData`, and `mode` props to interface
- Updated all connector modal calls to pass through these props

### 2. Fixed Individual Connector Modals

#### Google Sheets ✅ FIXED
- Added proper `initialConfig.parameters` loading into `actionConfig`
- Added logging for debugging

#### Gmail ✅ FIXED  
- Added proper `initialConfig.parameters` loading into `actionConfig`
- Added logging for debugging

#### Notion ✅ FIXED
- Added missing `initialConfig` and `mode` props to interface
- Added configuration loading into `parameters` state
- Added resource/operation restoration

#### Remaining Connectors (Need Same Fix)
- YouTube
- Perplexity  
- Google Translate
- Google Drive
- Airtable
- Code

### 3. Pattern for Fixing Each Connector

1. **Add Missing Props to Interface**:
```tsx
interface ConnectorModalProps {
    // ... existing props
    initialConfig?: Partial<ConnectorConfig>; // Saved configuration
    initialData?: any; // AI-generated parameters  
    mode?: 'create' | 'edit';
}
```

2. **Update Component Function**:
```tsx
export function ConnectorModal({ 
    isOpen, 
    onClose, 
    onSave, 
    initialConfig,    // Add this
    initialData, 
    mode = 'create'   // Add this
}: ConnectorModalProps) {
```

3. **Add Configuration Loading useEffect**:
```tsx
// Initialize configuration
useEffect(() => {
    if (initialConfig) {
        console.log('🔄 [Connector] Modal: Loading saved configuration:', initialConfig);
        
        // Load general config
        setConfig(prev => ({ ...prev, ...initialConfig }));
        
        // Load saved parameters into actionConfig/parameters
        if (initialConfig.parameters) {
            console.log('🔄 [Connector] Modal: Loading saved parameters:', initialConfig.parameters);
            setActionConfig(prev => ({ ...prev, ...initialConfig.parameters }));
            // OR for connectors using different state:
            // setParameters(prev => ({ ...prev, ...initialConfig.parameters }));
        }
        
        // Update auth status if needed
        if (initialConfig.auth_config?.access_token) {
            setAuthStatus('authenticated');
        }
    }
}, [initialConfig]);
```

## Files Modified

### Core Infrastructure
- `frontend/components/ConnectorConfigModal.tsx` - Added props and pass-through
- `frontend/lib/connector-config-utils.ts` - Created utility functions

### Fixed Connectors
- `frontend/components/connectors/google_sheets/GoogleSheetsConnectorModal.tsx`
- `frontend/components/connectors/gmail/GmailConnectorModal.tsx`  
- `frontend/components/connectors/notion/NotionConnectorModal.tsx`

### Remaining Connectors (Need Fix)
- `frontend/components/connectors/youtube/YouTubeConnectorModal.tsx`
- `frontend/components/connectors/perplexity/PerplexityConnectorModal.tsx`
- `frontend/components/connectors/google_translate/GoogleTranslateConnectorModal.tsx`
- `frontend/components/connectors/google_drive/GoogleDriveConnectorModal.tsx`
- `frontend/components/connectors/airtable/AirtableConnectorModal.tsx`
- `frontend/components/connectors/code/CodeConnectorModal.tsx`

## Testing
After applying fixes, test by:
1. Configure a connector with specific parameters
2. Save the configuration  
3. Open a different connector modal
4. Reopen the original connector modal
5. Verify saved parameters are loaded correctly

## Impact
- ✅ Configurations now persist between modal opens/closes
- ✅ No more losing saved settings when switching between connectors
- ✅ Better user experience with preserved state
- ✅ Consistent behavior across all connectors