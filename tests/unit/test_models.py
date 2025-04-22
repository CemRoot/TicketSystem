"""
Unit tests for ticket management system models.
"""
import pytest
from django.utils import timezone
from datetime import timedelta

from ticket_system.models import (
    Ticket, TicketComment, Department, Category, SubCategory,
    Role, UserProfile, AIAnalysis, SystemLog
)

pytestmark = pytest.mark.model


@pytest.mark.django_db
class TestTicketModel:
    """Test the Ticket model."""

    def test_ticket_creation(self, ticket):
        """Test that a ticket can be created."""
        assert ticket.id is not None
        assert ticket.ticket_id is not None
        assert ticket.ticket_id.startswith("TKT-")
        
    def test_ticket_id_generation(self, regular_user, department, category):
        """Test that ticket IDs are generated with the correct format."""
        # Create multiple tickets and check their IDs
        ticket1 = Ticket.objects.create(
            title='Test Ticket 1',
            description='Description 1',
            priority='medium',
            status='new',
            department=department,
            category=category,
            created_by=regular_user
        )
        
        ticket2 = Ticket.objects.create(
            title='Test Ticket 2',
            description='Description 2',
            priority='medium',
            status='new',
            department=department,
            category=category,
            created_by=regular_user
        )
        
        # Check that the ticket IDs are formatted correctly and are different
        assert ticket1.ticket_id != ticket2.ticket_id
        assert ticket1.ticket_id.startswith("TKT-")
        assert ticket2.ticket_id.startswith("TKT-")
        
        # Check that the year and month are in the ID
        year = timezone.now().year
        month = timezone.now().month
        assert f"{year}{month:02d}" in ticket1.ticket_id
        assert f"{year}{month:02d}" in ticket2.ticket_id
    
    def test_ticket_status_transitions(self, ticket):
        """Test that ticket status transitions work correctly."""
        # Test transitioning from new to in_progress
        ticket.status = 'in_progress'
        ticket.save()
        assert ticket.status == 'in_progress'
        
        # Test transitioning to resolved
        ticket.status = 'resolved'
        ticket.save()
        assert ticket.status == 'resolved'
        assert ticket.resolution_time is not None
        
        # Test transitioning to closed
        ticket.status = 'closed'
        ticket.save()
        assert ticket.status == 'closed'
        
        # Test reopening a closed ticket
        ticket.status = 'in_progress'
        ticket.save()
        assert ticket.status == 'in_progress'
        assert ticket.resolution_time is None
    
    def test_sla_breach_detection(self, ticket):
        """Test that SLA breach is detected correctly."""
        # Set SLA target
        ticket.sla_target = 'standard'  # 24 hours
        ticket.save()
        
        # Simulate ticket being created 25 hours ago (should breach 24-hour SLA)
        ticket.created_at = timezone.now() - timedelta(hours=25)
        ticket.save()
        
        # Check that SLA breach is detected
        assert ticket.sla_breach is True
        
        # Resolve the ticket and check SLA breach status
        ticket.status = 'resolved'
        ticket.save()
        
        # SLA breach remains true even after resolution
        assert ticket.sla_breach is True
    
    def test_escalation(self, ticket, admin_user):
        """Test ticket escalation functionality."""
        # Initially not escalated
        assert ticket.is_escalated is False
        assert ticket.escalation_level == 0
        
        # Escalate the ticket
        ticket.escalate(admin_user, 'Testing escalation')
        ticket.refresh_from_db()
        
        # Check escalation status
        assert ticket.is_escalated is True
        assert ticket.escalation_level == 1
        
        # Check that an escalation record was created
        assert ticket.escalations.count() == 1
        escalation = ticket.escalations.first()
        assert escalation.level == 1
        assert escalation.reason == 'Testing escalation'
        assert escalation.created_by == admin_user


@pytest.mark.django_db
class TestUserProfileModel:
    """Test the UserProfile model."""
    
    def test_user_profile_creation(self, regular_user_profile):
        """Test that a user profile can be created."""
        assert regular_user_profile.id is not None
        assert regular_user_profile.user.username == 'regular_user'
        assert regular_user_profile.role.name == 'User'
        assert regular_user_profile.department.name == 'IT Support'
    
    def test_user_profile_permissions(self, regular_user_profile, staff_user_profile, admin_user_profile):
        """Test that user profiles have the correct permissions."""
        # Regular user has no staff or admin permissions
        assert regular_user_profile.role.is_staff is False
        assert regular_user_profile.role.is_admin is False
        
        # Staff user has staff permissions but no admin permissions
        assert staff_user_profile.role.is_staff is True
        assert staff_user_profile.role.is_admin is False
        
        # Admin user has both staff and admin permissions
        assert admin_user_profile.role.is_staff is True
        assert admin_user_profile.role.is_admin is True


@pytest.mark.django_db
class TestAIAnalysisModel:
    """Test the AIAnalysis model."""
    
    def test_ai_analysis_creation(self, ai_analysis):
        """Test that an AI analysis can be created."""
        assert ai_analysis.id is not None
        assert ai_analysis.ticket is not None
        assert ai_analysis.sentiment_score == 0.75
        assert ai_analysis.suggested_priority == 'medium'
    
    def test_sentiment_classification(self, ai_analysis, ticket):
        """Test that sentiment is classified correctly."""
        # Positive sentiment
        ai_analysis.sentiment_score = 0.75
        ai_analysis.save()
        assert ai_analysis.get_sentiment_display() == 'Positive'
        
        # Negative sentiment
        ai_analysis.sentiment_score = -0.75
        ai_analysis.save()
        assert ai_analysis.get_sentiment_display() == 'Negative'
        
        # Neutral sentiment
        ai_analysis.sentiment_score = 0.1
        ai_analysis.save()
        assert ai_analysis.get_sentiment_display() == 'Neutral'


@pytest.mark.django_db
class TestTicketCommentModel:
    """Test the TicketComment model."""
    
    def test_comment_creation(self, ticket_comment):
        """Test that a comment can be created."""
        assert ticket_comment.id is not None
        assert ticket_comment.ticket is not None
        assert ticket_comment.user is not None
        assert ticket_comment.content == 'This is a test comment'
        
    def test_internal_comment(self, ticket, staff_user):
        """Test that internal comments can be created."""
        internal_comment = TicketComment.objects.create(
            ticket=ticket,
            user=staff_user,
            content='This is an internal note',
            is_internal=True
        )
        
        assert internal_comment.id is not None
        assert internal_comment.is_internal is True


@pytest.mark.django_db
class TestSystemLogModel:
    """Test the SystemLog model."""
    
    def test_system_log_creation(self, admin_user):
        """Test that a system log can be created."""
        log = SystemLog.objects.create(
            action='TEST',
            description='Test system log',
            user=admin_user,
            ip_address='127.0.0.1'
        )
        
        assert log.id is not None
        assert log.action == 'TEST'
        assert log.user == admin_user
        assert log.ip_address == '127.0.0.1'
