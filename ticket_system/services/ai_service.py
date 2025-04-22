"""
AI Service module for ticket analysis and processing.
Integrates with Google Cloud NLP, Vertex AI, and Gemini.
"""
import time
import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

# Import Google Cloud libraries
try:
    import google.cloud.language as language
    import vertexai
    from vertexai.generative_models import GenerativeModel
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    logging.warning("Google Cloud libraries not available. AI services will be limited.")

from ticket_system.models import (
    Ticket, AIAnalysis, AIFeedback, Department, Category, User
)

logger = logging.getLogger(__name__)


class AIService:
    """
    Service for AI-based ticket analysis and processing.
    Integrates with Google Cloud NLP, Vertex AI, and Gemini.
    """
    
    def __init__(self):
        """Initialize the AI service and any necessary clients."""
        self.language_client = None
        self.vertex_model = None
        
        # Enable Google Cloud services by default
        global GOOGLE_CLOUD_AVAILABLE
        GOOGLE_CLOUD_AVAILABLE = True  # Enable Google Cloud services
        
        # Initialize Google Cloud services if available
        if GOOGLE_CLOUD_AVAILABLE:
            try:
                self.language_client = language.LanguageServiceClient()
                vertexai.init(project=settings.GOOGLE_CLOUD_PROJECT)
                self.vertex_model = GenerativeModel("gemini-pro")
                logger.info("Google Cloud AI services initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google Cloud AI services: {e}")
                GOOGLE_CLOUD_AVAILABLE = False  # Fall back if initialization fails
        
    def process_ticket(self, ticket):
        """
        Process a new ticket with AI analysis.
        
        Args:
            ticket: Ticket object to analyze
            
        Returns:
            AIAnalysis object with results
        """
        start_time = time.time()
        
        # Check for existing analysis
        existing_analysis = AIAnalysis.objects.filter(ticket=ticket).first()
        if existing_analysis:
            logger.info(f"Using existing AI analysis for ticket {ticket.ticket_id}")
            return existing_analysis
        
        # Analyze sentiment
        sentiment_score = self._analyze_sentiment(ticket.description)
        
        # Classify ticket
        category, confidence = self._classify_text(ticket.description)
        
        # Suggest priority based on sentiment and content
        suggested_priority = self._suggest_priority(
            ticket.description, 
            sentiment_score
        )
        
        # Suggest technician based on category and content
        suggested_staff = self._suggest_staff(
            ticket.description,
            category
        )
        
        # Calculate processing time
        processing_time_seconds = time.time() - start_time
        processing_time_duration = timezone.timedelta(seconds=processing_time_seconds)
        
        # Get suggested department if available
        suggested_department = None
        if ticket.department:
            suggested_department = ticket.department
        else:
            # Try to find a department based on category
            try:
                department = Department.objects.filter(name__icontains=category).first()
                if not department:
                    # If no exact match, try to find by categories that contain this name
                    cat = Category.objects.filter(name__icontains=category).first()
                    if cat:
                        department = cat.department
                suggested_department = department
            except Exception as e:
                logger.error(f"Error finding department for category {category}: {e}")
        
        try:
            # Create and return AI analysis - handle the existing model fields
            return AIAnalysis.objects.create(
                ticket=ticket,
                sentiment_score=sentiment_score,
                suggested_category=category,
                category_confidence=confidence,
                suggested_priority=suggested_priority,
                suggested_department=suggested_department,
                processing_time=processing_time_duration
            )
        except Exception as e:
            logger.error(f"Error creating AIAnalysis: {e}")
            # Fallback with minimal fields if there's an error
            return AIAnalysis.objects.create(
                ticket=ticket,
                sentiment_score=sentiment_score,
                suggested_category=category,
                suggested_priority=suggested_priority
            )
    
    def _analyze_sentiment(self, text):
        """
        Analyze sentiment of text using Google Cloud NLP.
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment score between -1.0 (negative) and 1.0 (positive)
        """
        if not GOOGLE_CLOUD_AVAILABLE or not self.language_client:
            # Fallback to simple keyword-based sentiment analysis
            return self._fallback_sentiment_analysis(text)
        
        try:
            document = language.Document(
                content=text,
                type_=language.Document.Type.PLAIN_TEXT
            )
            sentiment = self.language_client.analyze_sentiment(
                document=document
            ).document_sentiment
            
            return sentiment.score
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return self._fallback_sentiment_analysis(text)
    
    def _fallback_sentiment_analysis(self, text):
        """
        Simple rule-based sentiment analysis as fallback.
        
        Args:
            text: Text to analyze
            
        Returns:
            Estimated sentiment score
        """
        text = text.lower()
        
        # Positive and negative word lists
        positive_words = [
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'pleased', 'happy', 'satisfied', 'thank', 'thanks', 'resolved',
            'appreciate', 'helpful', 'awesome', 'perfect', 'love', 'best'
        ]
        
        negative_words = [
            'bad', 'poor', 'terrible', 'awful', 'horrible', 'disappointed',
            'frustrat', 'annoying', 'issue', 'problem', 'error', 'fail',
            'broken', 'crash', 'not working', 'doesn\'t work', 'unusable',
            'angry', 'upset', 'hate', 'worst', 'slow', 'bug', 'difficult'
        ]
        
        # Count word occurrences
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        # Calculate sentiment score
        total = positive_count + negative_count
        if total == 0:
            return 0.0  # Neutral
        
        return (positive_count - negative_count) / total
    
    def _classify_text(self, text):
        """
        Classify ticket text to determine category.
        
        Args:
            text: Ticket description text
            
        Returns:
            Tuple of (category_name, confidence_score)
        """
        if not GOOGLE_CLOUD_AVAILABLE or not self.vertex_model:
            # Fallback to rule-based classification
            return self._fallback_classification(text)
        
        try:
            # Use Vertex AI Gemini for classification
            prompt = f"""
            You are an IT support ticket classifier. Classify the following support ticket into the most appropriate category.
            The possible categories are: Hardware, Software, Network, Account Access, Email, Security, General Inquiry.
            
            Ticket Description:
            {text}
            
            Respond only with the category name and a confidence score between 0 and 1, in this format:
            Category: [category name]
            Confidence: [score]
            """
            
            response = self.vertex_model.generate_content(prompt)
            response_text = response.text
            
            # Parse the response
            category_line = next((line for line in response_text.split('\n') if line.startswith('Category:')), '')
            confidence_line = next((line for line in response_text.split('\n') if line.startswith('Confidence:')), '')
            
            category = category_line.replace('Category:', '').strip() if category_line else 'General'
            confidence_str = confidence_line.replace('Confidence:', '').strip() if confidence_line else '0.7'
            
            try:
                confidence = float(confidence_str)
            except ValueError:
                confidence = 0.7  # Default confidence if parsing fails
            
            return category, min(max(confidence, 0.0), 1.0)  # Ensure confidence is between 0 and 1
            
        except Exception as e:
            logger.error(f"Error in text classification: {e}")
            return self._fallback_classification(text)
    
    def _fallback_classification(self, text):
        """
        Simple rule-based classification as fallback.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (category_name, confidence_score)
        """
        text = text.lower()
        
        # Define categories and related keywords
        categories = {
            'Hardware': ['computer', 'laptop', 'desktop', 'monitor', 'keyboard', 'mouse', 
                        'printer', 'hardware', 'device', 'screen', 'battery', 'charger', 'broken', 'physical'],
            'Software': ['software', 'program', 'application', 'app', 'install', 'update', 
                        'upgrade', 'crash', 'bug', 'error', 'license', 'office', 'windows', 'mac',
                        'pdf', 'document', 'reader', 'adobe', 'file', 'browser', 'chrome', 'firefox', 'edge',
                        'safari', 'open', 'view', 'display', 'render'],
            'Network': ['network', 'internet', 'wifi', 'connection', 'connect', 'ethernet', 
                       'router', 'modem', 'speed', 'slow', 'access', 'vpn', 'download', 'upload'],
            'Account': ['account', 'password', 'login', 'access', 'permission', 'reset', 
                       'locked', 'credential', 'username', 'user', 'authenticate'],
            'Email': ['email', 'mail', 'outlook', 'gmail', 'message', 'spam', 'phishing', 
                     'inbox', 'send', 'receive', 'compose'],
            'Security': ['security', 'virus', 'malware', 'suspicious', 'hack', 'breach', 
                        'phish', 'authentication', 'privacy', 'encrypt', 'firewall'],
        }
        
        # Count matches for each category
        scores = {}
        for category, keywords in categories.items():
            count = sum(1 for keyword in keywords if keyword in text)
            scores[category] = count
        
        # Get category with highest score
        max_score = max(scores.values()) if scores else 0
        if max_score == 0:
            return 'General', 0.6  # Default category
        
        best_categories = [cat for cat, score in scores.items() if score == max_score]
        confidence = min(0.6 + (max_score * 0.05), 0.95)  # Scale confidence based on keyword matches
        
        return best_categories[0], confidence
    
    def _suggest_priority(self, text, sentiment=None):
        """
        Suggest ticket priority based on text analysis.
        
        Args:
            text: Text to analyze
            sentiment: Optional pre-computed sentiment score
            
        Returns:
            Suggested priority level
        """
        # If sentiment not provided, compute it
        if sentiment is None:
            sentiment = self._analyze_sentiment(text)
        
        text = text.lower()
            
        # Check for urgent keywords - severity tiers
        critical_keywords = ['urgent', 'emergency', 'critical', 'immediately', 
                          'security breach', 'hack', 'data loss', 'unable to work',
                          'production down', 'system down', 'complete failure']
        
        high_keywords = ['broken', 'not working', 'failed', 'error',
                       'asap', 'important', 'serious', 'affecting work', 
                       'preventing', 'significant issue', 'major problem']
        
        medium_keywords = ['problem', 'issue', 'bug', 'fault', 'doesn\'t work correctly',
                         'intermittent', 'slow', 'delayed', 'inconvenient']
        
        # Context detection - determine if issue is business critical
        business_impact_terms = ['all users', 'everyone', 'company wide', 'production',
                               'customer', 'deadline', 'revenue', 'urgent', 'meeting',
                               'presentation', 'unable to continue']
        
        # Count keyword matches in each category
        critical_count = sum(1 for keyword in critical_keywords if keyword in text)
        high_count = sum(1 for keyword in high_keywords if keyword in text)
        medium_count = sum(1 for keyword in medium_keywords if keyword in text)
        business_impact = sum(1 for term in business_impact_terms if term in text)
        
        # Determine priority based on keywords, sentiment and business impact
        if critical_count >= 1 or (business_impact >= 2 and high_count >= 1) or sentiment < -0.7:
            return 'critical'
        elif high_count >= 2 or (business_impact >= 1 and medium_count >= 2) or sentiment < -0.4:
            return 'high'
        elif medium_count >= 1 or high_count >= 1 or sentiment < -0.1:
            return 'medium'
        else:
            return 'low'
            
    def _suggest_staff(self, text, category):
        """
        Suggest appropriate staff based on ticket content and category.
        
        Args:
            text: Ticket description text
            category: The ticket category
            
        Returns:
            Username of suggested staff member
        """
        # Try to find staff users with matching expertise
        try:
            # Get department related to the category
            category_obj = Category.objects.filter(name__icontains=category).first()
            if category_obj and category_obj.department:
                # Find staff in the department
                staff_users = User.objects.filter(
                    profile__department=category_obj.department,
                    profile__role__is_staff=True,
                    is_active=True
                )
                
                if staff_users:
                    # For simplicity, return the username of the first staff user
                    # In a real system, would use more sophisticated assignment logic
                    return staff_users.first().username
            
            # If no department-specific staff found, return a general staff user
            general_staff = User.objects.filter(
                profile__role__is_staff=True,
                is_active=True
            ).first()
            
            if general_staff:
                return general_staff.username
                
        except Exception as e:
            logger.error(f"Error in staff suggestion: {e}")
        
        # Default - no staff suggested
        return None
    
    def get_suggestion(self, ticket_id):
        """
        Get AI suggestions for a ticket.
        
        Args:
            ticket_id: ID of the ticket
            
        Returns:
            Dictionary of AI suggestions or error message
        """
        try:
            analysis = AIAnalysis.objects.get(ticket_id=ticket_id)
            result = {
                'sentiment_score': analysis.sentiment_score,
                'suggested_category': analysis.suggested_category,
                'suggested_priority': analysis.suggested_priority,
            }
            
            # Safely add confidence score from category_confidence field
            if hasattr(analysis, 'category_confidence') and analysis.category_confidence is not None:
                result['confidence_score'] = analysis.category_confidence
            
            # Add department info if available
            if hasattr(analysis, 'suggested_department') and analysis.suggested_department:
                result['suggested_department'] = analysis.suggested_department.name
            elif analysis.ticket and analysis.ticket.department:
                result['suggested_department'] = analysis.ticket.department.name
                
            # Add staff suggestion if available
            if hasattr(analysis, 'suggested_assignee') and analysis.suggested_assignee:
                result['suggested_staff'] = analysis.suggested_assignee.username
                
            return result
        except AIAnalysis.DoesNotExist:
            return {
                'error': 'No AI analysis available for this ticket'
            }
    
    def generate_response(self, ticket):
        """
        Generate an automated response for a ticket.
        
        Args:
            ticket: Ticket object
            
        Returns:
            Generated response text
        """
        if not GOOGLE_CLOUD_AVAILABLE or not self.vertex_model:
            # Fallback to template-based response
            return self._fallback_response_generation(ticket)
        
        try:
            # Create a prompt for Gemini
            prompt = f"""
            You are an IT support assistant generating a helpful response to a ticket.
            
            Ticket Information:
            - ID: {ticket.ticket_id}
            - Title: {ticket.title}
            - Description: {ticket.description}
            - Category: {ticket.category.name if ticket.category else 'Uncategorized'}
            - Priority: {ticket.priority}
            
            Generate a professional, helpful response that:
            1. Acknowledges the issue
            2. Provides initial troubleshooting steps or asks for clarifying information if needed
            3. Sets appropriate expectations for resolution
            4. Has a professional tone
            5. Is concise (maximum 100 words)
            
            Do not include any placeholders or text in brackets.
            """
            
            response = self.vertex_model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error in response generation: {e}")
            return self._fallback_response_generation(ticket)
    
    def _fallback_response_generation(self, ticket):
        """
        Generate response based on templates as fallback.
        
        Args:
            ticket: Ticket object
            
        Returns:
            Template-based response text
        """
        # Get category name safely
        category_name = ticket.category.name if ticket.category else "your issue"
        
        # Select template based on priority
        if ticket.priority == 'critical':
            template = f"""
            Thank you for reporting this critical issue regarding {category_name}. We're treating this with highest priority and a technician has been assigned to investigate immediately. We'll provide updates as soon as possible. If you have any additional information that might help us resolve this faster, please let us know.
            
            Reference: {ticket.ticket_id}
            """
        elif ticket.priority == 'high':
            template = f"""
            Thank you for submitting your ticket about {category_name}. This has been classified as high priority and we'll begin working on it promptly. A technician will review your issue within the next few hours. Please provide any additional details that might help us understand the problem better.
            
            Reference: {ticket.ticket_id}
            """
        else:
            template = f"""
            Thank you for contacting IT support about {category_name}. We've received your ticket and it will be assigned to an appropriate technician. Our typical response time is within 24 hours. If you have any additional information to add, please reply to this ticket.
            
            Reference: {ticket.ticket_id}
            """
        
        return template.strip()
    
    def generate_automatic_comment(self, ticket):
        """
        Generate an AI response/comment for a ticket based on its content.
        
        Args:
            ticket: The ticket object to generate a comment for
            
        Returns:
            Generated comment text as a string
        """
        try:
            # Analyze ticket content
            category_name, _ = self._fallback_classification(ticket.description)
            sentiment = self._analyze_sentiment(ticket.description)
            priority = self._suggest_priority(ticket.description, sentiment)
            
            # Get ticket details
            ticket_id = ticket.ticket_id
            title = ticket.title
            
            # Build response templates based on ticket category and content
            templates = {
                'Hardware': [
                    f"I've analyzed your hardware issue with ticket ID {ticket_id}. Based on your description, this appears to be a {priority} priority hardware problem. Our IT team will examine this shortly. In the meantime, please try basic troubleshooting steps like checking connections and restarting the device.",
                    f"Thank you for reporting this hardware issue. Your ticket ({ticket_id}) has been classified as a {priority} priority task. A technician will be assigned to investigate the hardware problem described in '{title}'.",
                    f"Your hardware-related ticket ({ticket_id}) has been received and categorized as {priority} priority. The IT hardware team has been notified and will address this issue according to our service level agreement."
                ],
                'Software': [
                    f"I've reviewed your software issue (ticket {ticket_id}). This has been classified as {priority} priority. Before a technician contacts you, please try closing all applications, restarting the software, and clearing your browser cache if web-related.",
                    f"Your software issue '{title}' (ID: {ticket_id}) has been logged with {priority} priority. The software support team will investigate. It may help to check if any recent updates were installed before the issue started.",
                    f"Thank you for submitting ticket {ticket_id} regarding the software issue. It has been assigned {priority} priority. Please ensure your software is updated to the latest version while waiting for technical assistance."
                ],
                'Network': [
                    f"We've received your network-related ticket ({ticket_id}). It has been categorized as {priority} priority. While waiting for support, please try restarting your router/modem and verifying your network cables are securely connected.",
                    f"Your network issue '{title}' (ID: {ticket_id}) has been registered with {priority} priority. The network team has been notified. In the meantime, please check if other devices are experiencing similar issues.",
                    f"Network issue ticket {ticket_id} has been logged and assigned {priority} priority. Please try power cycling your network equipment while waiting for a network specialist to investigate."
                ],
                'Account': [
                    f"Your account-related ticket ({ticket_id}) has been received and assigned {priority} priority. For security reasons, please do not share your password or security details in any follow-up communications.",
                    f"We've registered your account issue (ticket ID: {ticket_id}) with {priority} priority. The account management team will review this shortly. Please note any recent changes you made to your account settings.",
                    f"Thank you for reporting this account issue. Your ticket ({ticket_id}) has been classified as {priority} priority. While you wait, please verify your account details and ensure you're using the correct credentials."
                ],
                'Security': [
                    f"Your security concern (ticket {ticket_id}) has been escalated with {priority} priority. Please immediately change any potentially compromised passwords and do not click on suspicious links or attachments.",
                    f"Security issue ticket {ticket_id} has been logged with {priority} priority. Our security team has been notified and will investigate promptly. Please limit use of the affected system until we resolve this issue.",
                    f"We've received your security-related ticket ({ticket_id}) and categorized it as {priority} priority. For your protection, please enable two-factor authentication if available while our team investigates."
                ],
                'General': [
                    f"Thank you for submitting ticket {ticket_id}. We've reviewed your request and assigned it {priority} priority. A support representative will contact you according to our service level agreement.",
                    f"Your ticket ({ticket_id}) has been received and is being processed with {priority} priority. Our team will address your concerns as outlined in '{title}'.",
                    f"We've logged your request (ID: {ticket_id}) with {priority} priority. A support team member will be assigned to your case and will follow up with you shortly."
                ]
            }
            
            # Select template based on category
            category_templates = templates.get(category_name, templates['General'])
            
            # Add timestamp to comment
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Choose a template and format with ticket information
            import random
            response = random.choice(category_templates)
            
            # Add SLA information based on priority
            sla_info = {
                'critical': "Based on our SLA, critical issues are addressed within 2 hours.",
                'high': "According to our SLA, high priority issues are resolved within 8 hours.",
                'medium': "As per our SLA, medium priority issues are addressed within 24 hours.",
                'low': "Following our SLA, low priority issues are typically resolved within 48 hours."
            }
            
            response += f" {sla_info.get(priority, '')}"
            
            # Sign off
            response += f"\n\nTimestamp: {timestamp}\nAI Assistant"
            
            return response
            
        except Exception as e:
            # Fallback response in case of errors
            print(f"Error generating automatic comment: {str(e)}")
            return "Thank you for your ticket submission. Our team will review your request and respond as soon as possible according to our service level agreement."
    
    def record_feedback(self, ticket_id, feedback_type, is_correct, corrected_value=None, provided_by=None):
        """
        Record feedback about AI suggestions.
        
        Args:
            ticket_id: ID of the ticket
            feedback_type: Type of feedback (category, priority, staff)
            is_correct: Whether the AI suggestion was correct
            corrected_value: The correct value if AI was wrong
            provided_by: User who provided the feedback
            
        Returns:
            Created AIFeedback object or None if error
        """
        try:
            # Get the ticket and its AI analysis
            ticket = Ticket.objects.get(id=ticket_id)
            analysis = AIAnalysis.objects.get(ticket=ticket)
            
            # Create and return feedback record
            return AIFeedback.objects.create(
                ticket=ticket,
                ai_analysis=analysis,
                feedback_type=feedback_type,
                is_correct=is_correct,
                corrected_value=corrected_value,
                provided_by=provided_by
            )
        except (Ticket.DoesNotExist, AIAnalysis.DoesNotExist) as e:
            logger.error(f"Error recording AI feedback: {e}")
            return None
    
    def calculate_model_accuracy(self):
        """
        Calculate accuracy metrics based on feedback.
        
        Returns:
            Dictionary with accuracy metrics
        """
        try:
            # Get all feedback
            all_feedback = AIFeedback.objects.all()
            total_count = all_feedback.count()
            
            if total_count == 0:
                return {
                    'overall_accuracy': 0,
                    'category_accuracy': 0,
                    'priority_accuracy': 0,
                    'staff_accuracy': 0,
                    'feedback_count': 0
                }
            
            # Count correct predictions
            correct_count = all_feedback.filter(is_correct=True).count()
            
            # Calculate type-specific accuracy
            category_feedback = all_feedback.filter(feedback_type='category')
            category_correct = category_feedback.filter(is_correct=True).count()
            category_accuracy = category_correct / category_feedback.count() if category_feedback.exists() else 0
            
            priority_feedback = all_feedback.filter(feedback_type='priority')
            priority_correct = priority_feedback.filter(is_correct=True).count()
            priority_accuracy = priority_correct / priority_feedback.count() if priority_feedback.exists() else 0
            
            staff_feedback = all_feedback.filter(feedback_type='staff')
            staff_correct = staff_feedback.filter(is_correct=True).count()
            staff_accuracy = staff_correct / staff_feedback.count() if staff_feedback.exists() else 0
            
            # Overall accuracy
            overall_accuracy = correct_count / total_count
            
            return {
                'overall_accuracy': overall_accuracy,
                'category_accuracy': category_accuracy,
                'priority_accuracy': priority_accuracy,
                'staff_accuracy': staff_accuracy,
                'feedback_count': total_count
            }
            
        except Exception as e:
            logger.error(f"Error calculating accuracy metrics: {e}")
            return {
                'error': str(e)
            }
    
    def auto_assign_ticket(self, ticket):
        """
        Automatically assign a ticket based on AI suggestions.
        
        Args:
            ticket: Ticket object to assign
            
        Returns:
            Boolean indicating success
        """
        try:
            # Only proceed if ticket is unassigned
            if ticket.assigned_to is not None:
                return False
            
            # Get the AI analysis for this ticket
            analysis = AIAnalysis.objects.filter(ticket=ticket).first()
            if not analysis or analysis.category_confidence < 0.8:
                return False  # Only auto-assign if high confidence
            
            # Find suggested staff user
            if analysis.suggested_staff:
                try:
                    staff_user = User.objects.get(username=analysis.suggested_staff)
                    # Assign ticket
                    ticket.assigned_to = staff_user
                    
                    # Also update category if one was suggested and confidence is high
                    if analysis.suggested_category and analysis.category_confidence > 0.85:
                        category = Category.objects.filter(
                            name__icontains=analysis.suggested_category
                        ).first()
                        
                        if category:
                            ticket.category = category
                    
                    # Update priority if suggested
                    if analysis.suggested_priority:
                        ticket.priority = analysis.suggested_priority
                    
                    # Save changes
                    ticket.save(update_fields=['assigned_to', 'category', 'priority'])
                    return True
                    
                except User.DoesNotExist:
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error in auto-assigning ticket: {e}")
            return False
