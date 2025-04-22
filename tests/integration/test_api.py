"""
API integration tests for the ticket management system.
These tests can be used with Google Cloud services like Gemini and Vertex AI for automation.
"""
import json
import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = pytest.mark.api


@pytest.mark.django_db
class TestTicketAPI:
    """Test the Ticket API endpoints."""
    
    def test_ticket_list_unauthorized(self, api_client):
        """Test that unauthenticated users cannot access ticket list."""
        url = reverse('ticket_system:api-ticket-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_ticket_list_as_regular_user(self, authenticated_regular_api_client, ticket, assigned_ticket):
        """Test that regular users can only see their own tickets."""
        url = reverse('ticket_system:api-ticket-list')
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Regular user should only see tickets they created
        assert len(data) == 2
        assert data[0]['ticket_id'] == ticket.ticket_id or data[1]['ticket_id'] == ticket.ticket_id
    
    def test_ticket_list_as_staff(self, authenticated_staff_api_client, ticket, assigned_ticket, staff_user_profile):
        """Test that staff users can see tickets in their department and assigned to them."""
        url = reverse('ticket_system:api-ticket-list')
        response = authenticated_staff_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Staff should see tickets in their department
        assert len(data) >= 1
    
    def test_ticket_list_filtering(self, authenticated_regular_api_client, ticket, department):
        """Test that tickets can be filtered."""
        # Create another ticket with different status
        from ticket_system.models import Ticket
        Ticket.objects.create(
            title='Another Test Ticket',
            description='This is another test ticket',
            priority='high',
            status='closed',
            department=department,
            category=ticket.category,
            created_by=authenticated_regular_api_client.user
        )
        
        # Test filtering by status
        url = reverse('ticket_system:api-ticket-list') + '?status=new'
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]['status'] == 'new'
        
        # Test filtering by priority
        url = reverse('ticket_system:api-ticket-list') + '?priority=high'
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]['priority'] == 'high'
    
    def test_ticket_detail(self, authenticated_regular_api_client, ticket):
        """Test that a user can get the details of their ticket."""
        url = reverse('ticket_system:api-ticket-detail', kwargs={'ticket_id': ticket.ticket_id})
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['ticket_id'] == ticket.ticket_id
        assert data['title'] == ticket.title
        assert data['description'] == ticket.description
    
    def test_ticket_create(self, authenticated_regular_api_client, department, category):
        """Test that a user can create a ticket."""
        url = reverse('ticket_system:api-ticket-list')
        data = {
            'title': 'API Test Ticket',
            'description': 'This ticket was created via API',
            'priority': 'medium',
            'department': department.id,
            'category': category.id
        }
        
        response = authenticated_regular_api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data['title'] == 'API Test Ticket'
        assert response_data['ticket_id'] is not None
        
        # Check that the ticket was created in the database
        from ticket_system.models import Ticket
        ticket = Ticket.objects.get(ticket_id=response_data['ticket_id'])
        assert ticket.title == 'API Test Ticket'
        assert ticket.created_by == authenticated_regular_api_client.user
    
    def test_ticket_update(self, authenticated_regular_api_client, ticket):
        """Test that a user can update their ticket."""
        url = reverse('ticket_system:api-ticket-detail', kwargs={'ticket_id': ticket.ticket_id})
        data = {
            'title': 'Updated Ticket Title',
            'description': 'Updated description',
            'priority': 'high',
            'department': ticket.department.id,
            'category': ticket.category.id
        }
        
        response = authenticated_regular_api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        ticket.refresh_from_db()
        assert ticket.title == 'Updated Ticket Title'
        assert ticket.description == 'Updated description'
        assert ticket.priority == 'high'


@pytest.mark.django_db
class TestTicketCommentAPI:
    """Test the Ticket Comment API endpoints."""
    
    def test_comment_list(self, authenticated_regular_api_client, ticket, ticket_comment):
        """Test that a user can list comments on their ticket."""
        url = reverse('ticket_system:api-ticket-comments', kwargs={'ticket_id': ticket.ticket_id})
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]['content'] == 'This is a test comment'
    
    def test_comment_create(self, authenticated_regular_api_client, ticket):
        """Test that a user can add a comment to their ticket."""
        url = reverse('ticket_system:api-ticket-comments', kwargs={'ticket_id': ticket.ticket_id})
        data = {
            'content': 'This is a new comment from API'
        }
        
        response = authenticated_regular_api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data['content'] == 'This is a new comment from API'
        
        # Check that the comment was created in the database
        from ticket_system.models import TicketComment
        comment = TicketComment.objects.get(id=response_data['id'])
        assert comment.content == 'This is a new comment from API'
        assert comment.user == authenticated_regular_api_client.user
        assert comment.ticket == ticket
    
    def test_internal_comment_as_regular_user(self, authenticated_regular_api_client, ticket):
        """Test that regular users cannot create internal comments."""
        url = reverse('ticket_system:api-ticket-comments', kwargs={'ticket_id': ticket.ticket_id})
        data = {
            'content': 'Attempted internal comment',
            'is_internal': True
        }
        
        response = authenticated_regular_api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Check that the comment was created but is NOT internal
        from ticket_system.models import TicketComment
        comment = TicketComment.objects.get(id=response.json()['id'])
        assert comment.is_internal is False
    
    def test_internal_comment_as_staff(self, authenticated_staff_api_client, ticket):
        """Test that staff users can create internal comments."""
        url = reverse('ticket_system:api-ticket-comments', kwargs={'ticket_id': ticket.ticket_id})
        data = {
            'content': 'Internal staff note',
            'is_internal': True
        }
        
        response = authenticated_staff_api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Check that the comment was created as internal
        from ticket_system.models import TicketComment
        comment = TicketComment.objects.get(id=response.json()['id'])
        assert comment.is_internal is True
    
    def test_staff_can_see_internal_comments(self, authenticated_staff_api_client, ticket):
        """Test that staff users can see internal comments."""
        # Create an internal comment
        from ticket_system.models import TicketComment
        TicketComment.objects.create(
            ticket=ticket,
            user=authenticated_staff_api_client.user,
            content='Internal staff note',
            is_internal=True
        )
        
        url = reverse('ticket_system:api-ticket-comments', kwargs={'ticket_id': ticket.ticket_id})
        response = authenticated_staff_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Staff should see all comments including internal ones
        assert len(data) >= 1
        internal_comments = [c for c in data if c['is_internal']]
        assert len(internal_comments) >= 1
    
    def test_regular_users_cannot_see_internal_comments(self, authenticated_regular_api_client, ticket, staff_user):
        """Test that regular users cannot see internal comments."""
        # Create an internal comment
        from ticket_system.models import TicketComment
        TicketComment.objects.create(
            ticket=ticket,
            user=staff_user,
            content='Internal staff note',
            is_internal=True
        )
        
        # Create a regular comment for comparison
        TicketComment.objects.create(
            ticket=ticket,
            user=staff_user,
            content='Regular comment',
            is_internal=False
        )
        
        url = reverse('ticket_system:api-ticket-comments', kwargs={'ticket_id': ticket.ticket_id})
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Regular users should only see non-internal comments
        internal_comments = [c for c in data if c.get('is_internal', False)]
        assert len(internal_comments) == 0
        
        # But they should see the regular comment
        regular_comments = [c for c in data if c['content'] == 'Regular comment']
        assert len(regular_comments) == 1


@pytest.mark.django_db
class TestUserAPI:
    """Test the User API endpoints."""
    
    def test_user_list_as_regular_user(self, authenticated_regular_api_client):
        """Test that regular users cannot access user list."""
        url = reverse('ticket_system:api-user-list')
        response = authenticated_regular_api_client.get(url)
        
        # Regular users should not be able to list all users
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_user_list_as_staff(self, authenticated_staff_api_client, regular_user, staff_user, admin_user):
        """Test that staff users can list users."""
        url = reverse('ticket_system:api-user-list')
        response = authenticated_staff_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should contain at least the three test users
        assert len(data) >= 3
        
        usernames = [user['username'] for user in data]
        assert 'regular_user' in usernames
        assert 'staff_user' in usernames
        assert 'admin_user' in usernames
    
    def test_user_detail_own_profile(self, authenticated_regular_api_client, regular_user):
        """Test that users can view their own profile."""
        url = reverse('ticket_system:api-user-detail', kwargs={'pk': regular_user.id})
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['username'] == 'regular_user'
    
    def test_user_detail_other_user_as_regular(self, authenticated_regular_api_client, staff_user):
        """Test that regular users cannot view other users' profiles."""
        url = reverse('ticket_system:api-user-detail', kwargs={'pk': staff_user.id})
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_user_detail_other_user_as_admin(self, authenticated_admin_api_client, regular_user):
        """Test that admin users can view other users' profiles."""
        url = reverse('ticket_system:api-user-detail', kwargs={'pk': regular_user.id})
        response = authenticated_admin_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['username'] == 'regular_user'


@pytest.mark.django_db
class TestDepartmentAPI:
    """Test the Department API endpoints."""
    
    def test_department_list(self, authenticated_regular_api_client, department, another_department):
        """Test that users can list departments."""
        url = reverse('ticket_system:api-department-list')
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should show both departments
        assert len(data) >= 2
        
        department_names = [d['name'] for d in data]
        assert 'IT Support' in department_names
        assert 'HR' in department_names


@pytest.mark.django_db
class TestCategoryAPI:
    """Test the Category API endpoints."""
    
    def test_category_list(self, authenticated_regular_api_client, category):
        """Test that users can list categories."""
        url = reverse('ticket_system:api-category-list')
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should show the category
        assert len(data) >= 1
        assert data[0]['name'] == 'Hardware'
    
    def test_category_filter_by_department(self, authenticated_regular_api_client, category, department, another_department):
        """Test that categories can be filtered by department."""
        # Create another category in a different department
        from ticket_system.models import Category
        Category.objects.create(
            name='Benefits',
            description='Benefits related issues',
            department=another_department,
            is_active=True
        )
        
        # Filter by IT Support department
        url = reverse('ticket_system:api-category-list') + f'?department_id={department.id}'
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only show categories in the IT Support department
        assert len(data) == 1
        assert data[0]['name'] == 'Hardware'
        
        # Filter by HR department
        url = reverse('ticket_system:api-category-list') + f'?department_id={another_department.id}'
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only show categories in the HR department
        assert len(data) == 1
        assert data[0]['name'] == 'Benefits'


@pytest.mark.django_db
class TestNotificationAPI:
    """Test the Notification API endpoints."""
    
    def test_notification_list(self, authenticated_regular_api_client, regular_user):
        """Test that users can list their notifications."""
        # Create some notifications for the user
        from ticket_system.models import Notification
        Notification.objects.create(
            user=regular_user,
            title='Test Notification 1',
            content='This is test notification 1',
            notification_type='ticket_update'
        )
        Notification.objects.create(
            user=regular_user,
            title='Test Notification 2',
            content='This is test notification 2',
            notification_type='comment',
            is_read=True
        )
        
        url = reverse('ticket_system:api-notification-list')
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should show both notifications
        assert len(data) == 2
        notification_titles = [n['title'] for n in data]
        assert 'Test Notification 1' in notification_titles
        assert 'Test Notification 2' in notification_titles
    
    def test_notification_filter_by_read_status(self, authenticated_regular_api_client, regular_user):
        """Test that notifications can be filtered by read status."""
        # Create some notifications with different read statuses
        from ticket_system.models import Notification
        Notification.objects.create(
            user=regular_user,
            title='Unread Notification',
            content='This is an unread notification',
            notification_type='ticket_update',
            is_read=False
        )
        Notification.objects.create(
            user=regular_user,
            title='Read Notification',
            content='This is a read notification',
            notification_type='comment',
            is_read=True
        )
        
        # Filter by unread notifications
        url = reverse('ticket_system:api-notification-list') + '?is_read=false'
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only show unread notifications
        assert len(data) == 1
        assert data[0]['title'] == 'Unread Notification'
        assert data[0]['is_read'] is False
        
        # Filter by read notifications
        url = reverse('ticket_system:api-notification-list') + '?is_read=true'
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only show read notifications
        assert len(data) == 1
        assert data[0]['title'] == 'Read Notification'
        assert data[0]['is_read'] is True
    
    def test_mark_notification_read(self, authenticated_regular_api_client, regular_user):
        """Test that users can mark notifications as read."""
        # Create an unread notification
        from ticket_system.models import Notification
        notification = Notification.objects.create(
            user=regular_user,
            title='Notification to Mark Read',
            content='This notification will be marked as read',
            notification_type='ticket_update',
            is_read=False
        )
        
        url = reverse('ticket_system:api-mark-notification-read', kwargs={'pk': notification.id})
        response = authenticated_regular_api_client.patch(url, {}, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check that the notification was marked as read
        notification.refresh_from_db()
        assert notification.is_read is True
    
    def test_cannot_mark_other_users_notification(self, authenticated_staff_api_client, regular_user):
        """Test that users cannot mark other users' notifications as read."""
        # Create a notification for a different user
        from ticket_system.models import Notification
        notification = Notification.objects.create(
            user=regular_user,
            title='Other User Notification',
            content='This notification belongs to another user',
            notification_type='ticket_update',
            is_read=False
        )
        
        url = reverse('ticket_system:api-mark-notification-read', kwargs={'pk': notification.id})
        response = authenticated_staff_api_client.patch(url, {}, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Check that the notification was not marked as read
        notification.refresh_from_db()
        assert notification.is_read is False
