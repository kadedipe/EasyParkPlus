
## 2. **authentication.md** - Authentication API

```markdown
# Authentication API

## Overview
Authentication is required for all API endpoints. The system uses JWT (JSON Web Tokens) for authentication.

## Endpoints

### Login
Authenticate and obtain a JWT token.

**POST** `/auth/login`

**Request Body:**
```json
{
  "email": "string",
  "password": "string",
  "remember_me": "boolean"
}