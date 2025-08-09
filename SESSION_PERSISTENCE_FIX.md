# Session Persistence and Homepage Navigation Fix

## Problem
When refreshing the page, the workflow that was created was being removed, and a fresh page was shown again. The user also requested a String-like interface with:
1. A homepage with chat history
2. A smooth sliding sidebar that appears on hover
3. Proper state persistence for workflows and conversations

## Solution Implemented

### 1. Enhanced Session Management (`frontend/lib/session.ts`)

**New Features Added:**
- **Workflow State Persistence**: Save/load complete workflow states including ReAct steps and progress
- **Conversation Caching**: Cache conversation lists to reduce API calls
- **Automatic Cleanup**: Remove old workflow states to prevent localStorage bloat
- **Enhanced State Structure**: Store workflow, reactSteps, and progress together

**Key Functions:**
```typescript
saveWorkflowState(sessionId: string, workflowState: Partial<WorkflowState>)
loadWorkflowState(sessionId: string): WorkflowState | null
clearWorkflowState(sessionId: string)
saveConversationsCache(conversations: any[])
loadConversationsCache(): any[] | null
cleanupOldWorkflowStates()
```

### 2. New Homepage Component (`frontend/components/HomePage.tsx`)

**Features:**
- **String-like Interface**: Matches the design shown in the provided images
- **Smooth Sliding Sidebar**: Appears on hover over the left edge of the screen
- **Conversation History**: Shows recent chats with workflow indicators
- **Quick Actions**: Pre-defined automation suggestions
- **Search Functionality**: Filter conversations by title or content
- **State Restoration**: Clicking on a conversation loads the complete workflow state

**Key UI Elements:**
- Main input field with "What do you want to automate?" prompt
- Grid of quick action buttons
- Recent chats section with workflow badges
- Hover-triggered sidebar with full conversation list

### 3. Enhanced TrueReActWorkflowBuilder (`frontend/components/TrueReActWorkflowBuilder.tsx`)

**New Features:**
- **Session ID Support**: Accept sessionId prop for loading specific conversations
- **Initial Query Support**: Auto-start with a query from the homepage
- **State Persistence**: Automatically save/restore workflow state, ReAct steps, and progress
- **Automatic State Loading**: Restore complete workflow state when switching between conversations

**Key Changes:**
```typescript
interface TrueReActWorkflowBuilderProps {
  sessionId?: string;
  initialQuery?: string;
}

// Auto-load persisted state
useEffect(() => {
  if (sessionId) {
    const persistedState = sessionManager.loadWorkflowState(sessionId);
    if (persistedState) {
      setCurrentWorkflow(persistedState.workflow);
      setReActSteps(persistedState.reactSteps);
      setProgress(persistedState.progress);
    }
  }
}, [sessionId]);

// Auto-save state changes
useEffect(() => {
  if (sessionId && (currentWorkflow || reactSteps.length > 0 || progress > 0)) {
    sessionManager.saveWorkflowState(sessionId, {
      workflow: currentWorkflow,
      reactSteps,
      progress
    });
  }
}, [sessionId, currentWorkflow, reactSteps, progress]);
```

### 4. Updated Main Page (`frontend/app/page.tsx`)

**Changes:**
- **Conditional Rendering**: Show HomePage or TrueReActWorkflowBuilder based on state
- **Navigation Logic**: Handle transitions between homepage and workflow builder
- **Brand Update**: Changed to "String" branding to match the provided design
- **Click-to-Home**: Logo is clickable to return to homepage

### 5. State Persistence Test Component (`frontend/components/StatePersistenceTest.tsx`)

**Purpose:**
- Test the session persistence functionality
- Verify save/load/clear operations work correctly
- Debug state management issues

## How It Works

### 1. Homepage Flow
1. User lands on homepage with String-like interface
2. Can type in main input or click quick actions
3. Recent conversations are shown with workflow indicators
4. Hovering on left edge reveals full conversation sidebar

### 2. Conversation Selection
1. User clicks on a conversation from recent chats or sidebar
2. System loads the conversation's sessionId
3. TrueReActWorkflowBuilder loads with the sessionId
4. Persisted state is automatically restored (workflow, ReAct steps, progress)

### 3. State Persistence
1. Every change to workflow, ReAct steps, or progress is automatically saved
2. State is keyed by sessionId for proper isolation
3. Old states are cleaned up automatically to prevent storage bloat
4. Page refresh maintains complete state

### 4. Sidebar Navigation
1. Hover over left 4px of screen triggers sidebar
2. Sidebar slides in smoothly with conversation list
3. Search functionality filters conversations
4. Click outside or X button closes sidebar

## Key Benefits

1. **No Data Loss**: Workflows persist across page refreshes
2. **Smooth UX**: String-like interface with intuitive navigation
3. **Performance**: Conversation caching reduces API calls
4. **Storage Management**: Automatic cleanup prevents localStorage bloat
5. **State Isolation**: Each conversation maintains its own complete state
6. **Visual Feedback**: Progress bars, workflow indicators, and status badges

## Technical Implementation Details

### LocalStorage Structure
```
promptflow_session: "current-session-id"
promptflow_last_activity: "2024-01-01T12:00:00.000Z"
promptflow_workflow_cache_session-123: {
  sessionId: "session-123",
  workflow: { ... },
  reactSteps: [ ... ],
  progress: 75,
  timestamp: "2024-01-01T12:00:00.000Z"
}
promptflow_conversations_cache: {
  conversations: [ ... ],
  timestamp: "2024-01-01T12:00:00.000Z"
}
```

### Error Handling
- All localStorage operations are wrapped in try-catch blocks
- Graceful degradation if localStorage is unavailable
- Console warnings for debugging without breaking functionality

### Performance Optimizations
- Conversation cache expires after 5 minutes
- Automatic cleanup keeps only 10 most recent workflow states
- Debounced state saving to prevent excessive writes

## Testing

To test the implementation:

1. **Basic Persistence**: Create a workflow, refresh page, verify it's restored
2. **Conversation Switching**: Switch between conversations, verify each maintains its state
3. **Sidebar Navigation**: Hover on left edge, verify smooth sidebar animation
4. **Homepage Flow**: Start from homepage, verify quick actions and recent chats work
5. **Storage Cleanup**: Create many workflows, verify old ones are cleaned up

The implementation provides a complete solution for state persistence and navigation that matches the String-like interface design while maintaining all workflow data across page refreshes and conversation switches.