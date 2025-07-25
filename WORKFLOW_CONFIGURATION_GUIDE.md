# Workflow Configuration Guide

## 🚨 **Current Execution Issues Fixed**

The workflow execution failed due to missing required parameters and authentication. Here's how to fix each issue:

## 🔧 **Step-by-Step Configuration**

### 1. **Perplexity Search Node Configuration**
**Error**: `Parameter validation failed for perplexity_search: 'action' is a required property`

**Fix**: Configure the Perplexity node with required parameters:
- **Action**: Select "search" (required)
- **Query**: "Find the top 5 recent blogs posted by Google"
- **Model**: "llama-3.1-sonar-small-128k-online"
- **API Key**: Your Perplexity API key (in Authentication tab)

### 2. **Text Summarizer Node Configuration**
**Error**: `Unexpected error in text_summarizer: 1 validation error for AuthRequirements`

**Fix**: Configure the Text Summarizer node:
- **Text**: Use output from Perplexity search
- **Max Length**: 100 words
- **Style**: "concise"
- **OpenAI API Key**: Your OpenAI API key (in Authentication tab)

### 3. **Gmail Connector Node Configuration**
**Error**: `Missing required auth field: access_token`

**Fix**: Configure the Gmail node:
- **Action**: Select "send" (required)
- **To**: "shreyashbarca10@gmail.com"
- **Subject**: "Google Blog Summary"
- **Body**: Use output from Text Summarizer
- **Access Token**: Gmail OAuth access token (in Authentication tab)

## 🎯 **How to Use the Interactive Configuration**

### **Step 1: Open Configuration Modal**
1. Double-click on any workflow node
2. Or hover over node and click "Configure" button

### **Step 2: Configure Parameters**
1. **Configuration Tab**: Set all required parameters
2. **Authentication Tab**: Add API keys/tokens
3. **Advanced Tab**: Adjust timeout and retry settings

### **Step 3: Save Configuration**
1. Fill all required fields (marked with red "Required" badges)
2. Click "Save Configuration"
3. Node will show "Configured" status with green checkmark

## 🔑 **Authentication Setup**

### **Perplexity API Key**
1. Go to [Perplexity API](https://www.perplexity.ai/settings/api)
2. Generate API key
3. Add to Authentication tab in Perplexity node

### **OpenAI API Key**
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create new secret key
3. Add to Authentication tab in Text Summarizer node

### **Gmail OAuth Token**
1. Set up Google OAuth application
2. Get access token through OAuth flow
3. Add to Authentication tab in Gmail node

## 📋 **Required Parameters Summary**

### **Perplexity Search Node**
```json
{
  "action": "search",
  "query": "Find the top 5 recent blogs posted by Google",
  "model": "llama-3.1-sonar-small-128k-online",
  "api_key": "your-perplexity-api-key"
}
```

### **Text Summarizer Node**
```json
{
  "text": "{{perplexity_search.result}}",
  "max_length": 100,
  "style": "concise",
  "openai_api_key": "your-openai-api-key"
}
```

### **Gmail Connector Node**
```json
{
  "action": "send",
  "to": "shreyashbarca10@gmail.com",
  "subject": "Google Blog Summary",
  "body": "{{text_summarizer.result}}",
  "access_token": "your-gmail-oauth-token"
}
```

## 🎨 **Visual Configuration Status**

### **Node Status Indicators**
- 🟢 **Green dot**: Node configured and ready
- 🟠 **Orange dot**: Node needs configuration
- 🔴 **Red dot**: Node has errors
- 🔵 **Blue dot**: Node is running

### **Configuration Status**
- ✅ **"Configured"**: All required parameters set
- ⚠️ **"Needs setup"**: Missing required parameters
- 🔑 **"Auth required"**: Missing authentication

## 🚀 **Testing the Workflow**

### **Before Execution**
1. Ensure all nodes show "Configured" status
2. Check authentication is set up for all nodes
3. Verify parameter values are correct

### **During Execution**
1. Watch node status indicators change
2. Blue dots show currently running nodes
3. Green dots show completed nodes
4. Red dots show failed nodes

### **After Execution**
1. Check execution results in workflow panel
2. Review any error messages
3. Adjust configuration if needed

## 🔄 **Common Configuration Patterns**

### **Parameter Chaining**
- Use `{{previous_node.result}}` to chain outputs
- Text Summarizer uses Perplexity search results
- Gmail uses Text Summarizer output

### **Conditional Parameters**
- Some parameters only appear based on action selection
- Gmail "to" field only needed for "send" action
- Sheets "data" field only needed for "write" action

### **Default Values**
- Many parameters have sensible defaults
- Override defaults as needed for your use case
- Advanced settings usually have good defaults

## 📝 **Best Practices**

### **Parameter Configuration**
1. **Start with required fields** - Fill all red "Required" badges first
2. **Use descriptive values** - Clear parameter names help debugging
3. **Test incrementally** - Configure and test one node at a time

### **Authentication Management**
1. **Store securely** - Never commit API keys to version control
2. **Use environment variables** - For production deployments
3. **Rotate regularly** - Update API keys periodically

### **Error Handling**
1. **Check logs** - Review execution logs for detailed errors
2. **Validate inputs** - Ensure parameter formats are correct
3. **Test connections** - Verify API keys work before execution

## 🎯 **Next Steps**

1. **Configure each node** using the interactive modal
2. **Add authentication** for all connectors
3. **Test the workflow** with proper configuration
4. **Monitor execution** and adjust as needed

The interactive configuration system now makes it easy to set up complex workflows with proper parameter validation and authentication management!