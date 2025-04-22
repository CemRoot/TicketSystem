"""
Test fixtures for the ticket management system.
"""
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from ticket_system.models import (
    Department, Category, SubCategory, Role, UserProfile,
    Ticket, TicketComment, TicketAttachment, TicketEscalation,
    AIAnalysis
)


@pytest.fixture
def api_client():
    """Return a DRF API client instance."""
    return APIClient()


@pytest.fixture
def regular_user():
    """Create and return a regular user."""
    user = User.objects.create_user(
        username='regular_user',
        email='regular@example.com',
        password='password123',
        first_name='Regular',
        last_name='User'
    )
    return user


@pytest.fixture
def staff_user():
    """Create and return a staff user."""
    user = User.objects.create_user(
        username='staff_user',
        email='staff@example.com',
        password='password123',
        first_name='Staff',
        last_name='User'
    )
    return user


@pytest.fixture
def admin_user():
    """Create and return an admin user."""
    user = User.objects.create_user(
        username='admin_user',
        email='admin@example.com',
        password='password123',
        first_name='Admin',
        last_name='User',
        is_staff=True  # Django staff (not our system staff)
    )
    return user


@pytest.fixture
def department():
    """Create and return a department."""
    return Department.objects.create(
        name='IT Support',
        description='Information Technology Support Department',
        is_active=True
    )


@pytest.fixture
def another_department():
    """Create and return another department."""
    return Department.objects.create(
        name='HR',
        description='Human Resources Department',
        is_active=True
    )


@pytest.fixture
def category(department):
    """Create and return a category."""
    return Category.objects.create(
        name='Hardware',
        description='Hardware related issues',
        department=department,
        is_active=True
    )


@pytest.fixture
def subcategory(category):
    """Create and return a subcategory."""
    return SubCategory.objects.create(
        name='Laptop',
        description='Laptop related issues',
        category=category,
        is_active=True
    )


@pytest.fixture
def admin_role():
    """Create and return an admin role."""
    return Role.objects.create(
        name='Administrator',
        description='System Administrator',
        is_admin=True,
        is_staff=True
    )


@pytest.fixture
def staff_role():
    """Create and return a staff role."""
    return Role.objects.create(
        name='Support Staff',
        description='IT Support Staff',
        is_admin=False,
        is_staff=True
    )


@pytest.fixture
def regular_role():
    """Create and return a regular user role."""
    return Role.objects.create(
        name='User',
        description='Regular System User',
        is_admin=False,
        is_staff=False
    )


@pytest.fixture
def regular_user_profile(regular_user, department, regular_role):
    """Create and return a profile for a regular user."""
    return UserProfile.objects.create(
        user=regular_user,
        department=department,
        role=regular_role,
        phone='123-456-7890'
    )


@pytest.fixture
def staff_user_profile(staff_user, department, staff_role):
    """Create and return a profile for a staff user."""
    return UserProfile.objects.create(
        user=staff_user,
        department=department,
        role=staff_role,
        phone='123-456-7891'
    )


@pytest.fixture
def admin_user_profile(admin_user, department, admin_role):
    """Create and return a profile for an admin user."""
    return UserProfile.objects.create(
        user=admin_user,
        department=department,
        role=admin_role,
        phone='123-456-7892'
    )


@pytest.fixture
def ticket(regular_user, department, category, subcategory):
    """Create and return a ticket."""
    return Ticket.objects.create(
        title='Test Ticket',
        description='This is a test ticket description',
        priority='medium',
        status='new',
        department=department,
        category=category,
        subcategory=subcategory,
        created_by=regular_user
    )


@pytest.fixture
def assigned_ticket(regular_user, staff_user, department, category, subcategory):
    """Create and return a ticket that's assigned to staff."""
    return Ticket.objects.create(
        title='Assigned Ticket',
        description='This ticket is assigned to staff',
        priority='high',
        status='in_progress',
        department=department,
        category=category,
        subcategory=subcategory,
        created_by=regular_user,
        assigned_to=staff_user
    )


@pytest.fixture
def ticket_comment(ticket, regular_user):
    """Create and return a ticket comment."""
    return TicketComment.objects.create(
        ticket=ticket,
        user=regular_user,
        content='This is a test comment'
    )


@pytest.fixture
def ai_analysis(ticket):
    """Create and return an AI analysis for a ticket."""
    return AIAnalysis.objects.create(
        ticket=ticket,
        sentiment_score=0.75,
        suggested_priority='medium',
        suggested_category='Hardware',
        suggested_staff='staff_user',
        processing_time=0.5
    )


@pytest.fixture
def authenticated_regular_client(client, regular_user):
    """Return an authenticated client as a regular user."""
    client.login(username='regular_user', password='password123')
    return client


@pytest.fixture
def authenticated_staff_client(client, staff_user):
    """Return an authenticated client as a staff user."""
    client.login(username='staff_user', password='password123')
    return client


@pytest.fixture
def authenticated_admin_client(client, admin_user):
    """Return an authenticated client as an admin user."""
    client.login(username='admin_user', password='password123')
    return client


@pytest.fixture
def authenticated_regular_api_client(api_client, regular_user):
    """Return an authenticated API client as a regular user."""
    api_client.force_authenticate(user=regular_user)
    return api_client


@pytest.fixture
def authenticated_staff_api_client(api_client, staff_user):
    """Return an authenticated API client as a staff user."""
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def authenticated_admin_api_client(api_client, admin_user):
    """Return an authenticated API client as an admin user."""
    api_client.force_authenticate(user=admin_user)
    return api_client
