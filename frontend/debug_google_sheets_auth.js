// Debug script to test Google Sheets authentication status
// Run this in browser console on the workflow page

console.log('🔍 Debugging Google Sheets Authentication Status');

// Test the authentication check logic
function testAuthCheck(connectorName) {
  console.log(`\n📋 Testing connector: ${connectorName}`);
  
  if (connectorName === 'gmail_connector' || 
      connectorName === 'perplexity_search' || 
      connectorName === 'google_sheets') {
    console.log('✅ Connector requires authentication');
    return 'required'; // Assuming no tokens for this test
  } else {
    console.log('ℹ️  Connector needs no authentication');
    return 'none';
  }
}

// Test different connectors
const testCases = [
  'gmail_connector',
  'google_sheets',
  'perplexity_search',
  'http_request',
  'webhook'
];

console.log('\n📊 Test Results:');
testCases.forEach(connector => {
  const result = testAuthCheck(connector);
  console.log(`${connector}: ${result}`);
});

// Check if there are any authentication tokens
console.log('\n🔑 Checking for existing tokens...');
fetch('/api/auth/tokens', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('supabase.auth.token') || 'no-token'}`
  }
})
.then(response => response.json())
.then(data => {
  console.log('📄 Token response:', data);
  if (data.tokens) {
    console.log('🔍 Found tokens:');
    data.tokens.forEach(token => {
      console.log(`  - ${token.connector_name}: ${token.token_type}`);
    });
  }
})
.catch(error => {
  console.error('❌ Error fetching tokens:', error);
});

console.log('\n💡 If Google Sheets still shows "No authentication required":');
console.log('1. Try refreshing the page (Ctrl+F5)');
console.log('2. Clear browser cache');
console.log('3. Check browser console for errors');
console.log('4. Verify the fix is applied in ConnectorConfigModal.tsx');