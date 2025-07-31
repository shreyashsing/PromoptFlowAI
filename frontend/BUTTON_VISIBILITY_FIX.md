# Button Visibility Fix - True ReAct Workflow Builder

## Problem
The send button in the bottom input area was being cut off and not visible on screen, making it impossible for users to send messages.

## Root Cause
The layout was using flexbox with `h-screen` which didn't properly account for:
1. Browser UI elements (address bar, etc.)
2. Proper space allocation for the bottom input area
3. The button being pushed below the viewport

## Solution Applied

### 1. Changed Layout System
- **From**: Flexbox (`flex flex-col`)
- **To**: CSS Grid (`grid grid-rows-[auto_1fr_auto]`)

### 2. Height Management
- **Container**: `h-[100vh]` for reliable viewport height
- **Sidebar**: `h-full` to fill container
- **Grid Layout**: 
  - Header: `auto` (fits content)
  - Steps: `1fr` (takes remaining space)
  - Input: `auto` with `min-h-[120px]` (guaranteed space)

### 3. Space Optimization
- Reduced padding: `p-4` → `p-3`
- Reduced spacing: `space-y-3` → `space-y-2`
- Reduced textarea rows: `3` → `2`
- Added minimum height for input area: `min-h-[120px]`

### 4. Scroll Area Constraints
- Added `min-h-0` to prevent flex overflow
- Added `max-h-[calc(100vh-200px)]` to ensure space for input

## Layout Structure (After Fix)

```tsx
<div className="h-[100vh] bg-gray-900 text-white flex overflow-hidden">
  <div className="w-96 bg-gray-800 border-r border-gray-700 grid grid-rows-[auto_1fr_auto] h-full">
    {/* Header - auto height */}
    <div className="p-4 border-b border-gray-700">
      {/* Title + Progress */}
    </div>

    {/* Steps - 1fr height (flexible) */}
    <div className="overflow-hidden min-h-0">
      <ScrollArea className="h-full max-h-[calc(100vh-200px)]">
        {/* ReAct steps */}
      </ScrollArea>
    </div>

    {/* Input - auto height with minimum */}
    <div className="p-3 border-t border-gray-700 min-h-[120px]">
      <Textarea rows={2} />
      <Button />
    </div>
  </div>
</div>
```

## Result
✅ Send button always visible
✅ Proper space allocation
✅ Responsive layout
✅ Reliable height management
✅ Better mobile compatibility

The input area now has guaranteed space and the button is always accessible to users.