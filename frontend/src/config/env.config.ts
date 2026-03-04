/**
 * Environment configuration helper
 * Provides type-safe access to environment variables
 */

interface EnvConfig {
  // Application
  appEnv: 'development' | 'staging' | 'production' | 'testing';
  appName: string;
  appVersion: string;
  appUrl: string;
  
  // API
  apiUrl: string;
  wsUrl: string;
  apiTimeout: number;
  apiRetryCount: number;
  
  // Features
  enableMockApi: boolean;
  enableAnalytics: boolean;
  enableSentry: boolean;
  enableDarkMode: boolean;
  enablePushNotifications: boolean;
  
  // Google Maps
  googleMapsApiKey: string;
  defaultMapCenter: { lat: number; lng: number };
  defaultMapZoom: number;
  
  // Payment
  stripePublicKey: string;
  paypalClientId: string;
  
  // Firebase
  firebaseConfig: {
    apiKey: string;
    authDomain: string;
    projectId: string;
    storageBucket: string;
    messagingSenderId: string;
    appId: string;
    measurementId: string;
  };
  
  // UI
  defaultTheme: 'light' | 'dark';
  defaultLanguage: string;
  defaultPageSize: number;
  dateFormat: string;
  timeFormat: string;
  currency: string;
  currencySymbol: string;
  
  // Debug
  debugMode: boolean;
  debugRedux: boolean;
  debugQuery: boolean;
  debugWebSocket: boolean;
}

class Environment {
  private static instance: Environment;
  private config: EnvConfig;

  private constructor() {
    this.config = this.loadConfig();
  }

  static getInstance(): Environment {
    if (!Environment.instance) {
      Environment.instance = new Environment();
    }
    return Environment.instance;
  }

  private loadConfig(): EnvConfig {
    // Validate required variables
    const requiredVars = [
      'VITE_API_URL',
      'VITE_GOOGLE_MAPS_API_KEY',
      'VITE_STRIPE_PUBLIC_KEY',
    ];

    requiredVars.forEach(varName => {
      if (!import.meta.env[varName]) {
        console.warn(`Missing required environment variable: ${varName}`);
      }
    });

    return {
      // Application
      appEnv: (import.meta.env.VITE_APP_ENV as any) || 'development',
      appName: import.meta.env.VITE_APP_NAME || 'Parking Management System',
      appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0',
      appUrl: import.meta.env.VITE_APP_URL || 'http://localhost:3000',
      
      // API
      apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
      wsUrl: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',
      apiTimeout: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000'),
      apiRetryCount: parseInt(import.meta.env.VITE_API_RETRY_COUNT || '3'),
      
      // Features
      enableMockApi: import.meta.env.VITE_ENABLE_MOCK_API === 'true',
      enableAnalytics: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
      enableSentry: import.meta.env.VITE_ENABLE_SENTRY === 'true',
      enableDarkMode: import.meta.env.VITE_ENABLE_DARK_MODE !== 'false',
      enablePushNotifications: import.meta.env.VITE_ENABLE_PUSH_NOTIFICATIONS === 'true',
      
      // Google Maps
      googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '',
      defaultMapCenter: {
        lat: parseFloat(import.meta.env.VITE_DEFAULT_MAP_CENTER_LAT || '40.7128'),
        lng: parseFloat(import.meta.env.VITE_DEFAULT_MAP_CENTER_LNG || '-74.0060'),
      },
      defaultMapZoom: parseInt(import.meta.env.VITE_DEFAULT_MAP_ZOOM || '12'),
      
      // Payment
      stripePublicKey: import.meta.env.VITE_STRIPE_PUBLIC_KEY || '',
      paypalClientId: import.meta.env.VITE_PAYPAL_CLIENT_ID || '',
      
      // Firebase
      firebaseConfig: {
        apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
        authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || '',
        projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || '',
        storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || '',
        messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '',
        appId: import.meta.env.VITE_FIREBASE_APP_ID || '',
        measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || '',
      },
      
      // UI
      defaultTheme: (import.meta.env.VITE_DEFAULT_THEME as 'light' | 'dark') || 'light',
      defaultLanguage: import.meta.env.VITE_DEFAULT_LANGUAGE || 'en',
      defaultPageSize: parseInt(import.meta.env.VITE_DEFAULT_PAGE_SIZE || '20'),
      dateFormat: import.meta.env.VITE_DATE_FORMAT || 'MM/DD/YYYY',
      timeFormat: import.meta.env.VITE_TIME_FORMAT || 'hh:mm A',
      currency: import.meta.env.VITE_CURRENCY || 'USD',
      currencySymbol: import.meta.env.VITE_CURRENCY_SYMB || '$',
      
      // Debug
      debugMode: import.meta.env.VITE_DEBUG_MODE === 'true',
      debugRedux: import.meta.env.VITE_DEBUG_REDUX === 'true',
      debugQuery: import.meta.env.VITE_DEBUG_QUERY === 'true',
      debugWebSocket: import.meta.env.VITE_DEBUG_WEBSOCKET === 'true',
    };
  }

  getConfig(): EnvConfig {
    return this.config;
  }

  isDevelopment(): boolean {
    return this.config.appEnv === 'development';
  }

  isStaging(): boolean {
    return this.config.appEnv === 'staging';
  }

  isProduction(): boolean {
    return this.config.appEnv === 'production';
  }

  isTesting(): boolean {
    return this.config.appEnv === 'testing';
  }
}

export const env = Environment.getInstance();
export const config = env.getConfig();