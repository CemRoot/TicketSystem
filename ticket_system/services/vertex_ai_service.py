"""
Google Vertex AI / Gemini integration for the ticket system.

This service is responsible for AI-powered ticket analysis and response generation
using Google's Vertex AI and Gemini models.
"""
import os
import json
from pathlib import Path
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from django.conf import settings
from django.contrib.auth.models import User
import re
# Import models needed for database queries
from ticket_system.models import Department, Category
import google.api_core.exceptions
import time

# The credential file path
CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, 'credentials', 'google-credentials.json')

class VertexAIService:
    """Integration with Google's Vertex AI and Gemini models for ticket analysis."""
    
    def __init__(self):
        """Initialize the Vertex AI service with appropriate credentials."""
        # Initialize Vertex AI with project and location from credentials
        try:
            # Check if credentials file exists and has content
            if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 10:
                self._initialize_vertexai()
                self.model = GenerativeModel("gemini-1.5-pro")
                self.is_available = True
            else:
                print("Google credentials file is empty or not properly configured")
                self.is_available = False
            
            # Configure fallback settings
            self.fallback_enabled = True  # Enable fallback by default
            self.max_retries = 3  # Maximum number of retries
            self.retry_delay = 2  # Base delay between retries in seconds
        except Exception as e:
            print(f"Error initializing Vertex AI: {str(e)}")
            self.is_available = False
    
    def _initialize_vertexai(self):
        """Initialize Vertex AI with Google Cloud credentials."""
        try:
            # Read credentials file
            with open(CREDENTIALS_PATH, 'r') as f:
                credentials = json.load(f)
            
            # Initialize Vertex AI
            vertexai.init(
                project=credentials.get('project_id', ''),
                location="us-central1",  # Default region
            )
        except Exception as e:
            print(f"Failed to initialize Vertex AI: {str(e)}")
            raise
    
    def _call_with_fallback(self, prompt, fallback_prompt=None):
        """
        Call Gemini with fallback retry logic for 429 errors.
        
        Args:
            prompt: The prompt to send to the model
            fallback_prompt: Optional simpler prompt to use as fallback
            
        Returns:
            Response text or None if all attempts fail
        """
        if not self.is_available:
            return None
            
        # Use provided prompt or the original
        current_prompt = prompt
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                response = self.model.generate_content(current_prompt)
                return response.text.strip()
            except google.api_core.exceptions.ResourceExhausted as e:
                # Handle 429 error specifically
                retry_count += 1
                print(f"Resource exhausted (429) error, attempt {retry_count} of {self.max_retries}")
                
                # If this was the last retry with original prompt and we have a fallback
                if retry_count == 1 and fallback_prompt:
                    print("Trying simpler fallback prompt...")
                    current_prompt = fallback_prompt
                
                # If we've exhausted all retries
                if retry_count >= self.max_retries:
                    print("All retries exhausted, returning simpler response")
                    # Return a generic response as last resort
                    if "ticket" in prompt.lower():
                        return json.dumps({
                            "suggested_department_name": "IT",
                            "suggested_category_name": "General",
                            "suggested_priority": "medium",
                            "sentiment_score": 0.0,
                            "confidence_score": 0.5
                        })
                    else:
                        return "I apologize, but I'm currently experiencing technical limitations. A human agent will review your ticket shortly."
                
                # Wait before retrying with exponential backoff
                wait_time = self.retry_delay * (2 ** (retry_count - 1))
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            
            except Exception as e:
                # Handle other errors
                print(f"Error calling Gemini: {str(e)}")
                return None
        
        return None
    
    def analyze_ticket(self, title, description):
        """
        Analyze ticket content using Gemini to determine appropriate 
        department, category, and priority.
        
        Args:
            title: Ticket title
            description: Ticket description
            
        Returns:
            Dict containing suggested department, category, priority and confidence scores
        """
        if not self.is_available:
            return None
            
        try:
            # Create prompt for Gemini
            prompt = f"""
            You are a ticket analysis system. Analyze this support ticket and determine:
            1. The most appropriate department (choose from: IT, HR, Finance, Legal, Sales, Marketing, Customer Support)
            2. The most appropriate category (choose from: Hardware, Software, Network, Account, Security, General)
            3. The appropriate priority level (choose from: low, medium, high, critical)
            
            Ticket Title: {title}
            Ticket Description: {description}
            
            Provide your analysis in the following JSON format only, with no other text or explanation:
            {{
                "department": "department_name",
                "category": "category_name",
                "priority": "priority_level",
                "confidence_score": 0.85
            }}
            """
            
            # Send request to Gemini
            response_text = self._call_with_fallback(prompt)
            
            # Extract JSON from response
            try:
                result_text = response_text
                # Find JSON content (it might be wrapped in code blocks)
                if "```json" in result_text:
                    json_str = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    json_str = result_text.split("```")[1].strip()
                else:
                    json_str = result_text.strip()
                
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError:
                print(f"Error parsing JSON from response: {response_text}")
                return None
                
        except Exception as e:
            print(f"Error analyzing ticket with Vertex AI: {str(e)}")
            return None
    
    def generate_response(self, ticket):
        """
        Generate an AI response that attempts to solve the ticket issue.
        
        Args:
            ticket: The ticket object
            
        Returns:
            String containing the AI-generated response
        """
        if not self.is_available:
            return "AI response generation is currently unavailable."
            
        # Create prompt for Gemini
        prompt = f"""
        Role:
        You are an expert IT support assistant helping with a ticket in our system.
        
        Objectives:
        1. Understand the ticket content and provide thoughtful assistance.
        2. Respond like a helpful IT assistant: Start with a friendly greeting (e.g., "Hello! I'm the AI Assistant 👋"). Be clear and professional. DO NOT use markdown formatting like asterisks for bold or italic text. Use relevant emojis sparingly if appropriate (like ✅, 📡, 🔐, 🔄, 👍).
        3. Provide actionable steps or clear information.
        
        Ticket Details:
        Ticket ID: {ticket.ticket_id}
        Title: {ticket.title}
        Description: {ticket.description}
        Status: {ticket.status}
        Category: {ticket.category.name if ticket.category else "Uncategorized"}
        Department: {ticket.department.name if ticket.department else "Unassigned"}
        
        Your response should:
        1. Greet the user and introduce yourself as the AI system
        2. Acknowledge their issue
        3. Provide initial troubleshooting steps or request more information if needed
        4. Includes specific details from the ticket
        5. Mentions any relevant SLA information based on the priority (critical: 2 hours, high: 8 hours, medium: 24 hours, low: 48 hours)
        
        Your Response (No Markdown):
        """
        
        # Create a simpler fallback prompt for rate limiting cases
        fallback_prompt = f"""
        You are an IT support assistant. Write a brief response acknowledging receipt of this ticket:
        
        Ticket ID: {ticket.ticket_id}
        Title: {ticket.title}
        
        Keep it under 3 sentences and don't use markdown formatting.
        """
        
        try:
            # Use the call_with_fallback method
            response_text = self._call_with_fallback(prompt, fallback_prompt)
            
            # Add signature to the response (no need for this now as it's in the prompt)
            if response_text and not "AI Support Assistant" in response_text:
                response_text += "\n\n-- AI Support Assistant"
            
            return response_text
                
        except Exception as e:
            print(f"Error generating response with Vertex AI: {e}")
            return "I apologize, but I'm currently experiencing technical limitations. A human agent will review your ticket shortly."
    
    def suggest_assignee(self, ticket):
        """
        Suggest which team/department should be assigned to the ticket based on content.
        
        Args:
            ticket: The ticket object
            
        Returns:
            Dict containing suggested assignee info
        """
        if not self.is_available:
            return None
            
        try:
            # Create prompt for Gemini
            prompt = f"""
            You are a ticket routing system. Based on this support ticket, determine which team should handle this issue.
            
            Ticket Title: {ticket.title}
            Ticket Description: {ticket.description}
            Category: {ticket.category.name if ticket.category else "Uncategorized"}
            Department: {ticket.department.name if ticket.department else "Unassigned"}
            
            Provide your analysis in the following JSON format only, with no other text:
            {{
                "assigned_team": "team_name",
                "reason": "brief explanation of why this team",
                "confidence_score": 0.85
            }}
            
            Team options: IT Team, Finance Team, HR Team, Development Team, Legal Team, Sales Team, General Support
            """
            
            # Send request to Gemini
            response_text = self._call_with_fallback(prompt)
            
            # Extract JSON from response
            try:
                result_text = response_text
                # Find JSON content (it might be wrapped in code blocks)
                if "```json" in result_text:
                    json_str = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    json_str = result_text.split("```")[1].strip()
                else:
                    json_str = result_text.strip()
                
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError:
                print(f"Error parsing JSON from response: {response_text}")
                return None
                
        except Exception as e:
            print(f"Error suggesting assignee with Vertex AI: {e}")
            return None

    def get_ai_user(self):
        """Gets or creates the AI Assistant user."""
        user, created = User.objects.get_or_create(
            username='ai.assistant',
            defaults={
                'email': 'ai.assistant@ticketsystem.com',
                'first_name': 'AI',
                'last_name': 'Assistant',
                'is_staff': True  # Important for potential internal actions
            }
        )
        return user

    def generate_conversation_response(self, ticket, comments):
        """Generates the next response in the conversation."""
        if not self.is_available:
            return "AI response generation is currently unavailable."

        MAX_GEMINI_MESSAGES = 5 # Define the limit

        # Check if conversation limit reached (handled in the view, but good practice)
        # if ticket.gemini_message_count >= MAX_GEMINI_MESSAGES:
        #    return self.generate_escalation_suggestion(ticket, comments) # Handled by caller view

        conversation_history = f"Ticket Title: {ticket.title}\nDescription: {ticket.description}\nStatus: {ticket.get_status_display()}\nPriority: {ticket.get_priority_display()}\n\n--- Conversation History ---\n"
        # Ensure comments are ordered correctly when passed to this function
        for comment in comments.order_by('created_at'):
             prefix = "User" if comment.user == ticket.created_by else ("AI Assistant" if comment.user.username == 'ai.assistant' else "Staff")
             conversation_history += f"{prefix} ({comment.created_at.strftime('%Y-%m-%d %H:%M')}): {comment.content}\n"
        conversation_history += "\n--- End History ---"

        prompt = f"""
        Role:
        You are an expert IT support assistant for ticket {ticket.ticket_id}.
        
        Objectives:
        1. Review the conversation history and provide the next helpful response.
        2. Respond like a helpful IT assistant: Be clear and professional. DO NOT use markdown formatting like asterisks for bold or italic text. Use relevant emojis sparingly if appropriate (like ✅, 📡, 🔐, 🔄, 👍).
        3. Provide actionable steps or clear information based on the conversation context.

        Conversation Context:
        {conversation_history}

        Based *only* on the information above, provide the *next* helpful and concise response (max 100 words).
        - If the last message was from the user, respond directly to their query or statement.
        - If the last message was from you (AI Assistant) or Staff, and the user hasn't replied with new info, gently ask for clarification or state you are awaiting their input.
        - Provide specific troubleshooting steps if appropriate based on the user's last comment.
        - Ask clarifying questions if needed.
        - Maintain a helpful and professional tone.
        - Do *not* suggest escalating yet in this response.

        Your next response (No Markdown):
        """
        try:
            response_text = self._call_with_fallback(prompt)
            response_text = response_text.strip()
            # Simple cleaning for conversational response
            lines = response_text.split('\n')
            # Remove potential Gemini meta-text if any, adjust as needed
            cleaned_lines = [line for line in lines if not line.strip().startswith(("Constraint Checklist", "Confidence Score:"))]
            final_response = "\n".join(cleaned_lines).strip()

            if not "AI Support Assistant" in final_response:
                final_response += "\n\n-- AI Support Assistant" # Add signature
            return final_response

        except Exception as e:
            print(f"Error generating conversation response: {e}")
            return "I encountered an issue trying to generate a response. A human agent will review your comment shortly."

    def generate_escalation_suggestion(self, ticket, comments):
        """Generates an escalation message when the conversation limit is reached."""
        if not self.is_available:
            return "AI service unavailable."

        conversation_history = f"Ticket Title: {ticket.title}\nDescription: {ticket.description}\nStatus: {ticket.get_status_display()}\nPriority: {ticket.get_priority_display()}\n\n--- Conversation History ---\n"
        for comment in comments.order_by('created_at'):
            prefix = "User" if comment.user == ticket.created_by else ("AI Assistant" if comment.user.username == 'ai.assistant' else "Staff")
            conversation_history += f"{prefix} ({comment.created_at.strftime('%Y-%m-%d %H:%M')}): {comment.content}\n"
        conversation_history += "\n--- End History ---"

        # Define possible target departments/teams
        possible_departments = ["IT Support", "Development", "HR", "Finance", "Network Team", "Security Team"]  # Customize this list

        prompt = f"""
        You are an IT support assistant analyzing ticket {ticket.ticket_id}.
        The automated conversation limit has been reached, and the issue is not yet resolved.
        Review the ticket details and conversation history:

        {conversation_history}

        Based on the conversation, determine the single *most appropriate* team or department to escalate this ticket to for resolution. Choose *only* from the following list: {', '.join(possible_departments)}.

        Provide your response in the following JSON format ONLY, with no other text or explanation:
        {{
            "escalation_message": "A message to the user explaining the escalation.",
            "suggested_department": "The name of the department from the list provided."
        }}

        The escalation_message should clearly state that you couldn't resolve it and are escalating it to the relevant team (mention the team name you choose).
        """
        try:
            response_text = self._call_with_fallback(prompt)
            response_text = response_text.strip()
            # Extract JSON
            json_str = response_text
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].strip()

            result = json.loads(json_str)
            return result  # Returns dict with 'escalation_message' and 'suggested_department'

        except Exception as e:
            print(f"Error generating escalation suggestion: {e}")
            # Fallback message
            return {
                "escalation_message": "I haven't been able to resolve this issue after several attempts. I am now routing this ticket to the appropriate support team for further assistance.",
                "suggested_department": "IT Support"  # Default fallback
            }

    def analyze_comment_for_resolution(self, comment_text):
        """Analyzes if a user comment indicates resolution."""
        if not self.is_available:
            return False  # Default to not resolved if AI unavailable

        prompt = f"""
        Analyze the following user comment from a support ticket.
        Determine if the user is clearly stating that their reported problem has been fixed or resolved.
        Focus on explicit confirmation of resolution. Ignore simple thank yous if they don't confirm the fix.

        User Comment: "{comment_text}"

        Respond with only 'YES' if the comment clearly indicates the issue is resolved, or 'NO' otherwise. Do not provide explanations.
        Response:
        """
        try:
            response_text = self._call_with_fallback(prompt)
            decision = response_text.strip().upper()
            print(f"Resolution Analysis for comment '{comment_text[:50]}...': AI decision = {decision}")
            return decision == 'YES'
        except Exception as e:
            print(f"Error analyzing resolution intent: {e}")
            return False  # Default to NO on error

    def suggest_initial_fields(self, title, description):
        """
        Suggests Department, Category, Priority from initial text, using DB options.
        """
        # Fetch all departments and categories from the database
        departments = list(Department.objects.values_list('name', flat=True))
        categories = list(Category.objects.filter(is_active=True).values_list('name', flat=True))
        
        if not departments:
            departments = ["IT", "HR", "Finance", "Support"]
        if not categories:
            categories = ["Hardware", "Software", "Access", "General"]
        
        prompt = f"""
        Analyze the following IT support ticket draft:
        
        Title: {title}
        Description: {description}
        
        Available Options (Choose ONLY from these lists):
        * Departments: {', '.join(departments)}
        * Categories: {', '.join(categories)}
        * Priorities: low, medium, high, critical
        * Sentiment Scores: -1.0 (very negative) to 1.0 (very positive)

        Instructions:
        1. Analyze the core problem described.
        2. Select the SINGLE MOST SPECIFIC APPROPRIATE Department for this issue.
        3. Select the SINGLE MOST SPECIFIC APPROPRIATE Category for this issue.
        4. **Crucially:** If the user mentions inability to access systems, prioritize category options related to "Access", "Security", or "Account" if available.
        5. Determine the most appropriate Priority level based on business impact.
        6. Estimate the user's Sentiment Score based on their language (e.g., frustration, urgency).

        Example 1 (Access Issue):
        Title: Can't log in to CRM
        Description: Getting invalid password error on crm.company.com. Reset link isn't working.
        Output: {{ "suggested_department_name": "IT", "suggested_category_name": "Account Access", "suggested_priority": "high", "sentiment_score": -0.7, "confidence_score": 0.85 }}

        Example 2 (Network Issue):
        Title: Slow internet in office
        Description: The wifi connection in the main conference room is extremely slow today.
        Output: {{ "suggested_department_name": "IT", "suggested_category_name": "Network & Infrastructure", "suggested_priority": "medium", "sentiment_score": -0.3, "confidence_score": 0.75 }}

        Your Analysis (Respond ONLY with JSON):
        Provide your suggestions in the following JSON format ONLY, with no other text or explanation:
        {{
            "suggested_department_name": "department_name_from_list",
            "suggested_category_name": "category_name_from_list",
            "suggested_priority": "priority_level",
            "sentiment_score": 0.5,
            "confidence_score": 0.85
        }}
        Use null if a field cannot be confidently determined from the text AND the available options.
        """
        try:
            # Ensure the Gemini model is initialized
            if not self.model:
               print("Error: Gemini model not initialized in VertexAIService.")
               return None

            print(f"Sending prompt to Gemini for initial suggestions...")
            response_text = self._call_with_fallback(prompt)
            print(f"Received raw response from Gemini: {response_text}")

            # --- Robust JSON Extraction ---
            json_str = None
            # Try finding JSON within markdown blocks first
            match = re.search(r"```json\s*({.*?})\s*```", response_text, re.DOTALL)
            if match:
                json_str = match.group(1)
                print("Extracted JSON from markdown block.")
            else:
                # If no markdown, try finding the first '{' and last '}'
                start = response_text.find('{')
                end = response_text.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = response_text[start:end+1]
                    print("Extracted JSON by finding braces.")
                else:
                     print("Could not find JSON structure in response.")
                     return None # Cannot proceed without JSON

            if json_str:
                try:
                    result = json.loads(json_str)
                    # Validate or normalize the result if necessary
                    result['suggested_department_name'] = result.get('suggested_department_name')
                    result['suggested_category_name'] = result.get('suggested_category_name')
                    result['suggested_priority'] = result.get('suggested_priority')
                    result['sentiment_score'] = result.get('sentiment_score', 0.0)
                    result['confidence_score'] = result.get('confidence_score', 0.0)
                    print(f"Successfully parsed suggestions including sentiment/confidence: {result}")
                    return result
                except json.JSONDecodeError as json_e:
                    print(f"JSON Decode Error: {json_e}")
                    print(f"Failed JSON string was: >>>{json_str}<<<")
                    return None # Parsing failed
            else:
                 return None # No JSON found

        except Exception as e:
            # Catch errors during the API call or processing
            print(f"Error suggesting initial fields with Vertex AI: {e}")
            # Optionally: Log the full exception traceback
            import traceback
            traceback.print_exc()
            return None # Return None on error

    def generate_closing_confirmation(self, ticket_id):
        """Generates a standard closing confirmation message."""
        # This could be a simple template or another Gemini call if needed
        return f"Thank you for confirming. I have now closed ticket {ticket_id}. If the issue persists or you encounter further problems, please feel free to open a new ticket. If you believe this was closed in error, please contact an administrator."
