# Ticket System

A comprehensive ticket management system built with Django, designed for managing support tickets, task assignments, and workflow automation across departments.

## Overview

This ticket system provides a robust platform for handling support requests, task management, and internal communication within an organization. It includes role-based access control, notification systems, and AI-powered features for enhanced productivity.

## Features

- **User Management**: Role-based access control with admin, staff, and regular user permissions
- **Ticket Management**: Create, update, and track tickets across their lifecycle
- **Department Routing**: Automatically route tickets to appropriate departments
- **Notifications**: Real-time notification system for ticket updates
- **File Attachments**: Support for file uploads attached to tickets
- **Dashboard**: Comprehensive dashboard with ticket statistics and metrics
- **AI Integration**: Google Cloud AI integration for language processing and translation
- **API**: RESTful API for programmatic access to ticket system functions
- **Responsive UI**: Mobile-friendly web interface for all functionality

## Technology Stack

- **Backend**: Django 4.2.10, Python
- **API**: Django REST Framework 3.16.0
- **Database**: PostgreSQL
- **Task Queue**: Celery 5.5.1 with Redis 5.2.1
- **Authentication**: JWT-based authentication
- **AI Services**: Google Cloud Language and Translation APIs
- **Testing**: Pytest 8.3.5

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- Google Cloud Platform account (for AI features)

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd TicketSystem
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables by creating a `.env` file with the following variables:
   ```
   DEBUG=True
   SECRET_KEY=your_secret_key
   DATABASE_URL=postgres://user:password@localhost:5432/ticketsystem
   REDIS_URL=redis://localhost:6379/0
   GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
   ```

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Project Structure

```
TicketSystem/
│
├── project/                    # Django project settings
│   ├── settings.py             # Development settings
│   ├── settings_prod.py        # Production settings
│   ├── urls.py                 # Main URL routing
│   └── celery.py               # Celery configuration
│
├── ticket_system/              # Main application
│   ├── models.py               # Database models
│   ├── views.py                # View controllers
│   ├── forms.py                # Form definitions
│   ├── urls.py                 # URL routing for web views
│   ├── api_urls.py             # URL routing for API
│   ├── serializers.py          # DRF serializers
│   ├── admin.py                # Admin site configuration
│   ├── services/               # Business logic services
│   │   ├── ticket_service.py   # Ticket-related operations
│   │   ├── user_service.py     # User-related operations
│   │   └── ai_service.py       # AI integration services
│   ├── templates/              # HTML templates
│   └── templatetags/           # Custom template tags
│
├── static/                     # Static assets
├── media/                      # User uploads
├── documentation/              # Project documentation
├── tests/                      # Test suite
├── credentials/                # Credentials for external services
└── requirements.txt            # Project dependencies
```

## Key Components

### Models

- **User**: Extended Django user model with additional fields for role management
- **Department**: Organizational structure representation
- **Ticket**: Core ticket model with statuses, priorities, and metadata
- **Comment**: Ticket comments and updates
- **Attachment**: File attachments for tickets
- **Notification**: User notification system

### Services

The application follows a service-oriented architecture with key services:

- **TicketService**: Handles ticket operations including creation, updates, permissions, and status changes
- **UserService**: User management, authentication, and permission checks
- **NotificationService**: Manages the notification system for ticket updates
- **AIService**: Integrates with Google Cloud AI for language processing and translation

### Views

The system implements both web views (HTML templates) and API endpoints:

- Web views follow a standard Django MVT pattern
- API views are implemented using Django REST Framework for programmatic access

## API Endpoints

The system provides a RESTful API for programmatic access:

- `GET /api/tickets/`: List all accessible tickets
- `POST /api/tickets/`: Create a new ticket
- `GET /api/tickets/{id}/`: Retrieve a specific ticket
- `PUT /api/tickets/{id}/`: Update a ticket
- `PATCH /api/tickets/{id}/`: Partially update a ticket
- `GET /api/users/`: List all users
- `GET /api/departments/`: List all departments

Authentication is handled via JWT tokens:
- `POST /api/token/`: Obtain JWT token
- `POST /api/token/refresh/`: Refresh JWT token

## Permissions

The system implements role-based access control:

- **Admin**: Full access to all tickets and system settings
- **Staff**: Access to tickets in their department and assigned tickets
- **User**: Access to their own tickets and tickets they are assigned to

## Development

### Running Tests

```bash
pytest
```

### Fixtures and Data Loading

The system includes fixtures for initial data setup and a data fix script:

```bash
python manage.py loaddata initial_data
python fix_data.py  # For fixing specific data issues
```

## Deployment

For deployment instructions, refer to the `DEPLOYMENT_GUIDE.md` file which includes:

- Server requirements
- Environment setup
- Gunicorn and Nginx configuration
- Database setup
- Celery worker configuration

## User Guide

For detailed usage instructions, refer to the `USER_GUIDE.md` file.

## License

Open-Source

## Contact

Emin Cem Koyluoglu (dr.sam <3)