# Multi-User Authentication System

## Overview
The Platinum Tier dashboard now supports multi-user authentication with role-based access control. This system allows multiple users to access the dashboard with different permission levels.

## User Roles

### Admin
- Full access to all dashboard features
- Can create and manage users
- Can view all data and sections
- Has administrative privileges

### Approver
- Can view most dashboard sections
- Can approve tasks
- Can view financial and operational data
- Cannot create new users

### Viewer
- Limited access to dashboard features
- Can only see basic status information
- Cannot access system health, financial data, or logs
- Read-only access to pending tasks

## How Roles Work

The role-based access system works as follows:

1. **Authentication**: Users must log in with username and password
2. **Session Management**: Flask-Login manages user sessions
3. **Role Checking**: Each request is checked for appropriate role permissions
4. **Content Filtering**: Different dashboard sections are shown/hidden based on roles

### Role-Specific Access:

- **Viewer Role**:
  - Can see: AI Employee Status, Watchers Status, Pending Tasks
  - Cannot see: System Health, Financial Data, Social Posts, Predictive Insights, Live Logs

- **Approver Role**:
  - Can see: All sections that Viewer can see, plus Financial Data, Social Posts, Predictive Insights

- **Admin Role**:
  - Can see: All dashboard sections plus user management capabilities

## Bcrypt Password Storage

### Why Bcrypt?
Bcrypt is used for password hashing because:
- It's a secure, one-way hashing algorithm
- It includes salt to prevent rainbow table attacks
- It's adaptive, meaning it can be made more computationally expensive over time
- It's widely accepted as the standard for password storage

### Storage Location
User credentials are stored in `vault/Users.json` with the following format:
```json
{
  "user_id": {
    "username": "username",
    "password": "$2b$12$...", // bcrypt hashed password
    "role": "Admin|Approver|Viewer"
  }
}
```

## API Endpoints

### Authentication Endpoints
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /logout` - Logout user
- `GET /` - Main dashboard (requires login)

### User Management Endpoints
- `GET /api/users` - Get user list (Admin/Approver only)
- `POST /api/users` - Create new user (Admin only)

### Role Checking Endpoints
- `GET /api/user` - Get current user info
- `GET /api/check_role/<role>` - Check user role permissions

## Security Features

1. **Password Security**: All passwords are hashed using bcrypt
2. **Session Security**: Session-based authentication with Flask-Login
3. **Role Validation**: Each request validates user permissions
4. **Input Validation**: All user inputs are validated
5. **Data Protection**: Sensitive data is filtered based on roles

## Adding New Users

Administrators can create new users through the API or by directly editing the Users.json file to add new entries with bcrypt-hashed passwords.

## Testing the System

1. Start the dashboard: `python dashboard.py`
2. Navigate to `http://localhost:5000`
3. You'll be redirected to the login page
4. Use default credentials:
   - Username: `admin`
   - Password: `admin123`
5. Verify role-based access works correctly