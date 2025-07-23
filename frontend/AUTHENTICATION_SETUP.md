# Frontend Authentication Setup

## Overview
Complete Supabase authentication integration for the PromptFlow AI frontend.

## Features Implemented

### 🔐 Authentication Components
- **LoginForm**: Email/password login with validation
- **SignUpForm**: User registration with email confirmation
- **UserMenu**: Dropdown menu with user profile and logout
- **ProtectedRoute**: Wrapper component for authenticated routes

### 🔄 Authentication Context
- **AuthProvider**: React context for global auth state
- **useAuth**: Custom hook for accessing auth functions
- Session management with automatic token refresh
- Persistent authentication state

### 🛡️ Security Features
- JWT token handling with automatic refresh
- Protected routes that redirect to login
- Secure token storage via Supabase client
- API request interceptors for authentication

### 🎨 UI/UX Components
- Modern, responsive design with Tailwind CSS
- Loading states and error handling
- Accessible form components with proper validation
- Consistent styling with existing design system

## Setup Instructions

### 1. Environment Variables
Create or update `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

### 2. Supabase Configuration
1. Go to your Supabase project dashboard
2. Navigate to Settings > API
3. Copy your Project URL and anon/public key
4. Update the environment variables above

### 3. Authentication Flow
1. Users visit `/auth` for login/signup
2. Successful authentication redirects to main app
3. Protected routes automatically redirect unauthenticated users
4. User menu provides profile access and logout

## File Structure

```
frontend/
├── lib/
│   ├── supabase.ts              # Supabase client configuration
│   ├── auth-context.tsx         # Authentication context provider
│   ├── api.ts                   # Updated API client with auth
│   └── types.ts                 # Updated with user types
├── components/
│   ├── auth/
│   │   ├── LoginForm.tsx        # Login form component
│   │   ├── SignUpForm.tsx       # Registration form component
│   │   ├── UserMenu.tsx         # User dropdown menu
│   │   └── ProtectedRoute.tsx   # Route protection wrapper
│   └── ui/                      # Reusable UI components
├── app/
│   ├── auth/
│   │   └── page.tsx             # Authentication page
│   ├── layout.tsx               # Updated with AuthProvider
│   └── page.tsx                 # Updated with ProtectedRoute
└── .env.local                   # Environment variables
```

## Usage Examples

### Using Authentication in Components
```tsx
import { useAuth } from '@/lib/auth-context'

function MyComponent() {
  const { user, signOut, loading } = useAuth()
  
  if (loading) return <div>Loading...</div>
  if (!user) return <div>Please log in</div>
  
  return (
    <div>
      <p>Welcome, {user.email}!</p>
      <button onClick={signOut}>Sign Out</button>
    </div>
  )
}
```

### Protecting Routes
```tsx
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

function ProtectedPage() {
  return (
    <ProtectedRoute>
      <div>This content is only visible to authenticated users</div>
    </ProtectedRoute>
  )
}
```

### Making Authenticated API Calls
```tsx
import api from '@/lib/api'

// API client automatically includes auth headers
const response = await api.get('/api/v1/workflows')
```

## Authentication States

### Loading State
- Shown while checking authentication status
- Prevents flash of unauthenticated content

### Authenticated State
- User has valid session
- Access to protected routes and features
- API calls include authentication headers

### Unauthenticated State
- User needs to log in
- Redirected to `/auth` page
- Limited access to public content only

## Error Handling

### Authentication Errors
- Invalid credentials show user-friendly messages
- Network errors are handled gracefully
- Token refresh failures redirect to login

### API Errors
- 401 responses trigger automatic token refresh
- Failed refresh redirects to authentication page
- Other errors are passed through to components

## Security Considerations

### Token Management
- Access tokens stored securely by Supabase client
- Automatic refresh prevents expired token issues
- Logout clears all authentication data

### Route Protection
- Server-side rendering respects authentication state
- Client-side navigation is protected
- Deep links redirect through authentication flow

### API Security
- All API requests include authentication headers
- Backend validates tokens on every request
- Expired tokens are automatically refreshed

## Testing

### Manual Testing
1. Visit `/auth` and create a new account
2. Check email for confirmation link
3. Log in with created credentials
4. Verify protected routes work correctly
5. Test logout functionality

### Development Mode
- Dev token fallback for backend testing
- Environment variable validation
- Error boundary for auth failures

## Troubleshooting

### Common Issues

**Build Error: "supabaseUrl is required"**
- Ensure environment variables are set correctly
- Check `.env.local` file exists and has correct values

**Infinite Redirect Loop**
- Verify Supabase URL and keys are correct
- Check authentication callback URLs in Supabase dashboard

**API Calls Failing**
- Confirm backend is running and accessible
- Verify CORS settings allow frontend domain
- Check authentication headers are being sent

### Debug Mode
Enable debug logging by adding to your component:
```tsx
const { user, session } = useAuth()
console.log('Auth Debug:', { user, session })
```

## Next Steps

### Enhancements
1. **Password Reset**: Add forgot password functionality
2. **Social Login**: Integrate Google/GitHub OAuth
3. **Profile Management**: User profile editing page
4. **Role-Based Access**: Different user roles and permissions
5. **Session Management**: Advanced session controls

### Integration
1. **Backend Sync**: Ensure user profiles sync with backend
2. **Workflow Ownership**: Associate workflows with authenticated users
3. **API Permissions**: Implement proper authorization checks
4. **Audit Logging**: Track user actions and authentication events

## Production Checklist

- [ ] Environment variables configured
- [ ] Supabase project properly set up
- [ ] Email templates customized
- [ ] CORS settings configured
- [ ] SSL certificates in place
- [ ] Error monitoring enabled
- [ ] Authentication flows tested
- [ ] Security review completed

## Support

For issues or questions:
1. Check this documentation first
2. Review Supabase authentication docs
3. Check browser console for errors
4. Verify environment configuration
5. Test with fresh browser session