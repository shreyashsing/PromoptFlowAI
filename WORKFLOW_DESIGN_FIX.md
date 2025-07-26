# Workflow Design Fix: Google Blog Search

## Current Issue
Your workflow was designed incorrectly. It's using Gmail to search for Google blogs, but Gmail searches your email inbox, not the web. This is why it's not finding the content you want.

## Correct Workflow Design
For your request "find the top 5 recent blogs posted by Google using Perplexity, summarize all 5 into one combined summary, and send the summarized text to Gmail", the workflow should be:

### Step 1: Web Search with Perplexity
- **Connector**: Perplexity Search
- **Action**: search
- **Query**: "recent blog posts from Google site:blog.google latest 5"
- **Purpose**: Find recent Google blog posts from the web

### Step 2: Summarize Content
- **Connector**: Text Summarizer
- **Input**: {perplexity_search.result}
- **Style**: paragraph
- **Length**: medium
- **Purpose**: Create a combined summary of all blog posts

### Step 3: Send Email
- **Connector**: Gmail Connector
- **Action**: send
- **To**: 19sumanshreya@gmail.com
- **Subject**: "Top 5 Recent Google Blogs - Summary"
- **Body**: {text_summarizer.result}
- **Purpose**: Send the summary via email

## How to Fix Your Current Workflow

### Option 1: Modify Existing Workflow
1. Go to your workflow editor
2. Replace the first Gmail connector (the one doing search) with Perplexity Search
3. Configure Perplexity with the query: "recent blog posts from Google site:blog.google latest 5"
4. Keep the Text Summarizer and final Gmail send connector as they are
5. Update the data flow connections

### Option 2: Create New Workflow
Ask the conversational agent again with a clearer request:
"Create a workflow that uses Perplexity to search for recent Google blog posts, then summarizes them and emails the summary to 19sumanshreya@gmail.com"

## Why This Matters
- **Gmail Search**: Searches your email inbox for emails from Google
- **Perplexity Search**: Searches the entire web for current blog posts
- **Web Content**: Blog posts are published on websites, not in your email

## Authentication Still Required
Even with the correct workflow design, you'll still need to:
1. Authenticate the Gmail connector for sending emails (follow GMAIL_AUTHENTICATION_GUIDE.md)
2. Ensure Perplexity connector has proper API credentials

## Expected Results
With the correct workflow:
- Perplexity will find actual recent blog posts from blog.google
- Text Summarizer will create a meaningful summary of the content
- Gmail will successfully send the summary to your email address