"""
AI integration tests for the ticket management system.
These tests specifically target the AI functionalities and can be used with 
Google Cloud services like Gemini and Vertex AI for automation.
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework import status

from ticket_system.models import AIAnalysis, Ticket
from ticket_system.services.ai_service import AIService

pytestmark = pytest.mark.ai


class MockVertexAI:
    """Mock class for VertexAI responses."""
    
    @staticmethod
    def analyze_text_sentiment(text):
        """Mock sentiment analysis."""
        # Determine sentiment based on some keywords
        if any(word in text.lower() for word in ['great', 'excellent', 'happy', 'pleased']):
            return {
                'score': 0.8,
                'magnitude': 0.9,
                'document_sentiment': {'score': 0.8, 'magnitude': 0.9}
            }
        elif any(word in text.lower() for word in ['bad', 'poor', 'angry', 'frustrated']):
            return {
                'score': -0.7,
                'magnitude': 0.8,
                'document_sentiment': {'score': -0.7, 'magnitude': 0.8}
            }
        else:
            return {
                'score': 0.1,
                'magnitude': 0.2,
                'document_sentiment': {'score': 0.1, 'magnitude': 0.2}
            }
    
    @staticmethod
    def classify_text(text):
        """Mock text classification."""
        if 'hardware' in text.lower() or 'laptop' in text.lower() or 'computer' in text.lower():
            return {
                'categories': [
                    {'name': 'Hardware', 'confidence': 0.92},
                    {'name': 'IT Support', 'confidence': 0.87}
                ]
            }
        elif 'software' in text.lower() or 'application' in text.lower() or 'program' in text.lower():
            return {
                'categories': [
                    {'name': 'Software', 'confidence': 0.95},
                    {'name': 'IT Support', 'confidence': 0.85}
                ]
            }
        else:
            return {
                'categories': [
                    {'name': 'General', 'confidence': 0.75},
                    {'name': 'IT Support', 'confidence': 0.65}
                ]
            }
    
    @staticmethod
    def generate_text(prompt):
        """Mock text generation."""
        if 'hardware' in prompt.lower():
            return "This appears to be a hardware issue. Have you tried checking the physical connections? Please provide more details about your hardware setup."
        elif 'software' in prompt.lower():
            return "This looks like a software issue. Have you tried restarting the application? Please provide the version of the software you're using."
        else:
            return "Thank you for your request. Could you please provide more details about the issue you're experiencing?"


@pytest.mark.django_db
class TestAIAnalysisProcessing:
    """Test the AI analysis processing functionality."""
    
    @patch('ticket_system.services.ai_service.AIService._analyze_sentiment')
    @patch('ticket_system.services.ai_service.AIService._classify_text')
    @patch('ticket_system.services.ai_service.AIService._suggest_staff')
    def test_process_ticket(self, mock_suggest_staff, mock_classify_text, mock_analyze_sentiment, ticket):
        """Test that a ticket can be processed by the AI service."""
        # Setup mocks
        mock_analyze_sentiment.return_value = 0.8
        mock_classify_text.return_value = ("Hardware", 0.92)
        mock_suggest_staff.return_value = "staff_user"
        
        # Process the ticket
        ai_service = AIService()
        analysis = ai_service.process_ticket(ticket)
        
        assert analysis is not None
        assert analysis.ticket == ticket
        assert analysis.sentiment_score == 0.8
        assert analysis.suggested_category == "Hardware"
        assert analysis.suggested_staff == "staff_user"
        assert analysis.confidence_score == 0.92
        
        # Make sure the mocks were called
        mock_analyze_sentiment.assert_called_once()
        mock_classify_text.assert_called_once()
        mock_suggest_staff.assert_called_once()
    
    def test_get_suggestion_success(self, ticket, ai_analysis):
        """Test retrieving AI suggestions."""
        # Set up the analysis
        ai_analysis.ticket = ticket
        ai_analysis.sentiment_score = 0.8
        ai_analysis.suggested_category = "Hardware"
        ai_analysis.suggested_priority = "high"
        ai_analysis.suggested_staff = "staff_user"
        ai_analysis.save()
        
        # Get the suggestion
        ai_service = AIService()
        suggestion = ai_service.get_suggestion(ticket.id)
        
        assert suggestion is not None
        assert suggestion['sentiment_score'] == 0.8
        assert suggestion['suggested_category'] == "Hardware"
        assert suggestion['suggested_priority'] == "high"
        assert suggestion['suggested_staff'] == "staff_user"
    
    def test_get_suggestion_no_analysis(self):
        """Test retrieving AI suggestions when no analysis exists."""
        # No analysis exists for this ticket ID
        ai_service = AIService()
        suggestion = ai_service.get_suggestion(999999)
        
        assert suggestion == {
            'error': 'No AI analysis available for this ticket'
        }


@pytest.mark.django_db
class TestAIEndpoints:
    """Test the AI-specific API endpoints."""
    
    @patch('ticket_system.views.AIService.process_ticket')
    def test_process_ticket_api(self, mock_process_ticket, authenticated_staff_api_client, ticket):
        """Test the API endpoint for processing a ticket."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.sentiment_score = 0.8
        mock_process.suggested_category = "Hardware"
        mock_process.suggested_priority = "high"
        mock_process.suggested_staff = "staff_user"
        mock_process.confidence_score = 0.92
        mock_process_ticket.return_value = mock_process
        
        url = reverse('ticket_system:api-process-ticket', kwargs={'ticket_id': ticket.ticket_id})
        response = authenticated_staff_api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['success'] is True
        assert 'analysis_id' in data
        
        # Check that the service was called
        mock_process_ticket.assert_called_once_with(ticket)
    
    @patch('ticket_system.views.AIService.get_suggestion')
    def test_get_ai_analysis_api(self, mock_get_suggestion, authenticated_regular_api_client, ticket):
        """Test the API endpoint for getting AI analysis."""
        # Setup mock
        mock_get_suggestion.return_value = {
            'sentiment_score': 0.8,
            'suggested_category': "Hardware",
            'suggested_priority': "high",
            'suggested_staff': "staff_user"
        }
        
        url = reverse('ticket_system:api-ticket-ai-analysis', kwargs={'ticket_id': ticket.ticket_id})
        response = authenticated_regular_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['sentiment_score'] == 0.8
        assert data['suggested_category'] == "Hardware"
        
        # Check that the service was called
        mock_get_suggestion.assert_called_once_with(ticket.id)


@pytest.mark.django_db
class TestAIModelIntegration:
    """Test the integration with AI models through Vertex AI/Gemini."""
    
    @patch('ticket_system.services.ai_service.vertexai')
    def test_sentiment_analysis_integration(self, mock_vertexai, ticket):
        """Test integration with sentiment analysis model."""
        # Setup mock to use our MockVertexAI
        mock_vertexai.VertexAI = MockVertexAI
        
        # Set the ticket description to trigger positive sentiment
        ticket.description = "I'm really happy with the service, but I need help with my laptop."
        ticket.save()
        
        ai_service = AIService()
        sentiment_score = ai_service._analyze_sentiment(ticket.description)
        
        assert sentiment_score > 0.5  # Positive sentiment
        
        # Set the ticket description to trigger negative sentiment
        ticket.description = "I'm very frustrated with this poor service. My computer isn't working."
        ticket.save()
        
        sentiment_score = ai_service._analyze_sentiment(ticket.description)
        
        assert sentiment_score < 0  # Negative sentiment
    
    @patch('ticket_system.services.ai_service.vertexai')
    def test_text_classification_integration(self, mock_vertexai, ticket):
        """Test integration with text classification model."""
        # Setup mock to use our MockVertexAI
        mock_vertexai.VertexAI = MockVertexAI
        
        # Set the ticket description to trigger hardware classification
        ticket.description = "My laptop screen is flickering and sometimes goes blank."
        ticket.save()
        
        ai_service = AIService()
        category, confidence = ai_service._classify_text(ticket.description)
        
        assert category == "Hardware"
        assert confidence > 0.9
        
        # Set the ticket description to trigger software classification
        ticket.description = "The application keeps crashing whenever I try to save my work."
        ticket.save()
        
        category, confidence = ai_service._classify_text(ticket.description)
        
        assert category == "Software"
        assert confidence > 0.9
    
    @patch('ticket_system.services.ai_service.vertexai')
    def test_text_generation_integration(self, mock_vertexai, ticket):
        """Test integration with text generation model."""
        # Setup mock to use our MockVertexAI
        mock_vertexai.VertexAI = MockVertexAI
        
        # Set the ticket description to trigger hardware-related response
        ticket.description = "My laptop screen is flickering and sometimes goes blank."
        ticket.save()
        
        ai_service = AIService()
        response = ai_service.generate_response(ticket)
        
        assert "hardware" in response.lower()
        assert "physical connections" in response.lower()
        
        # Set the ticket description to trigger software-related response
        ticket.description = "The application keeps crashing whenever I try to save my work."
        ticket.save()
        
        response = ai_service.generate_response(ticket)
        
        assert "software" in response.lower()
        assert "restarting" in response.lower()


@pytest.mark.django_db
class TestAutomatedTicketRoutingWithAI:
    """Test automated ticket routing using AI suggestions."""
    
    @patch('ticket_system.services.ai_service.AIService._classify_text')
    @patch('ticket_system.services.ai_service.AIService._suggest_staff')
    def test_automatic_assignment_based_on_ai(self, mock_suggest_staff, mock_classify_text, ticket, staff_user):
        """Test that tickets can be automatically assigned based on AI suggestions."""
        # Setup mocks
        mock_classify_text.return_value = ("Hardware", 0.95)
        mock_suggest_staff.return_value = staff_user.username
        
        # Create AIAnalysis with high confidence
        AIAnalysis.objects.create(
            ticket=ticket,
            sentiment_score=0.1,
            suggested_category="Hardware",
            suggested_priority="medium",
            suggested_staff=staff_user.username,
            confidence_score=0.95
        )
        
        # This would typically be called by a background task after ticket creation
        AIService.auto_assign_ticket(ticket)
        
        # Refresh ticket from database
        ticket.refresh_from_db()
        
        # Check that the ticket was assigned as suggested by AI
        assert ticket.assigned_to == staff_user
        assert ticket.category.name == "Hardware"
        assert ticket.priority == "medium"
    
    @patch('ticket_system.services.ai_service.AIService._classify_text')
    @patch('ticket_system.services.ai_service.AIService._suggest_staff')
    def test_auto_assignment_with_low_confidence(self, mock_suggest_staff, mock_classify_text, ticket, staff_user):
        """Test that tickets are not auto-assigned when AI confidence is low."""
        # Setup mocks
        mock_classify_text.return_value = ("Hardware", 0.55)  # Low confidence
        mock_suggest_staff.return_value = staff_user.username
        
        # Create AIAnalysis with low confidence
        AIAnalysis.objects.create(
            ticket=ticket,
            sentiment_score=0.1,
            suggested_category="Hardware",
            suggested_priority="medium",
            suggested_staff=staff_user.username,
            confidence_score=0.55  # Low confidence
        )
        
        # This would typically be called by a background task after ticket creation
        AIService.auto_assign_ticket(ticket)
        
        # Refresh ticket from database
        ticket.refresh_from_db()
        
        # Check that the ticket was NOT auto-assigned due to low confidence
        assert ticket.assigned_to is None  # Should remain unassigned


@pytest.mark.django_db
class TestAIFeedbackLoop:
    """Test AI feedback loop for model improvement."""
    
    def test_record_ai_feedback(self, ticket, ai_analysis, staff_user):
        """Test recording feedback about AI suggestions."""
        from ticket_system.models import AIFeedback
        
        # Record feedback that the AI suggestion was correct
        feedback = AIService.record_feedback(
            ticket_id=ticket.id,
            feedback_type='category',
            is_correct=True,
            corrected_value=None,
            provided_by=staff_user
        )
        
        assert feedback is not None
        assert feedback.ticket == ticket
        assert feedback.ai_analysis == ai_analysis
        assert feedback.feedback_type == 'category'
        assert feedback.is_correct is True
        assert feedback.corrected_value is None
        
        # Record feedback that the AI suggestion was incorrect
        feedback = AIService.record_feedback(
            ticket_id=ticket.id,
            feedback_type='priority',
            is_correct=False,
            corrected_value='high',
            provided_by=staff_user
        )
        
        assert feedback is not None
        assert feedback.ticket == ticket
        assert feedback.ai_analysis == ai_analysis
        assert feedback.feedback_type == 'priority'
        assert feedback.is_correct is False
        assert feedback.corrected_value == 'high'
    
    def test_feedback_api_endpoint(self, authenticated_staff_api_client, ticket, ai_analysis):
        """Test the API endpoint for submitting AI feedback."""
        url = reverse('ticket_system:api-ticket-ai-feedback', kwargs={'ticket_id': ticket.ticket_id})
        data = {
            'feedback_type': 'category',
            'is_correct': False,
            'corrected_value': 'Software'
        }
        
        response = authenticated_staff_api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data['success'] is True
        
        # Check that the feedback was recorded in the database
        from ticket_system.models import AIFeedback
        feedback = AIFeedback.objects.filter(ticket=ticket).first()
        
        assert feedback is not None
        assert feedback.feedback_type == 'category'
        assert feedback.is_correct is False
        assert feedback.corrected_value == 'Software'


@pytest.mark.django_db
class TestAIModelPerformanceMetrics:
    """Test collection and analysis of AI model performance metrics."""
    
    def test_calculate_model_accuracy(self, ticket, ai_analysis, staff_user):
        """Test calculating model accuracy based on feedback."""
        from ticket_system.models import AIFeedback
        
        # Create some feedback records
        AIFeedback.objects.create(
            ticket=ticket,
            ai_analysis=ai_analysis,
            feedback_type='category',
            is_correct=True,
            provided_by=staff_user
        )
        
        AIFeedback.objects.create(
            ticket=ticket,
            ai_analysis=ai_analysis,
            feedback_type='priority',
            is_correct=False,
            corrected_value='high',
            provided_by=staff_user
        )
        
        # Calculate accuracy metrics
        metrics = AIService.calculate_model_accuracy()
        
        assert metrics is not None
        assert 'overall_accuracy' in metrics
        assert 'category_accuracy' in metrics
        assert 'priority_accuracy' in metrics
        
        # With our test data, category should be 100% accurate and priority 0%
        assert metrics['category_accuracy'] == 1.0
        assert metrics['priority_accuracy'] == 0.0
        assert metrics['overall_accuracy'] == 0.5  # Average of the two
    
    def test_model_performance_report_api(self, authenticated_admin_api_client):
        """Test the API endpoint for retrieving model performance reports."""
        url = reverse('ticket_system:api-ai-performance')
        response = authenticated_admin_api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert 'accuracy_metrics' in data
        assert 'feedback_counts' in data
        assert 'suggestion_distribution' in data
