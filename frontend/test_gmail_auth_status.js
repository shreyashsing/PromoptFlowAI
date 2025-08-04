// Test script to verify Gmail authentication status check
// Run this in browser console when Gmail modal is open

async function testGmailAuthStatus() {
    console.log('🧪 Testing Gmail authentication status check...');
    
    try {
        // Get session token (this would normally come from auth context)
        const baseUrl = 'http://localhost:8000';
        
        // First, let's see what tokens are available
        const response = await fetch(`${baseUrl}/api/v1/auth/tokens`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer YOUR_SESSION_TOKEN_HERE`, // Replace with actual token
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            console.log('📋 All tokens:', data);
            
            const gmailToken = data.tokens?.find(token => 
                token.connector_name === 'gmail_connector' && 
                token.token_type === 'oauth2' && 
                token.is_active
            );

            if (gmailToken) {
                console.log('✅ Gmail token found:', gmailToken);
                console.log('🔑 Access token available:', !!gmailToken.token_data?.access_token);
                console.log('🔄 Refresh token available:', !!gmailToken.token_data?.refresh_token);
            } else {
                console.log('❌ No valid Gmail token found');
            }
        } else {
            console.error('❌ Failed to fetch tokens:', response.status, response.statusText);
        }
    } catch (error) {
        console.error('❌ Error testing auth status:', error);
    }
}

// Run the test
testGmailAuthStatus();