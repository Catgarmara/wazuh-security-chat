import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const healthData = {
      status: 'healthy',
      service: 'wazuh-ai-frontend',
      version: process.env.NEXT_PUBLIC_APP_VERSION || '2.0.0',
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development',
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      features: {
        siem_dashboard: process.env.NEXT_PUBLIC_FEATURE_SIEM_DASHBOARD === 'true',
        model_management: process.env.NEXT_PUBLIC_FEATURE_MODEL_MANAGEMENT === 'true',
        threat_correlation: process.env.NEXT_PUBLIC_FEATURE_THREAT_CORRELATION === 'true',
        alert_management: process.env.NEXT_PUBLIC_FEATURE_ALERT_MANAGEMENT === 'true',
      },
      configuration: {
        api_url: process.env.NEXT_PUBLIC_API_URL,
        ws_url: process.env.NEXT_PUBLIC_WS_URL,
        theme: process.env.NEXT_PUBLIC_THEME || 'dark',
        auth_enabled: process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true',
      }
    };

    return NextResponse.json(healthData, { status: 200 });
  } catch (error) {
    const errorData = {
      status: 'unhealthy',
      service: 'wazuh-ai-frontend',
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString(),
    };

    return NextResponse.json(errorData, { status: 500 });
  }
}