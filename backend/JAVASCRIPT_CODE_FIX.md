# JavaScript Code Fix for Blog Content Extraction

## Problem
The JavaScript code in the code node is not finding blog content because it's not handling the correct data structure. The input data comes wrapped in a `main` key, but the code expects it at the root level.

## Current Input Structure
```javascript
inputData = {
  "main": {
    "response": "Blog content here...",
    "citations": [...]
  }
}
```

## Fixed JavaScript Code
```javascript
// Inspect inputData and extract blog post contents
let blogContents = [];
let blogCount = 0;

// Helper function to extract content from a blog post object
function extractContent(blog) {
  if (!blog || typeof blog !== 'object') return '';
  // Try common content fields
  const possibleFields = ['content', 'body', 'text', 'description', 'response'];
  for (let field of possibleFields) {
    if (typeof blog[field] === 'string' && blog[field].length > 0) {
      return blog[field];
    }
  }
  
  // Try other string properties
  for (let key in blog) {
    if (typeof blog[key] === 'string' && blog[key].length > 50) {
      return blog[key];
    }
  }
  
  return '';
}

// Get the actual data - handle the 'main' wrapper
let actualData = inputData;
if (inputData && typeof inputData === 'object' && inputData.main) {
  actualData = inputData.main;
}

// Process the actual data
if (actualData && typeof actualData === 'object') {
  // Try to find an array property
  for (let key in actualData) {
    if (Array.isArray(actualData[key])) {
      const blogsArray = actualData[key];
      for (let blog of blogsArray) {
        let content = extractContent(blog);
        if (content) {
          blogContents.push(content);
          blogCount++;
        }
      }
      break;
    }
  }
  
  // If no array found, try to extract from main response
  if (blogContents.length === 0) {
    // Check if there's a response field with content
    if (actualData.response && typeof actualData.response === 'string' && actualData.response.length > 0) {
      blogContents.push(actualData.response);
      blogCount = 1;
    }
    // Check if the whole actualData is a string
    else if (typeof actualData === 'string' && actualData.length > 0) {
      blogContents.push(actualData);
      blogCount = 1;
    }
  }
}

// If actualData is a string, treat as single blog content
if (typeof actualData === 'string' && actualData.length > 0) {
  blogContents = [actualData];
  blogCount = 1;
}

const combinedText = blogContents.join('\n\n');

return {
  combinedText,
  blogCount,
  timestamp: new Date().toISOString(),
  sourceType: typeof actualData,
  originalKeys: Object.keys(actualData || {}),
  debugInfo: {
    inputDataType: typeof inputData,
    actualDataType: typeof actualData,
    inputDataKeys: inputData ? Object.keys(inputData) : [],
    actualDataKeys: actualData ? Object.keys(actualData) : [],
    foundArrays: actualData ? Object.keys(actualData).filter(key => Array.isArray(actualData[key])) : []
  }
};
```

## Key Changes
1. **Handle the 'main' wrapper**: Extract `actualData = inputData.main` if it exists
2. **Added 'response' to content fields**: Include 'response' as a valid content field
3. **Better debugging**: Added more debug information to understand data structure

This fix should resolve the issue where `blogCount` is 0 and `combinedText` is empty.