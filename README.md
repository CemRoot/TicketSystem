<div align="center">

# 🎫 Ticket System

### Enterprise-Grade Ticket Management Platform

A comprehensive ticket management system built with Django, designed for managing support tickets, task assignments, and workflow automation across departments.

[![Django](https://img.shields.io/badge/Django-4.2.10-092E20?style=flat&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-316192?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Celery](https://img.shields.io/badge/Celery-5.5.1-37814A?style=flat&logo=celery&logoColor=white)](https://docs.celeryproject.org/)
[![Redis](https://img.shields.io/badge/Redis-5.2.1-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

[Features](#-features) • [Installation](#-installation) • [Documentation](#-documentation) • [API](#-api-endpoints) • [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Installation](#-installation)
- [Project Structure](#-project-structure)
- [Key Components](#-key-components)
- [API Endpoints](#-api-endpoints)
- [Permissions](#-permissions)
- [Development](#-development)
- [Deployment](#-deployment)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)

## 🎯 Overview

This ticket system provides a robust, enterprise-ready platform for handling support requests, task management, and internal communication within organizations. It includes role-based access control, real-time notifications, and AI-powered features for enhanced productivity and automation.

## ✨ Features

### Core Functionality
- 🔐 **User Management** - Role-based access control (Admin, Staff, User)
- 🎫 **Ticket Management** - Complete lifecycle management from creation to resolution
- 🏢 **Department Routing** - Intelligent automatic routing to appropriate departments
- 🔔 **Real-Time Notifications** - Instant updates on ticket status changes
- 📎 **File Attachments** - Secure file upload and management system

### Advanced Features
- 📊 **Analytics Dashboard** - Comprehensive metrics and statistics visualization
- 🤖 **AI Integration** - Google Cloud AI for language processing and auto-translation
- 🔌 **RESTful API** - Full programmatic access with JWT authentication
- 📱 **Responsive Design** - Mobile-first, accessible interface
- ⚡ **Async Task Processing** - Celery-based background job handling

## 🛠️ Technology Stack

| Category | Technologies |
|----------|-------------|
| **Backend Framework** | Django 4.2.10, Python 3.8+ |
| **API Framework** | Django REST Framework 3.16.0 |
| **Database** | PostgreSQL |
| **Caching & Queue** | Redis 5.2.1, Celery 5.5.1 |
| **Authentication** | JWT (JSON Web Tokens) |
| **AI Services** | Google Cloud Language & Translation APIs |
| **Testing** | Pytest 8.3.5 |
| **Web Server** | Gunicorn (Production) |

## 🚀 Installation

### Prerequisites

Before you begin, ensure you have the following installed:

- ![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white) Python 3.8 or higher
- ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Latest-316192?style=flat&logo=postgresql&logoColor=white) PostgreSQL
- ![Redis](https://img.shields.io/badge/Redis-Latest-DC382D?style=flat&logo=redis&logoColor=white) Redis
- Google Cloud Platform account (for AI features - optional)

### Quick Start

#### 1️⃣ Clone the Repository
```bash
git clone <repository-url>
cd TicketSystem
```

#### 2️⃣ Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4️⃣ Configure Environment Variables
Create a `.env` file in the project root:

```env
# Django Settings
DEBUG=True
SECRET_KEY=your_secret_key_here

# Database
DATABASE_URL=postgres://user:password@localhost:5432/ticketsystem

# Redis
REDIS_URL=redis://localhost:6379/0

# Google Cloud AI (Optional)
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

#### 5️⃣ Database Setup
```bash
# Run migrations
python manage.py migrate

# Create superuser account
python manage.py createsuperuser

# Load initial data (optional)
python manage.py loaddata initial_data
```

#### 6️⃣ Start Development Server
```bash
# Start Django development server
python manage.py runserver

# In another terminal, start Celery worker (for async tasks)
celery -A project worker -l info
```

🎉 **Your application is now running at** `http://localhost:8000`

## 📁 Project Structure

```
TicketSystem/
│
├── 📦 project/                      # Django project configuration
│   ├── settings.py                  # Development settings
│   ├── settings_prod.py             # Production settings
│   ├── urls.py                      # Main URL routing
│   ├── celery.py                    # Celery task queue config
│   ├── wsgi.py                      # WSGI entry point
│   └── asgi.py                      # ASGI entry point
│
├── 🎫 ticket_system/                # Core application
│   ├── models.py                    # Database models (User, Ticket, Department, etc.)
│   ├── views.py                     # View controllers
│   ├── forms.py                     # Django forms
│   ├── urls.py                      # Web view URL routing
│   ├── api_urls.py                  # API endpoint routing
│   ├── serializers.py               # DRF serializers
│   ├── admin.py                     # Admin interface configuration
│   │
│   ├── 🔧 services/                 # Business logic layer
│   │   ├── ticket_service.py        # Ticket operations
│   │   ├── user_service.py          # User management
│   │   ├── notification_service.py  # Notifications
│   │   └── ai_service.py            # Google Cloud AI integration
│   │
│   ├── 🎨 templates/                # HTML templates
│   ├── 🏷️  templatetags/            # Custom template filters
│   └── 📦 migrations/               # Database migrations
│
├── 🖼️  static/                      # Static files (CSS, JS, images)
├── 📁 media/                        # User-uploaded files
├── 📚 docs/                         # Project documentation
│   ├── BPMN_Analysis.md             # Process analysis
│   ├── bpmn_as_is.md                # Current state documentation
│   └── bpmn_to_be.md                # Future state documentation
│
├── 🧪 tests/                        # Test suite
│   ├── test_models.py               # Model tests
│   ├── test_views.py                # View tests
│   ├── test_services.py             # Service tests
│   └── test_api.py                  # API tests
│
├── 🔧 scripts/                      # Utility scripts
│   └── fix_data.py                  # Data migration/fix script
│
├── ⚙️  config/                      # Configuration files
│   └── gunicorn_config.py           # Gunicorn server config
│
├── 📄 Configuration Files
│   ├── requirements.txt             # Python dependencies
│   ├── pytest.ini                   # Pytest configuration
│   ├── .env                         # Environment variables (not in git)
│   ├── .gitignore                   # Git ignore rules
│   └── manage.py                    # Django management script
│
└── 📖 Documentation Files
    ├── README.md                    # This file - project overview
    ├── CONTRIBUTING.md              # Contribution guidelines
    ├── LICENSE                      # MIT License
    ├── DEPLOYMENT_GUIDE.md          # Deployment instructions
    └── USER_GUIDE.md                # End-user documentation
```

## 🔑 Key Components

### 📊 Models

| Model | Description |
|-------|-------------|
| **User** | Extended Django user model with role management (Admin, Staff, User) |
| **Department** | Organizational structure and department hierarchy |
| **Ticket** | Core ticket entity with status, priority, assignment, and metadata |
| **Comment** | Threaded comments and updates on tickets |
| **Attachment** | Secure file attachment management |
| **Notification** | Real-time notification system for ticket events |

### 🔧 Services Layer

The application follows a **service-oriented architecture** with separation of concerns:

| Service | Responsibility |
|---------|---------------|
| **TicketService** | Ticket CRUD operations, status management, permissions |
| **UserService** | User authentication, authorization, profile management |
| **NotificationService** | Real-time notification dispatch and management |
| **AIService** | Google Cloud AI integration for language processing and translation |

### 🎨 Views Architecture

The system implements a **hybrid architecture**:

- **Web Views**: Django MVT pattern with server-side rendering
- **API Views**: RESTful endpoints using Django REST Framework
- **Authentication**: JWT-based stateless authentication for API access

## 🔌 API Endpoints

The system provides a comprehensive RESTful API:

### Ticket Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tickets/` | List all accessible tickets |
| `POST` | `/api/tickets/` | Create a new ticket |
| `GET` | `/api/tickets/{id}/` | Retrieve ticket details |
| `PUT` | `/api/tickets/{id}/` | Update ticket (full) |
| `PATCH` | `/api/tickets/{id}/` | Update ticket (partial) |
| `DELETE` | `/api/tickets/{id}/` | Delete ticket |

### User & Department Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users/` | List all users |
| `GET` | `/api/users/{id}/` | Get user details |
| `GET` | `/api/departments/` | List all departments |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/token/` | Obtain JWT access & refresh tokens |
| `POST` | `/api/token/refresh/` | Refresh JWT access token |

**Authentication**: All API endpoints require JWT token authentication. Include the token in the `Authorization` header:
```
Authorization: Bearer <your-jwt-token>
```

## 🔒 Permissions & Access Control

The system implements **role-based access control (RBAC)**:

| Role | Permissions |
|------|-------------|
| **👑 Admin** | Full system access, user management, all tickets, system configuration |
| **👔 Staff** | Department tickets, assigned tickets, create/update tickets in their domain |
| **👤 User** | Own tickets, assigned tickets, create new tickets |

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ticket_system

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Run linting
flake8 ticket_system/

# Format code
black ticket_system/

# Type checking
mypy ticket_system/
```

### Database Management

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Load fixtures
python manage.py loaddata initial_data

# Fix data issues (custom script - if needed)
python scripts/fix_data.py
```

## 🚀 Deployment

For comprehensive deployment instructions, see **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

Key deployment topics covered:
- ☁️ Server requirements and setup
- 🐳 Docker containerization
- 🔧 Gunicorn and Nginx configuration
- 🗄️ PostgreSQL database setup
- ⚡ Celery worker configuration
- 🔐 Security best practices
- 📊 Monitoring and logging

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file - project overview and setup |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Guidelines for contributing to the project |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Production deployment instructions |
| [USER_GUIDE.md](USER_GUIDE.md) | End-user documentation and tutorials |
| [docs/](docs/) | BPMN analysis and technical documentation |

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please ensure your code:
- ✅ Passes all tests (`pytest`)
- ✅ Follows PEP 8 style guidelines
- ✅ Includes appropriate documentation
- ✅ Has test coverage for new features

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 📧 Contact

**Emin Cem Koyluoglu** (dr.sam)

---

<div align="center">

**⭐ Star this repository if you find it helpful!**

Made with ❤️ using Django

</div>