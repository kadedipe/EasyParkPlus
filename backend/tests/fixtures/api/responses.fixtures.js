// parking-management/backend/tests/fixtures/api/responses.fixtures.js
const responseFixtures = {
  // Success responses
  success: {
    ok: { success: true, message: 'Operation successful' },
    created: { success: true, message: 'Resource created successfully' },
    updated: { success: true, message: 'Resource updated successfully' },
    deleted: { success: true, message: 'Resource deleted successfully' }
  },
  
  // Error responses
  errors: {
    badRequest: {
      success: false,
      statusCode: 400,
      message: 'Bad Request',
      errors: []
    },
    unauthorized: {
      success: false,
      statusCode: 401,
      message: 'Unauthorized',
      error: 'Authentication required'
    },
    forbidden: {
      success: false,
      statusCode: 403,
      message: 'Forbidden',
      error: 'Access denied'
    },
    notFound: {
      success: false,
      statusCode: 404,
      message: 'Not Found',
      error: 'Resource not found'
    },
    conflict: {
      success: false,
      statusCode: 409,
      message: 'Conflict',
      error: 'Resource already exists'
    },
    validation: {
      success: false,
      statusCode: 400,
      message: 'Validation Error',
      errors: [
        { field: 'email', message: 'Email is required' },
        { field: 'password', message: 'Password is too weak' }
      ]
    },
    serverError: {
      success: false,
      statusCode: 500,
      message: 'Internal Server Error',
      error: 'Something went wrong'
    },
    rateLimit: {
      success: false,
      statusCode: 429,
      message: 'Too Many Requests',
      error: 'Rate limit exceeded',
      retryAfter: 60
    }
  },
  
  // Pagination responses
  pagination: {
    firstPage: {
      data: [],
      pagination: {
        page: 1,
        limit: 10,
        total: 100,
        pages: 10,
        hasNext: true,
        hasPrev: false
      }
    },
    middlePage: {
      data: [],
      pagination: {
        page: 5,
        limit: 10,
        total: 100,
        pages: 10,
        hasNext: true,
        hasPrev: true
      }
    },
    lastPage: {
      data: [],
      pagination: {
        page: 10,
        limit: 10,
        total: 100,
        pages: 10,
        hasNext: false,
        hasPrev: true
      }
    }
  },
  
  // Auth responses
  auth: {
    loginSuccess: {
      success: true,
      data: {
        user: {
          id: '507f1f77bcf86cd799439011',
          email: 'user@example.com',
          firstName: 'John',
          lastName: 'Doe',
          role: 'user'
        },
        token: 'jwt-token-here',
        refreshToken: 'refresh-token-here',
        expiresIn: 3600
      }
    },
    registerSuccess: {
      success: true,
      data: {
        user: {
          id: '507f1f77bcf86cd799439011',
          email: 'new@example.com',
          firstName: 'New',
          lastName: 'User'
        },
        token: 'jwt-token-here'
      }
    }
  },
  
  // User responses
  user: {
    profile: {
      success: true,
      data: {
        id: '507f1f77bcf86cd799439011',
        email: 'user@example.com',
        firstName: 'John',
        lastName: 'Doe',
        phone: '+1234567890',
        role: 'user',
        createdAt: '2024-01-01T00:00:00.000Z',
        stats: {
          totalReservations: 10,
          totalSpent: 250.00,
          memberSince: '2024-01-01'
        }
      }
    },
    userList: {
      success: true,
      data: {
        users: [],
        pagination: {
          page: 1,
          limit: 10,
          total: 25
        }
      }
    }
  },
  
  // Parking spot responses
  parkingSpot: {
    single: {
      success: true,
      data: {
        id: '507f1f77bcf86cd799439012',
        name: 'A1',
        location: {
          latitude: 40.7128,
          longitude: -74.0060,
          address: '123 Main St'
        },
        type: 'standard',
        pricePerHour: 10.00,
        status: 'available',
        amenities: ['security', 'lighting']
      }
    },
    list: {
      success: true,
      data: {
        spots: [],
        pagination: {
          page: 1,
          limit: 20,
          total: 50
        }
      }
    },
    nearby: {
      success: true,
      data: {
        spots: [
          {
            id: '507f1f77bcf86cd799439012',
            name: 'A1',
            distance: 150,
            pricePerHour: 10.00
          }
        ],
        center: {
          latitude: 40.7128,
          longitude: -74.0060
        }
      }
    }
  },
  
  // Reservation responses
  reservation: {
    single: {
      success: true,
      data: {
        id: '507f1f77bcf86cd799439013',
        spotId: '507f1f77bcf86cd799439012',
        startTime: '2024-01-02T10:00:00.000Z',
        endTime: '2024-01-02T12:00:00.000Z',
        status: 'confirmed',
        totalAmount: 20.00,
        spot: {
          name: 'A1',
          location: {
            address: '123 Main St'
          }
        }
      }
    },
    list: {
      success: true,
      data: {
        reservations: [],
        pagination: {
          page: 1,
          limit: 10,
          total: 15
        }
      }
    },
    cancelled: {
      success: true,
      data: {
        id: '507f1f77bcf86cd799439013',
        status: 'cancelled',
        cancelledAt: '2024-01-01T15:00:00.000Z',
        refund: {
          amount: 20.00,
          status: 'completed'
        }
      }
    }
  },
  
  // Payment responses
  payment: {
    success: {
      success: true,
      data: {
        id: '507f1f77bcf86cd799439014',
        status: 'completed',
        transactionId: 'txn_123456',
        amount: 20.00,
        method: 'credit_card'
      }
    },
    receipt: {
      success: true,
      data: {
        id: '507f1f77bcf86cd799439014',
        transactionId: 'txn_123456',
        amount: 20.00,
        date: '2024-01-01T10:00:00.000Z',
        reservationDetails: {
          spotName: 'A1',
          startTime: '2024-01-02T10:00:00.000Z',
          endTime: '2024-01-02T12:00:00.000Z'
        }
      }
    }
  }
};

module.exports = responseFixtures;