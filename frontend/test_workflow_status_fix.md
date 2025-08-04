# Workflow Status Fix

## Issue
Workflows were being created with status "draft" instead of "active", causing execution to fail with error:
> "Workflow must be ACTIVE to execute (current status: draft)"

## Root Cause Analysis

### 1. Backend Model Issue
The `CreateWorkflowRequest` model in `backend/app/models/database.py` didn't include a `status` field, so the frontend's `status: 'active'` was being ignored.

### 2. Hardcoded Draft Status
The workflow creation logic in `backend/app/api/workflows.py` was hardcoded to use `WorkflowStatus.DRAFT`:
```python
status=WorkflowStatus.DRAFT,  # This was hardcoded!
```

### 3. Data Format Mismatch
The frontend was sending `steps` but the backend expected `nodes` and `edges` format.

## Fixes Applied

### 1. Updated CreateWorkflowRequest Model
```python
class CreateWorkflowRequest(BaseModel):
    # ... other fields ...
    status: Optional[WorkflowStatus] = WorkflowStatus.ACTIVE  # Added status field
```

### 2. Fixed Workflow Creation Logic
```python
status=request.status or WorkflowStatus.ACTIVE,  # Use request status or default to ACTIVE
```

### 3. Fixed Frontend Data Format
Updated frontend to transform `steps` into `nodes` and `edges`:
```javascript
nodes: (currentWorkflow.steps || []).map((step, index) => ({
  id: `${step.connector_name}-${index}`,
  type: 'connector',
  connector_name: step.connector_name,
  parameters: step.parameters || {},
  position: { x: index * 250 + 100, y: 100 }
})),
edges: // Generate edges connecting sequential steps
```

## Expected Behavior After Fix
1. Workflows created by ReAct agent will have status "active"
2. Workflow execution will succeed immediately after creation
3. No more "draft status" errors
4. Proper transformation from ReAct steps to workflow nodes/edges

## Testing
1. Create a workflow using the ReAct agent
2. Click "Run Workflow" 
3. Verify workflow executes without status errors
4. Check that Gmail connector actually sends emails