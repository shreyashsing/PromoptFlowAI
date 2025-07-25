import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const authHeader = request.headers.get('authorization')

    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization header required' },
        { status: 401 }
      )
    }

    // Forward request to backend - Fixed URL to include /api/v1 prefix
    const backendResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/oauth/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authHeader
      },
      body: JSON.stringify(body)
    })

    const data = await backendResponse.json()

    if (!backendResponse.ok) {
      return NextResponse.json(data, { status: backendResponse.status })
    }

    return NextResponse.json(data)

  } catch (error) {
    console.error('OAuth callback error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}