markdown
# 🅿️ Parking Management System - Frontend

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![React](https://img.shields.io/badge/react-18.2.0-61DAFB.svg)
![TypeScript](https://img.shields.io/badge/typescript-5.2.2-3178C6.svg)
![Vite](https://img.shields.io/badge/vite-5.0.0-646CFF.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Coverage](https://img.shields.io/badge/coverage-80%25-yellow.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)

**Modern, responsive web application for parking management**  
Built with React, TypeScript, and Material-UI

[Live Demo](https://parking.example.com) •
[Documentation](https://docs.parking.example.com) •
[API Reference](https://api.parking.example.com/docs)

</div>

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Pages & Components](#-pages--components)
- [State Management](#-state-management)
- [API Integration](#-api-integration)
- [Styling](#-styling)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Performance](#-performance)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)

---

## ✨ Features

### 👤 User Features
- **🔐 Authentication**
  - User registration & login
  - Social login (Google, Facebook, Apple)
  - Multi-factor authentication
  - Password reset flow
  - Session management

- **🚗 Vehicle Management**
  - Add/remove vehicles
  - Set default vehicle
  - Vehicle details (make, model, license plate)
  - Multiple vehicle types

- **📅 Reservations**
  - Search available parking spots
  - Real-time availability
  - Book parking spots
  - Modify/cancel reservations
  - Reservation history
  - Check-in/check-out QR codes

- **💰 Payments**
  - Secure payment processing
  - Multiple payment methods
  - Payment history
  - Digital receipts
  - Refund requests

- **👤 Profile Management**
  - Personal information
  - Notification preferences
  - Payment methods
  - Account settings

### 🅿️ Parking Features
- **🗺️ Interactive Map**
  - Real-time spot availability
  - Spot details on hover
  - Filter by spot type
  - Directions to spots

- **🔍 Smart Search**
  - Filter by location, price, type
  - Sort by distance, price, rating
  - Advanced filters
  - Save searches

- **⭐ Reviews & Ratings**
  - Rate parking spots
  - Leave reviews
  - View spot ratings
  - Upload photos

### 👨‍💼 Admin Features
- **📊 Dashboard**
  - Real-time occupancy
  - Revenue analytics
  - User statistics
  - System health

- **🅿️ Spot Management**
  - Add/remove spots
  - Update spot details
  - Set dynamic pricing
  - Maintenance scheduling

- **👥 User Management**
  - View users
  - Manage roles
  - Handle disputes
  - View audit logs

- **📈 Reports**
  - Revenue reports
  - Occupancy reports
  - User activity reports
  - Export data

### 🎨 UI/UX Features
- **📱 Responsive Design**
  - Mobile-first approach
  - Tablet & desktop optimized
  - Touch-friendly interactions

- **🌓 Dark Mode**
  - Light/dark theme toggle
  - System preference detection
  - Persistent preference

- **🌐 Internationalization**
  - Multi-language support
  - RTL support
  - Date/time localization
  - Currency formatting

- **♿ Accessibility**
  - WCAG 2.1 AA compliant
  - Screen reader friendly
  - Keyboard navigation
  - High contrast mode

---

## 🛠 Tech Stack

### Core Framework
| Technology | Version | Purpose |
|------------|---------|---------|
| [React](https://react.dev/) | 18.2.0 | UI library |
| [TypeScript](https://www.typescriptlang.org/) | 5.2.2 | Type safety |
| [Vite](https://vitejs.dev/) | 5.0.0 | Build tool |
| [React Router](https://reactrouter.com/) | 6.20.0 | Routing |

### UI Library
| Technology | Version | Purpose |
|------------|---------|---------|
| [Material-UI](https://mui.com/) | 5.14.0 | Component library |
| [Emotion](https://emotion.sh/) | 11.11.0 | CSS-in-JS |
| [React Hook Form](https://react-hook-form.com/) | 7.48.0 | Form handling |
| [Zod](https://zod.dev/) | 3.22.0 | Validation |

### State Management
| Technology | Version | Purpose |
|------------|---------|---------|
| [Zustand](https://zustand-demo.pmnd.rs/) | 4.4.0 | Global state |
| [React Query](https://tanstack.com/query/latest) | 5.12.0 | Server state |
| [Zustand Middleware](https://github.com/pmndrs/zustand) | 4.4.0 | Persist, devtools |

### API & Data Fetching
| Technology | Version | Purpose |
|------------|---------|---------|
| [Axios](https://axios-http.com/) | 1.6.0 | HTTP client |
| [React Query](https://tanstack.com/query/latest) | 5.12.0 | Data fetching |
| [WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket) | - | Real-time updates |
| [Socket.io-client](https://socket.io/) | 4.5.0 | WebSocket client |

### Maps & Location
| Technology | Version | Purpose |
|------------|---------|---------|
| [Google Maps React](https://visgl.github.io/react-google-maps/) | 2.19.0 | Interactive maps |
| [Mapbox GL](https://docs.mapbox.com/mapbox-gl-js/) | 3.0.0 | Alternative maps |
| [Geolocation API](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API) | - | User location |

### Forms & Validation
| Technology | Version | Purpose |
|------------|---------|---------|
| [React Hook Form](https://react-hook-form.com/) | 7.48.0 | Form management |
| [Zod](https://zod.dev/) | 3.22.0 | Schema validation |
| [Yup](https://github.com/jquense/yup) | 1.3.0 | Alternative validation |

### UI Components
| Technology | Version | Purpose |
|------------|---------|---------|
| [Material-UI](https://mui.com/) | 5.14.0 | Core components |
| [MUI X](https://mui.com/x/) | 6.18.0 | Data grid, charts |
| [React DatePicker](https://reactdatepicker.com/) | 5.0.0 | Date selection |
| [React Select](https://react-select.com/) | 5.8.0 | Advanced select |
| [React Dropzone](https://react-dropzone.js.org/) | 14.2.0 | File upload |

### Charts & Visualizations
| Technology | Version | Purpose |
|------------|---------|---------|
| [Recharts](https://recharts.org/) | 2.10.0 | Charts |
| [Victory](https://formidable.com/open-source/victory/) | 36.0.0 | Alternative charts |
| [React Circular Progressbar](https://www.npmjs.com/package/react-circular-progressbar) | 2.1.0 | Progress indicators |

### Testing
| Technology | Version | Purpose |
|------------|---------|---------|
| [Jest](https://jestjs.io/) | 29.7.0 | Unit testing |
| [React Testing Library](https://testing-library.com/react) | 14.1.0 | Component testing |
| [Cypress](https://www.cypress.io/) | 13.6.0 | E2E testing |
| [MSW](https://mswjs.io/) | 2.0.0 | API mocking |

### Code Quality
| Technology | Version | Purpose |
|------------|---------|---------|
| [ESLint](https://eslint.org/) | 8.55.0 | Linting |
| [Prettier](https://prettier.io/) | 3.1.0 | Formatting |
| [Husky](https://typicode.github.io/husky/) | 8.0.0 | Git hooks |
| [lint-staged](https://github.com/okonet/lint-staged) | 15.2.0 | Staged files |

---

## 🏗 Architecture

### Application Architecture

```mermaid
graph TB
    subgraph Browser[Browser]
        Router[React Router]
        Pages[Page Components]
        Components[UI Components]
        Store[State Management]
        Hooks[Custom Hooks]
        Services[API Services]
    end
    
    subgraph CDN[CDN / Static Hosting]
        Assets[Static Assets]
        Build[Build Files]
    end
    
    subgraph Backend[Backend Services]
        API[REST API]
        WS[WebSocket]
        Auth[Auth Service]
    end
    
    Router --> Pages
    Pages --> Components
    Pages --> Store
    Pages --> Hooks
    Hooks --> Services
    Services --> API
    Services --> WS
    Store --> Services
    
    Browser --> CDN
    Browser --> Backend
Component Architecture


























Data Flow















🚀 Quick Start
Prerequisites
Node.js 18+

npm 9+ or yarn 1.22+

Git

Installation
Clone the repository

bash
git clone https://github.com/yourusername/parking-management.git
cd parking-management/frontend
Install dependencies

bash
npm install
# or
yarn install
Set up environment variables

bash
cp .env.example .env.local
# Edit .env.local with your configuration
Start development server

bash
npm run dev
# or
yarn dev
Open browser

text
http://localhost:3000
Docker Setup
bash
# Build image
docker build -t parking-frontend .

# Run container
docker run -p 3000:3000 parking-frontend

# With docker-compose
docker-compose up -d
Available Scripts
bash
# Development
npm run dev          # Start dev server
npm run preview      # Preview production build

# Building
npm run build        # Build for production
npm run build:analyze # Build with bundle analyzer

# Testing
npm run test         # Run tests
npm run test:watch   # Run tests in watch mode
npm run test:coverage # Run tests with coverage
npm run test:e2e     # Run E2E tests
npm run test:e2e:ui  # Run E2E tests with UI

# Linting & Formatting
npm run lint         # Run ESLint
npm run lint:fix     # Fix ESLint issues
npm run format       # Run Prettier
npm run format:check # Check formatting
npm run type-check   # Run TypeScript checks

# Code Generation
npm run generate:component # Generate new component
npm run generate:page      # Generate new page
npm run generate:hook      # Generate new hook

# Cleanup
npm run clean        # Clean build artifacts
npm run clean:all    # Clean everything (including node_modules)
📁 Project Structure
text
frontend/
├── public/                      # Static assets
│   ├── favicon.ico
│   ├── logo.svg
│   ├── manifest.json
│   └── robots.txt
│
├── src/
│   ├── assets/                  # Assets (images, fonts, etc.)
│   │   ├── images/
│   │   ├── fonts/
│   │   └── icons/
│   │
│   ├── components/               # Reusable components
│   │   ├── common/               # Common UI components
│   │   │   ├── Button/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Button.test.tsx
│   │   │   │   └── Button.module.css
│   │   │   ├── Input/
│   │   │   ├── Modal/
│   │   │   ├── Card/
│   │   │   └── Table/
│   │   │
│   │   ├── layout/               # Layout components
│   │   │   ├── Header/
│   │   │   ├── Footer/
│   │   │   ├── Sidebar/
│   │   │   └── Navigation/
│   │   │
│   │   └── features/             # Feature-specific components
│   │       ├── parking/
│   │       │   ├── ParkingMap/
│   │       │   ├── SpotCard/
│   │       │   └── AvailabilityCalendar/
│   │       ├── reservation/
│   │       │   ├── ReservationForm/
│   │       │   └── ReservationList/
│   │       ├── payment/
│   │       │   ├── PaymentForm/
│   │       │   └── PaymentHistory/
│   │       └── user/
│   │           ├── LoginForm/
│   │           ├── RegisterForm/
│   │           └── ProfileForm/
│   │
│   ├── pages/                    # Page components
│   │   ├── Home/
│   │   │   ├── HomePage.tsx
│   │   │   └── HomePage.test.tsx
│   │   ├── Search/
│   │   ├── Reservation/
│   │   ├── Dashboard/
│   │   ├── Profile/
│   │   ├── Admin/
│   │   ├── Auth/
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   └── NotFound/
│   │
│   ├── hooks/                    # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useReservation.ts
│   │   ├── usePayment.ts
│   │   ├── useWebSocket.ts
│   │   ├── useLocalStorage.ts
│   │   └── useMediaQuery.ts
│   │
│   ├── services/                 # API services
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── auth.ts
│   │   │   ├── parking.ts
│   │   │   ├── reservation.ts
│   │   │   ├── payment.ts
│   │   │   └── user.ts
│   │   ├── websocket/
│   │   │   └── index.ts
│   │   └── notifications/
│   │       └── index.ts
│   │
│   ├── store/                    # State management
│   │   ├── auth.store.ts
│   │   ├── parking.store.ts
│   │   ├── reservation.store.ts
│   │   ├── ui.store.ts
│   │   └── index.ts
│   │
│   ├── contexts/                  # React contexts
│   │   ├── AuthContext.tsx
│   │   ├── ThemeContext.tsx
│   │   └── NotificationContext.tsx
│   │
│   ├── utils/                     # Utility functions
│   │   ├── format.ts
│   │   ├── validation.ts
│   │   ├── date.ts
│   │   ├── currency.ts
│   │   └── helpers.ts
│   │
│   ├── types/                     # TypeScript type definitions
│   │   ├── api.types.ts
│   │   ├── models.types.ts
│   │   ├── forms.types.ts
│   │   └── index.ts
│   │
│   ├── config/                    # Configuration files
│   │   ├── routes.ts
│   │   ├── api.config.ts
│   │   └── theme.config.ts
│   │
│   ├── styles/                    # Global styles
│   │   ├── globals.css
│   │   ├── variables.css
│   │   └── themes/
│   │       ├── light.ts
│   │       └── dark.ts
│   │
│   ├── App.tsx                    # Main App component
│   ├── App.test.tsx               # App tests
│   ├── main.tsx                   # Entry point
│   ├── vite-env.d.ts              # Vite environment types
│   └── index.html                 # HTML template
│
├── tests/                          # Test files
│   ├── unit/
│   ├── integration/
│   └── e2e/
│       └── cypress/
│
├── scripts/                        # Build scripts
│   └── generate.js
│
├── .env.example                    # Environment variables example
├── .eslintrc.js                    # ESLint configuration
├── .prettierrc                     # Prettier configuration
├── .husky/                         # Husky git hooks
├── vite.config.ts                  # Vite configuration
├── tsconfig.json                   # TypeScript configuration
├── package.json                    # Dependencies
└── README.md                       # This file
⚙️ Configuration
Environment Variables
Variable	Description	Default	Required
VITE_API_URL	Backend API URL	http://localhost:8000	Yes
VITE_WS_URL	WebSocket URL	ws://localhost:8000	Yes
VITE_GOOGLE_MAPS_API_KEY	Google Maps API key	-	Yes
VITE_STRIPE_PUBLIC_KEY	Stripe publishable key	-	Yes
VITE_FIREBASE_API_KEY	Firebase API key	-	No
VITE_APP_NAME	Application name	Parking Management	No
VITE_APP_VERSION	Application version	1.0.0	No
VITE_SENTRY_DSN	Sentry DSN for error tracking	-	No
VITE_ANALYTICS_ID	Google Analytics ID	-	No
VITE_ENABLE_MOCK_API	Enable mock API	false	No
Theme Configuration
typescript
// src/config/theme.config.ts
export const lightTheme = {
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#9c27b0',
      light: '#ba68c8',
      dark: '#7b1fa2',
    },
    success: {
      main: '#2e7d32',
      light: '#4caf50',
      dark: '#1b5e20',
    },
    error: {
      main: '#d32f2f',
      light: '#ef5350',
      dark: '#c62828',
    },
    warning: {
      main: '#ed6c02',
      light: '#ff9800',
      dark: '#e65100',
    },
    info: {
      main: '#0288d1',
      light: '#03a9f4',
      dark: '#01579b',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontSize: '2.5rem', fontWeight: 500 },
    h2: { fontSize: '2rem', fontWeight: 500 },
    h3: { fontSize: '1.75rem', fontWeight: 500 },
    body1: { fontSize: '1rem' },
    body2: { fontSize: '0.875rem' },
  },
  spacing: 8,
  shape: {
    borderRadius: 4,
  },
};
Route Configuration
typescript
// src/config/routes.ts
export const ROUTES = {
  HOME: '/',
  SEARCH: '/search',
  RESERVATION: '/reservation/:id',
  DASHBOARD: '/dashboard',
  PROFILE: '/profile',
  SETTINGS: '/settings',
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  VERIFY_EMAIL: '/verify-email',
  ADMIN: {
    DASHBOARD: '/admin',
    USERS: '/admin/users',
    SPOTS: '/admin/spots',
    REPORTS: '/admin/reports',
    SETTINGS: '/admin/settings',
  },
} as const;
📱 Pages & Components
Authentication Pages
Page	Route	Description
Login	/login	User login with email/password or social
Register	/register	New user registration
Forgot Password	/forgot-password	Request password reset
Reset Password	/reset-password	Set new password
Verify Email	/verify-email	Email verification
Public Pages
Page	Route	Description
Home	/	Landing page with search
Search	/search	Search and filter parking spots
Spot Details	/spots/:id	Detailed spot information
Protected Pages
Page	Route	Description
Dashboard	/dashboard	User dashboard
My Reservations	/reservations	View/manage reservations
New Reservation	/reservations/new	Create reservation
Reservation Details	/reservations/:id	View reservation details
Profile	/profile	User profile
Payment Methods	/payment-methods	Manage payment methods
Vehicles	/vehicles	Manage vehicles
Notifications	/notifications	View notifications
Admin Pages
Page	Route	Description
Admin Dashboard	/admin	Admin overview
User Management	/admin/users	Manage users
Spot Management	/admin/spots	Manage parking spots
Reports	/admin/reports	View reports
System Settings	/admin/settings	Configure system
Key Components
ParkingMap Component
tsx
import { ParkingMap } from '@/components/features/parking/ParkingMap';

<ParkingMap
  spots={spots}
  center={userLocation}
  zoom={15}
  onSpotClick={handleSpotClick}
  selectedSpot={selectedSpot}
  showFilters={true}
/>
SpotCard Component
tsx
import { SpotCard } from '@/components/features/parking/SpotCard';

<SpotCard
  spot={spot}
  onReserve={handleReserve}
  onViewDetails={handleViewDetails}
  showPrice={true}
  showAvailability={true}
/>
ReservationForm Component
tsx
import { ReservationForm } from '@/components/features/reservation/ReservationForm';

<ReservationForm
  spotId={spotId}
  onSubmit={handleSubmit}
  initialData={initialData}
  minDate={new Date()}
  maxDate={addDays(new Date(), 30)}
/>
🗃️ State Management
Global State (Zustand)
typescript
// src/store/auth.store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      
      login: async (credentials) => {
        const response = await api.auth.login(credentials);
        set({ user: response.user, token: response.token, isAuthenticated: true });
      },
      
      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
        localStorage.removeItem('auth-storage');
      },
      
      refreshToken: async () => {
        const response = await api.auth.refreshToken();
        set({ token: response.token });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token }),
    }
  )
);
Server State (React Query)
typescript
// src/hooks/useReservation.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

export const useReservations = (filters?: ReservationFilters) => {
  return useQuery({
    queryKey: ['reservations', filters],
    queryFn: () => api.reservations.getList(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useCreateReservation = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateReservationData) => api.reservations.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reservations'] });
      queryClient.invalidateQueries({ queryKey: ['spots'] });
    },
  });
};
Local State (React Hooks)
typescript
// src/hooks/useSearchFilters.ts
import { useState, useCallback } from 'react';

export const useSearchFilters = (initialFilters?: SearchFilters) => {
  const [filters, setFilters] = useState<SearchFilters>(initialFilters || {
    spotType: 'all',
    priceRange: [0, 100],
    distance: 5,
    features: [],
  });
  
  const updateFilter = useCallback((key: keyof SearchFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);
  
  const resetFilters = useCallback(() => {
    setFilters({
      spotType: 'all',
      priceRange: [0, 100],
      distance: 5,
      features: [],
    });
  }, []);
  
  return { filters, updateFilter, resetFilters };
};
🌐 API Integration
API Client
typescript
// src/services/api/client.ts
import axios from 'axios';
import { useAuthStore } from '@/store/auth.store';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        await useAuthStore.getState().refreshToken();
        return apiClient(originalRequest);
      } catch {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
API Service Modules
typescript
// src/services/api/parking.ts
import apiClient from './client';
import { ParkingSpot, SearchFilters } from '@/types';

export const parkingApi = {
  getSpots: (filters?: SearchFilters) => 
    apiClient.get<ParkingSpot[]>('/parking/spots', { params: filters }),
    
  getSpotById: (id: string) => 
    apiClient.get<ParkingSpot>(`/parking/spots/${id}`),
    
  checkAvailability: (spotId: string, date: Date) => 
    apiClient.get<boolean>(`/parking/spots/${spotId}/availability`, { params: { date } }),
    
  getNearbySpots: (lat: number, lng: number, radius: number) =>
    apiClient.get<ParkingSpot[]>('/parking/nearby', { params: { lat, lng, radius } }),
};
React Query Hooks
typescript
// src/hooks/useParkingSpots.ts
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { parkingApi } from '@/services/api/parking';

export const useParkingSpots = (filters?: SearchFilters) => {
  return useQuery({
    queryKey: ['parkingSpots', filters],
    queryFn: () => parkingApi.getSpots(filters),
    staleTime: 60 * 1000, // 1 minute
  });
};

export const useInfiniteParkingSpots = (filters?: SearchFilters) => {
  return useInfiniteQuery({
    queryKey: ['parkingSpots', 'infinite', filters],
    queryFn: ({ pageParam = 1 }) => 
      parkingApi.getSpots({ ...filters, page: pageParam, limit: 20 }),
    getNextPageParam: (lastPage, pages) => 
      lastPage.hasNextPage ? pages.length + 1 : undefined,
    initialPageParam: 1,
  });
};
WebSocket Integration
typescript
// src/services/websocket/index.ts
import { io, Socket } from 'socket.io-client';
import { useAuthStore } from '@/store/auth.store';

class WebSocketService {
  private socket: Socket | null = null;
  
  connect() {
    const token = useAuthStore.getState().token;
    
    this.socket = io(import.meta.env.VITE_WS_URL, {
      auth: { token },
      transports: ['websocket'],
    });
    
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
    });
    
    this.socket.on('spot-update', (data) => {
      // Handle spot update
    });
    
    this.socket.on('reservation-update', (data) => {
      // Handle reservation update
    });
    
    this.socket.on('notification', (data) => {
      // Handle notification
    });
  }
  
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
  
  subscribeToSpot(spotId: string) {
    this.socket?.emit('subscribe-spot', { spotId });
  }
  
  unsubscribeFromSpot(spotId: string) {
    this.socket?.emit('unsubscribe-spot', { spotId });
  }
}

export const wsService = new WebSocketService();
🎨 Styling
CSS-in-JS with Emotion
tsx
// src/components/common/Button/Button.tsx
import styled from '@emotion/styled';
import { css } from '@emotion/react';

interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'small' | 'medium' | 'large';
  fullWidth?: boolean;
}

const Button = styled.button<ButtonProps>`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
  
  ${({ variant = 'primary' }) => variant === 'primary' && css`
    background-color: #1976d2;
    color: white;
    
    &:hover {
      background-color: #1565c0;
    }
    
    &:disabled {
      background-color: #ccc;
      cursor: not-allowed;
    }
  `}
  
  ${({ variant = 'primary' }) => variant === 'secondary' && css`
    background-color: #9c27b0;
    color: white;
    
    &:hover {
      background-color: #7b1fa2;
    }
  `}
  
  ${({ size = 'medium' }) => size === 'small' && css`
    padding: 6px 12px;
    font-size: 0.875rem;
  `}
  
  ${({ size = 'medium' }) => size === 'medium' && css`
    padding: 8px 16px;
    font-size: 1rem;
  `}
  
  ${({ size = 'medium' }) => size === 'large' && css`
    padding: 12px 24px;
    font-size: 1.125rem;
  `}
  
  ${({ fullWidth }) => fullWidth && css`
    width: 100%;
  `}
`;

export default Button;
Theme Provider
tsx
// src/contexts/ThemeContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import { lightTheme, darkTheme } from '@/config/theme.config';

type ThemeMode = 'light' | 'dark';

interface ThemeContextType {
  mode: ThemeMode;
  toggleTheme: () => void;
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('theme-mode');
    if (saved === 'light' || saved === 'dark') return saved;
    
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  
  useEffect(() => {
    localStorage.setItem('theme-mode', mode);
  }, [mode]);
  
  const toggleTheme = () => {
    setMode(prev => prev === 'light' ? 'dark' : 'light');
  };
  
  const theme = mode === 'light' ? lightTheme : darkTheme;
  
  return (
    <ThemeContext.Provider value={{ mode, toggleTheme, setMode }}>
      <MuiThemeProvider theme={theme}>
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};
Global Styles
css
/* src/styles/globals.css */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  line-height: 1.5;
  overflow-x: hidden;
}

a {
  color: inherit;
  text-decoration: none;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #555;
}
🧪 Testing
Unit Tests (Jest + React Testing Library)
tsx
// src/components/common/Button/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import Button from './Button';

describe('Button', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });
  
  it('handles click events', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
  
  it('can be disabled', () => {
    render(<Button disabled>Click me</Button>);
    
    expect(screen.getByText('Click me')).toBeDisabled();
  });
  
  it('applies variant classes', () => {
    const { rerender } = render(<Button variant="primary">Primary</Button>);
    expect(screen.getByText('Primary')).toHaveStyle({
      backgroundColor: '#1976d2',
    });
    
    rerender(<Button variant="secondary">Secondary</Button>);
    expect(screen.getByText('Secondary')).toHaveStyle({
      backgroundColor: '#9c27b0',
    });
  });
});
Component Tests
tsx
// src/components/features/parking/SpotCard/SpotCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import SpotCard from './SpotCard';

const mockSpot = {
  id: '1',
  spotNumber: 'A12',
  spotType: 'standard',
  price: 5.0,
  isAvailable: true,
  location: { lat: 40.7128, lng: -74.0060 },
};

describe('SpotCard', () => {
  it('displays spot information', () => {
    render(<SpotCard spot={mockSpot} />);
    
    expect(screen.getByText('A12')).toBeInTheDocument();
    expect(screen.getByText('$5.00')).toBeInTheDocument();
    expect(screen.getByText('Standard')).toBeInTheDocument();
  });
  
  it('shows availability badge', () => {
    render(<SpotCard spot={mockSpot} />);
    
    expect(screen.getByText('Available')).toBeInTheDocument();
    expect(screen.getByText('Available')).toHaveStyle({
      color: '#2e7d32',
    });
  });
  
  it('calls onReserve when button clicked', () => {
    const onReserve = jest.fn();
    render(<SpotCard spot={mockSpot} onReserve={onReserve} />);
    
    fireEvent.click(screen.getByText('Reserve'));
    expect(onReserve).toHaveBeenCalledWith(mockSpot.id);
  });
});
Integration Tests
tsx
// src/pages/Search/SearchPage.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import SearchPage from './SearchPage';
import { server } from '@/tests/mocks/server';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

describe('SearchPage', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
  
  it('loads and displays parking spots', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SearchPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
    
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText('A12')).toBeInTheDocument();
      expect(screen.getByText('B34')).toBeInTheDocument();
    });
  });
  
  it('filters spots by type', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SearchPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
    
    await waitFor(() => {
      fireEvent.change(screen.getByLabelText('Spot Type'), {
        target: { value: 'vip' },
      });
      
      expect(screen.getByText('VIP Spot')).toBeInTheDocument();
      expect(screen.queryByText('Standard Spot')).not.toBeInTheDocument();
    });
  });
});
E2E Tests (Cypress)
typescript
// tests/e2e/cypress/e2e/reservation.cy.ts
describe('Reservation Flow', () => {
  beforeEach(() => {
    cy.intercept('GET', '/api/v1/parking/spots', { fixture: 'spots.json' }).as('getSpots');
    cy.intercept('POST', '/api/v1/auth/login', { fixture: 'login.json' }).as('login');
    cy.intercept('POST', '/api/v1/reservations', { fixture: 'reservation.json' }).as('createReservation');
    
    cy.visit('/');
  });
  
  it('completes a reservation successfully', () => {
    // Login
    cy.get('[data-testid="login-button"]').click();
    cy.get('[data-testid="email-input"]').type('user@example.com');
    cy.get('[data-testid="password-input"]').type('password123');
    cy.get('[data-testid="submit-login"]').click();
    
    cy.wait('@login');
    
    // Search for spot
    cy.get('[data-testid="search-input"]').type('Downtown');
    cy.get('[data-testid="search-button"]').click();
    
    cy.wait('@getSpots');
    
    // Select spot
    cy.get('[data-testid="spot-card-A12"]').click();
    cy.get('[data-testid="reserve-button"]').click();
    
    // Fill reservation form
    cy.get('[data-testid="start-time"]').type('2024-01-20T10:00');
    cy.get('[data-testid="end-time"]').type('2024-01-20T12:00');
    cy.get('[data-testid="vehicle-select"]').select('Toyota Camry');
    cy.get('[data-testid="submit-reservation"]').click();
    
    cy.wait('@createReservation');
    
    // Verify success
    cy.get('[data-testid="success-message"]').should('contain', 'Reservation confirmed');
    cy.url().should('include', '/reservations/');
  });
});
🚢 Deployment
Build for Production
bash
# Create production build
npm run build

# Preview production build
npm run preview

# Build with bundle analysis
npm run build:analyze
Environment-Specific Builds
bash
# Development
npm run build -- --mode development

# Staging
npm run build -- --mode staging

# Production
npm run build -- --mode production
Docker Deployment
dockerfile
# Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
Nginx Configuration
nginx
# nginx.conf
server {
    listen 80;
    server_name parking.example.com;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Content-Type-Options "nosniff";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;";

    # Cache static assets
    location /assets {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (optional)
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
CI/CD Pipeline (GitHub Actions)
yaml
# .github/workflows/deploy.yml
name: Deploy Frontend

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Lint
        run: npm run lint
      
      - name: Type check
        run: npm run type-check
      
      - name: Test
        run: npm run test:ci
      
      - name: Build
        run: npm run build
        env:
          VITE_API_URL: ${{ secrets.VITE_API_URL }}
          VITE_GOOGLE_MAPS_API_KEY: ${{ secrets.VITE_GOOGLE_MAPS_API_KEY }}
      
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: frontend/dist

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: build
          path: dist
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
          working-directory: ./dist
⚡ Performance
Optimization Techniques
Code Splitting

tsx
// Lazy load routes
const SearchPage = lazy(() => import('@/pages/Search/SearchPage'));
const DashboardPage = lazy(() => import('@/pages/Dashboard/DashboardPage'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/search" element={<SearchPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </Suspense>
  );
}
Image Optimization

tsx
import { Img } from 'react-image';

<Img
  src={[imageUrl, fallbackImage]}
  loader={<Skeleton variant="rectangular" width={300} height={200} />}
  unloader={<img src="/placeholder.jpg" alt="fallback" />}
  alt="Parking spot"
/>
Virtual Lists

tsx
import { FixedSizeList as List } from 'react-window';

const Row = ({ index, style }) => (
  <div style={style}>
    <SpotCard spot={spots[index]} />
  </div>
);

<List
  height={600}
  itemCount={spots.length}
  itemSize={200}
  width="100%"
>
  {Row}
</List>
Memoization

tsx
const SpotCard = memo(({ spot, onReserve }) => {
  // Component logic
}, (prevProps, nextProps) => {
  return prevProps.spot.id === nextProps.spot.id &&
         prevProps.spot.isAvailable === nextProps.spot.isAvailable;
});
Debouncing

tsx
import { useDebounce } from 'use-debounce';

const SearchInput = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm] = useDebounce(searchTerm, 500);
  
  useEffect(() => {
    if (debouncedSearchTerm) {
      searchSpots(debouncedSearchTerm);
    }
  }, [debouncedSearchTerm]);
  
  return (
    <input
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
    />
  );
};
Performance Metrics
Metric	Target	Current
First Contentful Paint (FCP)	< 1.5s	1.2s
Largest Contentful Paint (LCP)	< 2.5s	2.1s
Time to Interactive (TTI)	< 3.5s	2.8s
Total Blocking Time (TBT)	< 300ms	150ms
Cumulative Layout Shift (CLS)	< 0.1	0.05
First Input Delay (FID)	< 100ms	45ms
Bundle Size Analysis
bash
# Run bundle analyzer
npm run build:analyze

# Results:
# - Total bundle size: 245 KB (gzipped)
# - Main chunk: 85 KB
# - Vendor chunk: 120 KB
# - Async chunks: 40 KB
🤝 Contributing
We welcome contributions! Please see our Contributing Guide.

Development Workflow
Fork the repository

Create a feature branch (git checkout -b feature/amazing-feature)

Commit changes (git commit -m 'feat: add amazing feature')

Push to branch (git push origin feature/amazing-feature)

Open a Pull Request

Code Style
Follow Airbnb JavaScript Style Guide

Use Conventional Commits

Write meaningful commit messages

Add tests for new features

Update documentation

Commit Convention
text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
Types: feat, fix, docs, style, refactor, perf, test, chore

Examples:

feat: add parking spot search functionality

fix: resolve payment processing error

docs: update API documentation

style: format code with prettier

refactor: simplify reservation form logic

Pull Request Process
Update the README.md with details of changes

Update the CHANGELOG.md with details of changes

The PR will be merged once you have the sign-off of two maintainers

📄 License
This project is licensed under the MIT License - see the LICENSE.txt file for details.

📞 Contact
Project Lead: lead@parking.example.com

Frontend Team: frontend@parking.example.com

Documentation: https://docs.parking.example.com

Issue Tracker: GitHub Issues

🙏 Acknowledgments
React - UI library

Material-UI - Component library

React Query - Data fetching

Zustand - State management

All our contributors

📊 Roadmap
Version 1.1.0 (Q2 2024)
Mobile app (React Native)

Push notifications

Offline mode

Advanced analytics dashboard

Version 1.2.0 (Q3 2024)
AI-powered parking recommendations

Voice search

AR navigation to spots

Integration with smart parking sensors

Version 2.0.0 (Q1 2025)
Multi-language support (i18n)

White-label solution

API marketplace

Blockchain payments

<div align="center"> <sub>Built with ❤️ by the Parking Management Team</sub> <br> <sub>© 2024 Parking Management System. All rights reserved.</sub> <br> <sub>Made with React ⚛️ and TypeScript 🔷</sub> </div> ```
This comprehensive README.md provides:

Key Features:
1. Project Overview
Badges for version, React, TypeScript, Vite, license, coverage

Feature highlights

Quick navigation

2. Detailed Feature List
User Features (authentication, vehicle management, reservations, payments)

Parking Features (interactive map, smart search, reviews)

Admin Features (dashboard, spot management, user management, reports)

UI/UX Features (responsive design, dark mode, i18n, accessibility)

3. Tech Stack Tables
Core Framework

UI Library

State Management

API & Data Fetching

Maps & Location

Forms & Validation

UI Components

Charts & Visualizations

Testing

Code Quality

4. Architecture Diagrams
Application architecture (Mermaid)

Component architecture

Data flow diagram

5. Quick Start Guide
Prerequisites

Installation steps

Docker setup

Available scripts

6. Project Structure
Detailed directory tree

Explanation of each folder

7. Configuration
Environment variables table

Theme configuration example

Route configuration

8. Pages & Components
Authentication pages

Public pages

Protected pages

Admin pages

Key component examples

9. State Management
Global state with Zustand (code example)

Server state with React Query (code example)

Local state with hooks (code example)

10. API Integration
API client with interceptors

Service modules

React Query hooks

WebSocket integration

11. Styling
CSS-in-JS with Emotion (code example)

Theme provider

Global styles

12. Testing
Unit tests with Jest + RTL (code example)

Component tests

Integration tests

E2E tests with Cypress

13. Deployment
Build commands

Docker deployment

Nginx configuration

CI/CD pipeline (GitHub Actions)

14. Performance
Optimization techniques (code examples)

Performance metrics table

Bundle size analysis

15. Contributing
Development workflow

Code style

Commit convention

PR process

16. Roadmap
Upcoming features by version

This README serves as a comprehensive documentation hub for developers working on the parking management system frontend.