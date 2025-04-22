"""
Views for the ticket management system.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, FloatField, DurationField, Sum, Case, When, IntegerField
from django.http import Http404, JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics, permissions, status, filters, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied

# Custom permission classes
class IsStaffUser(permissions.BasePermission):
    """
    Permission to only allow staff users to access the view.
    """
    def has_permission(self, request, view):
        return request.user and (request.user.is_staff or 
                                (hasattr(request.user, 'profile') and 
                                 request.user.profile.role and 
                                 request.user.profile.role.is_staff))

from .models import (
    Ticket, TicketComment, TicketAttachment, TicketEscalation,
    Department, Category, SubCategory, Role, UserProfile,
    Notification, SystemLog, AIAnalysis, ModelUsageStats,
    SLA, TicketUpdate
)
from .forms import (
    UserRegistrationForm, UserProfileForm, AdminUserCreateForm,
    TicketForm, TicketCommentForm, TicketAttachmentForm, TicketFilterForm,
    DepartmentForm, CategoryForm, SubCategoryForm, RoleForm, DateRangeForm
)
from .serializers import (
    TicketListSerializer, TicketDetailSerializer, TicketCreateUpdateSerializer,
    TicketCommentSerializer, TicketAttachmentSerializer, UserSerializer,
    DepartmentSerializer, CategorySerializer, NotificationSerializer
)
from .services.ticket_service import TicketService
from .services.user_service import UserService
from .services.ai_service import AIService
from .services.vertex_ai_service import VertexAIService


# Authentication Views
@csrf_exempt
def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Log the login
                SystemLog.objects.create(
                    user=user,
                    level='info',
                    component='auth',
                    action='User login',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                # Redirect to intended page or dashboard
                next_page = request.GET.get('next', 'dashboard')
                return redirect(next_page)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    
    return render(request, 'ticket_system/auth/login.html', {'form': form})


def logout_view(request):
    """Handle user logout."""
    if request.user.is_authenticated:
        # Log the logout
        SystemLog.objects.create(
            user=request.user,
            level='info',
            component='auth',
            action='User logout',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        logout(request)
    
    messages.info(request, "You have successfully logged out.")
    return redirect('login')


def register_view(request):
    """Handle new user registration."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(
                user=user,
                department=form.cleaned_data.get('department'),
                phone_number=form.cleaned_data.get('phone_number')
            )
            # Log the registration
            SystemLog.objects.create(
                user=user,
                level='info',
                component='auth',
                action='User registration',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Account created for {user.username}. You can now log in.")
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'ticket_system/auth/register.html', {'form': form})


def password_reset_view(request):
    """Handle password reset request."""
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            user_service = UserService()
            try:
                user_service.send_password_reset(email)
                messages.success(request, 'Password reset instructions have been sent to your email.')
                return redirect('login')
            except User.DoesNotExist:
                # Still show success to prevent email enumeration
                messages.success(request, 'Password reset instructions have been sent to your email.')
                return redirect('login')
    else:
        form = PasswordResetForm()
    return render(request, 'ticket_system/auth/password_reset.html', {'form': form})


@login_required
def profile_view(request):
    """Display user profile."""
    user = request.user
    
    # Get user's tickets
    created_tickets = Ticket.objects.filter(created_by=user).order_by('-created_at')[:5]
    assigned_tickets = Ticket.objects.filter(assigned_to=user).order_by('-created_at')[:5]
    
    # Get user's activity logs
    activity_logs = SystemLog.objects.filter(user=user).order_by('-created_at')[:10]
    
    context = {
        'user': user,
        'created_tickets': created_tickets,
        'assigned_tickets': assigned_tickets,
        'activity_logs': activity_logs
    }
    
    return render(request, 'ticket_system/auth/profile.html', context)


@login_required
@csrf_exempt
def edit_profile_view(request):
    """Handle editing user profile."""
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'ticket_system/auth/edit_profile.html', {'form': form})


@login_required
def change_password_view(request):
    """Handle changing user password."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in
            
            # Log the password change
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='auth',
                action='Password change',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, "Your password has been changed successfully.")
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'ticket_system/auth/change_password.html', {'form': form})


# Dashboard Views
@login_required
def dashboard_view(request):
    """Display the main dashboard for regular users."""
    user = request.user
    
    # Get counts for dashboard widgets
    if user.profile.role and user.profile.role.is_admin:
        # Admins see all tickets
        if user.profile.role.is_admin:
            # Admin sees all tickets
            open_tickets = Ticket.objects.filter(
                status__in=['new', 'assigned', 'in_progress', 'reopened']
            ).count()
            assigned_tickets = Ticket.objects.filter(assigned_to=user).count()
            tickets_today = Ticket.objects.filter(
                created_at__date=timezone.now().date()
            ).count()
            escalated_tickets = Ticket.objects.filter(is_escalated=True).count()
        else:
            # Staff sees department tickets
            department = user.profile.department
            department_filter = Q(department=department) if department else Q()
            
            open_tickets = Ticket.objects.filter(
                department_filter,
                status__in=['new', 'assigned', 'in_progress', 'reopened']
            ).count()
            assigned_tickets = Ticket.objects.filter(assigned_to=user).count()
            tickets_today = Ticket.objects.filter(
                department_filter,
                created_at__date=timezone.now().date()
            ).count()
            escalated_tickets = Ticket.objects.filter(
                department_filter,
                is_escalated=True
            ).count()
            
        # Get recent tickets (for staff/admin)
        if user.profile.role.is_admin:
            recent_tickets = Ticket.objects.all().order_by('-created_at')[:10]
        else:
            department = user.profile.department
            if department:
                recent_tickets = Ticket.objects.filter(
                    Q(department=department) | Q(assigned_to=user)
                ).distinct().order_by('-created_at')[:10]
            else:
                recent_tickets = Ticket.objects.filter(
                    assigned_to=user
                ).order_by('-created_at')[:10]
                
        # Get tickets with SLA breach
        sla_breach_count = Ticket.objects.filter(
            status__in=['new', 'assigned', 'in_progress', 'reopened'],
            sla_breach=True
        ).count()
        
        # Get unread notifications
        unread_notifications = Notification.objects.filter(
            user=user,
            is_read=False
        ).order_by('-created_at')[:5]
        
        context = {
            'open_tickets': open_tickets,
            'assigned_tickets': assigned_tickets,
            'tickets_today': tickets_today,
            'escalated_tickets': escalated_tickets,
            'sla_breach_count': sla_breach_count,
            'recent_tickets': recent_tickets,
            'unread_notifications': unread_notifications
        }
    else:
        # Regular user dashboard
        open_tickets = Ticket.objects.filter(
            created_by=user,
            status__in=['new', 'assigned', 'in_progress', 'reopened']
        ).count()
        closed_tickets = Ticket.objects.filter(
            created_by=user,
            status__in=['resolved', 'closed']
        ).count()
        
        # Get recent tickets (for regular users)
        recent_tickets = Ticket.objects.filter(
            created_by=user
        ).order_by('-created_at')[:10]
        
        # Get unread notifications
        unread_notifications = Notification.objects.filter(
            user=user,
            is_read=False
        ).order_by('-created_at')[:5]
        
        context = {
            'open_tickets': open_tickets,
            'closed_tickets': closed_tickets,
            'recent_tickets': recent_tickets,
            'unread_notifications': unread_notifications
        }
    
    return render(request, 'ticket_system/dashboard/dashboard.html', context)


@staff_member_required
def admin_dashboard_view(request):
    """Display admin dashboard with statistics."""
    # Get counts for admin dashboard
    total_tickets = Ticket.objects.all().count()
    open_tickets = Ticket.objects.filter(
        status__in=['new', 'assigned', 'in_progress', 'reopened']
    ).count()
    resolved_tickets = Ticket.objects.filter(
        status='resolved'
    ).count()
    closed_tickets = Ticket.objects.filter(
        status='closed'
    ).count()
    
    # Calculate SLA metrics
    total_active = Ticket.objects.filter(
        status__in=['new', 'assigned', 'in_progress', 'reopened']
    ).count()
    
    sla_breach_count = Ticket.objects.filter(
        status__in=['new', 'assigned', 'in_progress', 'reopened'],
        sla_breach=True
    ).count()
    
    sla_breach_percentage = (
        (sla_breach_count / total_active) * 100 if total_active > 0 else 0
    )
    
    # Get ticket distribution by department
    department_distribution = Ticket.objects.values('department__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Get ticket distribution by status
    status_distribution = []
    for status, label in Ticket.STATUS_CHOICES:
        count = Ticket.objects.filter(status=status).count()
        status_distribution.append({
            'label': label,
            'count': count
        })
    
    # Get ticket distribution by priority
    priority_distribution = []
    for priority, label in Ticket.PRIORITY_CHOICES:
        count = Ticket.objects.filter(priority=priority).count()
        priority_distribution.append({
            'label': label,
            'count': count
        })
    
    # Get latest tickets for quick access
    latest_tickets = Ticket.objects.all().order_by('-created_at')[:10]
    
    # Get system logs
    system_logs = SystemLog.objects.filter(
        level__in=['warning', 'error', 'critical']
    ).order_by('-created_at')[:10]
    
    context = {
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'resolved_tickets': resolved_tickets,
        'closed_tickets': closed_tickets,
        'sla_breach_count': sla_breach_count,
        'sla_breach_percentage': sla_breach_percentage,
        'department_distribution': department_distribution,
        'status_distribution': status_distribution,
        'priority_distribution': priority_distribution,
        'latest_tickets': latest_tickets,
        'system_logs': system_logs
    }
    
    return render(request, 'ticket_system/dashboard/admin_dashboard.html', context)


# Ticket Management Views
@login_required
def ticket_list_view(request):
    """Display list of tickets based on user role and filters."""
    user = request.user
    
    # Initialize filter form
    filter_form = TicketFilterForm(request.GET or None)
    
    # Base queryset depends on user role
    if user.profile.role and user.profile.role.is_admin:
        # Admins see all tickets
        tickets = Ticket.objects.all()
    elif user.profile.role and user.profile.role.is_staff:
        # Staff see tickets in their department and assigned to them
        department = user.profile.department
        if department:
            tickets = Ticket.objects.filter(
                Q(department=department) | Q(assigned_to=user)
            ).distinct()
        else:
            tickets = Ticket.objects.filter(assigned_to=user)
    else:
        # Regular users see only their tickets
        tickets = Ticket.objects.filter(created_by=user)
    
    # Apply filters if form is valid
    if filter_form.is_valid():
        data = filter_form.cleaned_data
        
        if data.get('status'):
            tickets = tickets.filter(status=data['status'])
            
        if data.get('priority'):
            tickets = tickets.filter(priority=data['priority'])
            
        if data.get('department'):
            tickets = tickets.filter(department=data['department'])
            
        if data.get('category'):
            tickets = tickets.filter(category=data['category'])
            
        if data.get('created_from'):
            tickets = tickets.filter(created_at__date__gte=data['created_from'])
            
        if data.get('created_to'):
            tickets = tickets.filter(created_at__date__lte=data['created_to'])
            
        if data.get('keyword'):
            keyword = data['keyword']
            tickets = tickets.filter(
                Q(title__icontains=keyword) | 
                Q(description__icontains=keyword) |
                Q(ticket_id__icontains=keyword)
            )
            
        if data.get('is_escalated'):
            tickets = tickets.filter(is_escalated=True)
            
        if data.get('sla_breach'):
            tickets = tickets.filter(sla_breach=True)
    
    # Order tickets by creation date (newest first)
    tickets = tickets.order_by('-created_at')
    
    # Paginate results
    paginator = Paginator(tickets, 20)  # 20 tickets per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prepare context
    context = {
        'filter_form': filter_form,
        'page_obj': page_obj,
        'total_count': tickets.count(),
    }
    
    return render(request, 'ticket_system/tickets/ticket_list.html', context)


@login_required
@csrf_exempt
def create_ticket_view(request):
    """Handle ticket creation."""
    user = request.user
    form = None
    
    if request.method == 'POST':
        # Add source='web' to ensure it's set
        post_data = request.POST.copy()
        if 'source' not in post_data or not post_data['source']:
            post_data['source'] = 'web'
            
        form = TicketForm(post_data, request.FILES)
        
        # Print form data for debugging
        print(f"Form data: {post_data}")
        
        if form.is_valid():
            # Create ticket but don't save to DB yet
            ticket = form.save(commit=False)
            ticket.created_by = user
            
            # Status should always be 'new' on creation
            ticket.status = 'new'
            
            # Set additional metadata
            ticket.source = post_data.get('source', 'web')
            
            # Get SLA settings based on priority
            priority = ticket.priority
            
            try:
                # Apply SLA calculation
                sla = SLA.objects.get(priority=priority)
                response_hours = sla.response_time_hours
                resolution_hours = sla.resolution_time_hours
                
                # Set SLA deadline
                ticket.sla_deadline = timezone.now() + timezone.timedelta(hours=response_hours)
                ticket.resolution_deadline = timezone.now() + timezone.timedelta(hours=resolution_hours)
            except SLA.DoesNotExist:
                # Use default SLA if none found
                print(f"Warning: No SLA found for {priority} priority.")
                # Default: 4 hours for response, 24 hours for resolution
                ticket.sla_deadline = timezone.now() + timezone.timedelta(hours=4)
                ticket.resolution_deadline = timezone.now() + timezone.timedelta(hours=24)
            
            # Save ticket first to get a valid ID, we'll update it after AI analysis
            ticket.save()
            
            # Create initial TicketUpdate record
            TicketUpdate.objects.create(
                ticket=ticket,
                updated_by=user,
                status='new',
                comment=f"Ticket created by {user.get_full_name() or user.username}",
                internal=False
            )
            
            # --- Assign to AI Assistant ---
            vertex_ai = VertexAIService() # Ensure service is initialized
            ai_user = vertex_ai.get_ai_user()
            if ai_user:
                ticket.assigned_to = ai_user
                ticket.first_assigned_at = timezone.now() # Set assignment time
                ticket.status = 'assigned' # Update status to assigned
                ticket.save(update_fields=['assigned_to', 'first_assigned_at', 'status'])
                print(f"Ticket {ticket.ticket_id} assigned to AI Assistant.")
            else:
                print(f"Warning: Could not find or create AI Assistant user.")
            
            # --- Apply AI Analysis ---
            ai_analysis_result = None
            if ticket.title and ticket.description and vertex_ai.is_available:
                print(f"Analyzing ticket {ticket.ticket_id} with Vertex AI")
                # Get AI recommendations for department, category, priority
                ai_analysis_result = vertex_ai.suggest_initial_fields(ticket.title, ticket.description)
                
                if ai_analysis_result:
                    print(f"Got AI analysis results: {ai_analysis_result}")
                    
                    # Try to find matching department
                    suggested_dept_name = ai_analysis_result.get('suggested_department_name')
                    suggested_dept_obj = None
                    if suggested_dept_name:
                        try:
                            suggested_dept_obj = Department.objects.get(name__iexact=suggested_dept_name)
                            if not ticket.department:  # Only set if not already set
                                ticket.department = suggested_dept_obj
                        except Department.DoesNotExist:
                            print(f"Department '{suggested_dept_name}' suggested by AI not found in database")
                    
                    # Try to find matching category
                    suggested_cat_name = ai_analysis_result.get('suggested_category_name')
                    suggested_cat_obj = None
                    if suggested_cat_name:
                        try:
                            category_filter = Q(name__iexact=suggested_cat_name)
                            if suggested_dept_obj:
                                category_filter &= Q(department=suggested_dept_obj)
                            
                            suggested_cat_obj = Category.objects.filter(category_filter).first()
                            if suggested_cat_obj and not ticket.category:  # Only set if not already set
                                ticket.category = suggested_cat_obj
                        except Exception as e:
                            print(f"Error finding category '{suggested_cat_name}': {e}")
                    
                    # Set suggested priority if available
                    suggested_priority = ai_analysis_result.get('suggested_priority')
                    if suggested_priority and not post_data.get('priority'):
                        if suggested_priority.lower() in [choice[0] for choice in Ticket.PRIORITY_CHOICES]:
                            ticket.priority = suggested_priority.lower()
                    
                    # Save ticket changes from AI suggestions
                    ticket.save(update_fields=['department', 'category', 'priority'])
                    
                    # Look for a suggested assignee - Improved logic
                    suggested_assignee_obj = None
                    assignee_suggestion = vertex_ai.suggest_assignee(ticket)
                    suggested_dept_obj = ticket.department  # Get the department set on the ticket

                    if suggested_dept_obj:
                        print(f"Looking for active staff in Department: {suggested_dept_obj.name} (ID: {suggested_dept_obj.id})")
                        # Explicitly check role__is_staff and is_active
                        staff_in_dept = User.objects.filter(
                            profile__department=suggested_dept_obj,
                            profile__role__is_staff=True,  # Check the role flag
                            is_active=True  # Ensure user is active
                        )
                        print(f"Found {staff_in_dept.count()} active staff users in this department.")
                        suggested_assignee_obj = staff_in_dept.order_by('?').first()  # Get one randomly

                        if suggested_assignee_obj:
                            print(f"Found potential assignee: {suggested_assignee_obj.username}")
                        else:
                            print(f"No suitable active staff found in department {suggested_dept_obj.name}.")
                    else:
                        print("No department set on ticket or suggested by AI, cannot find assignee.")
                        
                    # Create or update AI analysis record
                    analysis, created = AIAnalysis.objects.update_or_create(
                        ticket=ticket,
                        defaults={
                            'sentiment_score': ai_analysis_result.get('sentiment_score', 0.0),
                            'category_confidence': ai_analysis_result.get('confidence_score', 0.0),
                            'suggested_category': ticket.category.name if ticket.category else ai_analysis_result.get('suggested_category_name'),
                            'suggested_priority': ai_analysis_result.get('suggested_priority', ticket.priority).lower(),
                            'suggested_department': ticket.department,
                            'suggested_assignee': suggested_assignee_obj
                        }
                    )
                    print(f"AI Analysis record {'created' if created else 'updated'} for ticket {ticket.ticket_id} with details: Sentiment={analysis.sentiment_score}, Confidence={analysis.category_confidence}, Assignee={analysis.suggested_assignee}")
            else:
                # Fallback to traditional AI if Vertex AI fails
                fallback_ai_analysis(ticket)
        else:
            # Use traditional AI engine if Vertex is not available
            fallback_ai_analysis(ticket)
        
        # Generate and add initial AI comment
        try:
            ai_response_text = vertex_ai.generate_response(ticket)
            if ai_response_text and ai_user:  # Ensure ai_user exists
                comment = TicketComment.objects.create(
                    ticket=ticket,
                    content=ai_response_text,
                    user=ai_user,
                    is_internal=False
                )
                
                # Create TicketUpdate record for the new comment
                TicketUpdate.objects.create(
                    ticket=ticket,
                    updated_by=ai_user,
                    status=ticket.status,
                    comment=f"Initial response from AI Assistant.",
                    internal=False
                )
                
                # Increment AI response counter
                # ModelUsageStats.increment_stats(
                #     model_name='gemini-1.5-pro',
                #     api_name='generate_response',
                #     request_count=1,
                #     successful_predictions=1 if ai_response_text else 0,
                # )
                
                # Set first response time
                if not ticket.first_response_time:
                    # Increment counter
                    ticket.gemini_message_count = 1
                    # Set first response time
                    ticket.first_response_at = timezone.now()
                    if ticket.created_at:
                        ticket.first_response_time = ticket.first_response_at - ticket.created_at
                    # Set status to assigned
                    ticket.status = 'assigned'
                    # Save all updates
                    ticket.save(update_fields=['gemini_message_count', 'first_response_at', 'first_response_time', 'status'])
                    print(f"Initial AI comment added and status set to assigned for {ticket.ticket_id}")
        except Exception as e:
            print(f"Error generating initial AI response: {e}")
            # Don't fail ticket creation if AI response fails
        
        # Log ticket creation
        SystemLog.objects.create(
            user=user,
            level='info',
            component='tickets',
            action='Created ticket',
            details=f'ID: {ticket.ticket_id}, Title: {ticket.title}'
        )
        
        messages.success(request, f"Ticket #{ticket.ticket_id} has been created successfully.")
        return redirect('ticket_detail', ticket_id=ticket.ticket_id)
    else:
        # GET request - show form
        form = TicketForm()
        
        # Pre-populate department from user profile if available
        if hasattr(user, 'profile') and user.profile.department:
            form.fields['department'].initial = user.profile.department.id
    
    return render(request, 'ticket_system/tickets/create_ticket.html', {
        'form': form
    })


def fallback_ai_analysis(ticket):
    """Fallback to regular AI service if Vertex AI is not available."""
    try:
        if not ticket.pk:
            ticket.save()
            
        # Process AI suggestions with regular service
        ai_service = AIService()
        
        # Analyze text and get suggestions
        sentiment = ai_service._analyze_sentiment(ticket.description)
        category_name, confidence = ai_service._fallback_classification(ticket.description)
        
        # Set department based on ticket content - always use AI suggestion
        # Map categories to departments
        dept_mapping = {
            'Hardware': 'IT',
            'Software': 'IT',
            'Network': 'IT',
            'Account': 'IT',
            'Email': 'IT',
            'Security': 'IT',
            'Finance': 'FINANCE',
            'HR': 'HR',
            'Development': 'DEV',
            'Legal': 'LEGAL',
            'General': 'IT'  # Default to IT
        }
        
        dept_name = dept_mapping.get(category_name, 'IT')
        department = Department.objects.filter(name__icontains=dept_name).first()
        if department:
            ticket.department = department
        
        # Find a matching category - always use AI suggestion
        category_obj = None
        if category_name:
            category_obj = Category.objects.filter(name__icontains=category_name).first()
            if category_obj:
                ticket.category = category_obj
                ticket.save()
        
        # Always set priority based on sentiment analysis
        ticket.priority = ai_service._suggest_priority(ticket.description, sentiment)
        ticket.save()
        
        # Create AI analysis record
        analysis, created = AIAnalysis.objects.update_or_create(
            ticket=ticket,
            defaults={
                'sentiment_score': sentiment,
                'category_confidence': confidence,
                'suggested_category': category_obj.name if category_obj else category_name,
                'suggested_priority': ticket.priority,
                'suggested_department': ticket.department
            }
        )
        
        # Generate and add AI auto-response comment
        ai_comment = ai_service.generate_automatic_comment(ticket)
        if ai_comment:
            system_user, created = User.objects.get_or_create(
                username='ai.assistant',
                defaults={
                    'email': 'ai.assistant@ticketsystem.com',
                    'first_name': 'AI',
                    'last_name': 'Assistant',
                    'is_staff': True
                }
            )
            
            # Create the AI comment
            TicketComment.objects.create(
                ticket=ticket,
                user=system_user,
                content=ai_comment,
                is_internal=False
            )
            
            # Set first_response_at timestamp
            ticket.first_response_at = timezone.now()
            if ticket.created_at:
                ticket.first_response_time = ticket.first_response_at - ticket.created_at
            ticket.save(update_fields=['first_response_at', 'first_response_time'])
    except Exception as e:
        print(f"Error in fallback AI service: {str(e)}")


@login_required
def ticket_detail_view(request, ticket_id):
    """Display ticket details."""
    user = request.user
    
    try:
        # Get ticket with permission check
        ticket = TicketService.get_ticket_by_id(ticket_id, user)
        
        # Get ticket comments
        comments = ticket.comments.all().order_by('created_at')
        
        # Get ticket attachments
        attachments = ticket.attachments.all().order_by('-created_at')
        
        # Get ticket escalations
        escalations = ticket.escalations.all().order_by('-created_at')
        
        # Get AI analysis if available
        try:
            ai_analysis = ticket.ai_analysis
        except AIAnalysis.DoesNotExist:
            ai_analysis = None
        
        # Prepare forms for adding comment and attachment
        comment_form = TicketCommentForm()
        attachment_form = TicketAttachmentForm()
        
        # Determine if user can edit the ticket
        can_edit = False
        can_assign = False
        can_escalate = False
        
        if user.profile.role and (user.profile.role.is_staff or user.profile.role.is_admin):
            can_edit = True
            can_assign = True
            can_escalate = True
        elif ticket.assigned_to == user:
            can_edit = True
        
        # Prepare department and user lists for assignment/escalation
        departments = Department.objects.all()
        staff_users = User.objects.filter(
            profile__role__is_staff=True,
            is_active=True
        )
        
        context = {
            'ticket': ticket,
            'comments': comments,
            'attachments': attachments,
            'escalations': escalations,
            'ai_analysis': ai_analysis,
            'comment_form': comment_form,
            'attachment_form': attachment_form,
            'can_edit': can_edit,
            'can_assign': can_assign,
            'can_escalate': can_escalate,
            'departments': departments,
            'staff_users': staff_users,
        }
        
        return render(request, 'ticket_system/tickets/ticket_detail.html', context)
        
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('ticket_list')
    except PermissionError:
        messages.error(request, "You don't have permission to view this ticket.")
        return redirect('ticket_list')


@login_required
def edit_ticket_view(request, ticket_id):
    """Handle ticket editing."""
    user = request.user
    
    try:
        # Get ticket with permission check
        ticket = TicketService.get_ticket_by_id(ticket_id, user)
        
        # Check if user can edit the ticket
        is_staff = user.profile.role and (user.profile.role.is_staff or user.profile.role.is_admin)
        is_assignee = ticket.assigned_to == user
        
        if not (is_staff or is_assignee):
            messages.error(request, "You don't have permission to edit this ticket.")
            return redirect('ticket_detail', ticket_id=ticket_id)
        
        if request.method == 'POST':
            form = TicketForm(request.POST, instance=ticket)
            
            if form.is_valid():
                ticket = form.save()
                
                # Log ticket update
                SystemLog.objects.create(
                    user=user,
                    level='info',
                    component='ticket',
                    action=f'Updated ticket {ticket.ticket_id}',
                    details=f'Title: {ticket.title}'
                )
                
                messages.success(request, f"Ticket #{ticket.ticket_id} has been updated successfully.")
                return redirect('ticket_detail', ticket_id=ticket.ticket_id)
        else:
            form = TicketForm(instance=ticket)
        
        return render(request, 'ticket_system/tickets/edit_ticket.html', {
            'form': form,
            'ticket': ticket
        })
        
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('ticket_list')
    except PermissionError:
        messages.error(request, "You don't have permission to edit this ticket.")
        return redirect('ticket_list')


@login_required
def add_comment_view(request, ticket_id):
    """Add a comment to a ticket."""
    user = request.user
    
    try:
        # Get ticket with permission check
        ticket = TicketService.get_ticket_by_id(ticket_id, user)
        
        if request.method == 'POST':
            form = TicketCommentForm(request.POST)
            
            if form.is_valid():
                comment = form.save(commit=False)
                comment.ticket = ticket
                comment.user = user
                
                # Check if internal comment is allowed
                is_internal = form.cleaned_data.get('is_internal', False)
                if is_internal and not (user.profile.role and (user.profile.role.is_staff or user.profile.role.is_admin)):
                    is_internal = False
                
                comment.is_internal = is_internal
                comment.save()
                
                # Create TicketUpdate record for the new comment
                TicketUpdate.objects.create(
                    ticket=ticket,
                    updated_by=user,
                    status=ticket.status,
                    comment=f"Comment added by {user.get_full_name() or user.username}",
                    internal=is_internal
                )
                
                # Store user comment content for AI processing
                user_comment_content = comment.content
                user_is_creator = (user == ticket.created_by)
                
                # --- Track First Response Time ---
                # Check if commenter is staff/admin OR the AI assistant
                is_staff_or_ai = (hasattr(user, 'profile') and user.profile.role and (user.profile.role.is_staff or user.profile.role.is_admin)) or user.username == 'ai.assistant'
                # Check if response is not from the creator and first response time isn't set yet
                if is_staff_or_ai and not user_is_creator and not ticket.first_response_time:
                    ticket.first_response_time = timezone.now() - ticket.created_at
                    ticket.save(update_fields=['first_response_time'])
                    print(f"First response time set for ticket {ticket.ticket_id}")
                
                # Log comment creation
                SystemLog.objects.create(
                    user=user,
                    level='info',
                    component='ticket',
                    action=f'Added comment to ticket {ticket.ticket_id}',
                    details=f'Internal: {is_internal}'
                )
                
                # Create notifications for relevant users
                if not is_internal or is_internal and user != ticket.created_by:
                    # For the ticket creator
                    if user != ticket.created_by:
                        Notification.objects.create(
                            user=ticket.created_by,
                            ticket=ticket,
                            notification_type='comment',
                            title=f'New Comment on Ticket: {ticket.ticket_id}',
                            message=f'A new comment has been added to your ticket by {user.get_full_name() or user.username}'
                        )
                
                # For the assignee
                if ticket.assigned_to and user != ticket.assigned_to:
                    # Don't send internal comment notifications to non-staff users
                    if not is_internal or (is_internal and ticket.assigned_to.profile.role and 
                                        (ticket.assigned_to.profile.role.is_staff or ticket.assigned_to.profile.role.is_admin)):
                        Notification.objects.create(
                            user=ticket.assigned_to,
                            ticket=ticket,
                            notification_type='comment',
                            title=f'New Comment on Ticket: {ticket.ticket_id}',
                            message=f'A new comment has been added to a ticket assigned to you by {user.get_full_name() or user.username}'
                        )
                
                # --- Check if USER comment indicates resolution ---
                # (Only check if the commenter is the ticket creator and ticket is not already closed)
                resolution_detected = False
                if user_is_creator and ticket.status not in ['closed', 'resolved']:
                    vertex_ai = VertexAIService()
                    if vertex_ai.analyze_comment_for_resolution(user_comment_content):
                        resolution_detected = True
                        # Close the ticket
                        ticket.status = 'closed'
                        now = timezone.now()
                        ticket.closed_at = now
                        if not ticket.resolved_at:  # Set resolved_at if not already set
                            ticket.resolved_at = now
                            if ticket.created_at:
                                ticket.resolution_time = ticket.resolved_at - ticket.created_at
                        ticket.save()

                        # Create TicketUpdate record for the auto-closure
                        ai_user = vertex_ai.get_ai_user()
                        TicketUpdate.objects.create(
                            ticket=ticket,
                            updated_by=ai_user,
                            previous_status='assigned',
                            status='closed',
                            comment=f"Ticket auto-closed based on user confirmation of resolution.",
                            internal=False
                        )

                        # Log auto-closure
                        SystemLog.objects.create(
                            user=vertex_ai.get_ai_user(),  # Logged by AI
                            level='info',
                            component='ticket',
                            action=f'Ticket {ticket.ticket_id} was auto-closed based on user resolution confirmation',
                            details=f'Original comment: {user_comment_content[:50]}...'
                        )
                        
                        # Add an AI comment confirming closure
                        closing_message = vertex_ai.generate_closing_confirmation(ticket.ticket_id)
                        ai_user = vertex_ai.get_ai_user()
                        TicketComment.objects.create(
                            ticket=ticket,
                            user=ai_user,
                            content=closing_message,
                            is_internal=False
                        )
                        # Don't increment gemini_message_count for closing confirmation
                        
                        # Notify relevant parties about closure
                        if ticket.assigned_to:
                            Notification.objects.create(
                                user=ticket.assigned_to,
                                ticket=ticket,
                                notification_type='status',
                                title=f'Ticket Auto-Closed: {ticket.ticket_id}',
                                message=f'The ticket was automatically closed based on user confirmation of resolution.'
                            )
                
                # --- Trigger AI Response (if not just auto-closed and ticket is open) ---
                if not resolution_detected and ticket.status not in ['closed', 'resolved']:
                    vertex_ai = VertexAIService()
                    ai_user = vertex_ai.get_ai_user()
                    all_comments = ticket.comments.all() # Get updated comment list including the user's new one
                    MAX_GEMINI_MESSAGES = 5

                    ai_response_text = None # Initialize

                    # Check if escalation is needed
                    if ticket.gemini_message_count >= MAX_GEMINI_MESSAGES:
                        escalation_data = vertex_ai.generate_escalation_suggestion(ticket, all_comments)
                        ai_response_text = escalation_data.get("escalation_message")
                        suggested_dept_name = escalation_data.get("suggested_department")

                        # Optional: Log suggestion or assign ticket here based on suggested_dept_name
                        print(f"AI suggests escalating ticket {ticket.ticket_id} to {suggested_dept_name}")
                        # Add internal note about the escalation suggestion
                        TicketComment.objects.create(
                            ticket=ticket, 
                            user=ai_user,
                            content=f"Internal Note: AI suggests escalation to {suggested_dept_name} based on conversation.",
                            is_internal=True
                        )
                    else: # Generate normal conversation response
                        ai_response_text = vertex_ai.generate_conversation_response(ticket, all_comments)

                    # Save AI comment if a response was generated
                    if ai_response_text:
                        TicketComment.objects.create(
                            ticket=ticket,
                            user=ai_user,
                            content=ai_response_text,
                            is_internal=False
                        )
                        # Increment counter *only* when AI adds a message
                        ticket.gemini_message_count += 1
                        ticket.save(update_fields=['gemini_message_count'])
                
                # Set success message and redirect
                messages.success(request, 'Comment added successfully.')
                return redirect('ticket_detail', ticket_id=ticket.ticket_id)
            else:
                messages.error(request, 'There was an error adding your comment.')
        else:
            form = TicketCommentForm()
        
        context = {
            'ticket': ticket,
            'form': form,
            'comments': ticket.comments.all().order_by('created_at'),
        }
        return render(request, 'ticket_system/tickets/ticket_detail.html', context)
    
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('ticket_list')
    except PermissionError as e:
        messages.error(request, str(e))
        return redirect('ticket_list')


@login_required
def add_attachment_view(request, ticket_id):
    """Add an attachment to a ticket."""
    user = request.user
    
    try:
        # Get ticket with permission check
        ticket = TicketService.get_ticket_by_id(ticket_id, user)
        
        if request.method == 'POST':
            form = TicketAttachmentForm(request.POST, request.FILES)
            
            if form.is_valid() and request.FILES:
                attachment = form.save(commit=False)
                attachment.ticket = ticket
                attachment.uploaded_by = user
                attachment.file_name = request.FILES['file'].name
                attachment.file_type = request.FILES['file'].content_type
                attachment.file_size = request.FILES['file'].size
                attachment.save()
                
                # Log attachment upload
                SystemLog.objects.create(
                    user=user,
                    level='info',
                    component='ticket',
                    action=f'Added attachment to ticket {ticket.ticket_id}',
                    details=f'File: {attachment.file_name}'
                )
                
                messages.success(request, "Your attachment has been uploaded successfully.")
            else:
                messages.error(request, "There was an error with your upload. Please check the file and try again.")
        
        return redirect('ticket_detail', ticket_id=ticket.ticket_id)
        
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('ticket_list')
    except PermissionError:
        messages.error(request, "You don't have permission to add attachments to this ticket.")
        return redirect('ticket_list')


@login_required
def escalate_ticket_view(request, ticket_id):
    """Escalate a ticket to another department."""
    user = request.user
    
    # Check if user has permission to escalate tickets
    if not (user.profile.role and (user.profile.role.is_staff or user.profile.role.is_admin)):
        messages.error(request, "You don't have permission to escalate tickets.")
        return redirect('ticket_detail', ticket_id=ticket_id)
    
    try:
        # Get ticket with permission check
        ticket = TicketService.get_ticket_by_id(ticket_id, user)
        
        if request.method == 'POST':
            to_department_id = request.POST.get('to_department')
            to_user_id = request.POST.get('to_user')
            reason = request.POST.get('reason', '')
            
            if not to_department_id:
                messages.error(request, "Please select a department for escalation.")
                return redirect('ticket_detail', ticket_id=ticket_id)
            
            try:
                # Use service to handle escalation
                escalation = TicketService.escalate_ticket(
                    ticket_id=ticket_id,
                    user=user,
                    to_department_id=to_department_id,
                    to_user_id=to_user_id if to_user_id else None,
                    reason=reason,
                    is_auto=False
                )
                
                messages.success(request, f"Ticket has been escalated successfully to {escalation.to_department.name}.")
            except ValueError as e:
                messages.error(request, str(e))
        
        return redirect('ticket_detail', ticket.ticket_id)
        
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('ticket_list')
    except PermissionError:
        messages.error(request, "You don't have permission to view this ticket.")
        return redirect('ticket_list')


@login_required
def assign_ticket_view(request, ticket_id):
    """Assign a ticket to a user."""
    user = request.user
    
    # Check if user has permission to assign tickets
    if not (user.profile.role and (user.profile.role.is_staff or user.profile.role.is_admin)):
        messages.error(request, "You don't have permission to assign tickets.")
        return redirect('ticket_detail', ticket_id=ticket_id)
    
    try:
        # Get ticket with permission check
        ticket = TicketService.get_ticket_by_id(ticket_id, user)
        
        if request.method == 'POST':
            assignee_id = request.POST.get('assignee')
            
            if not assignee_id:
                messages.error(request, "Please select a user to assign the ticket to.")
                return redirect('ticket_detail', ticket_id=ticket_id)
            
            try:
                # Use service to handle assignment
                updated_ticket = TicketService.assign_ticket(
                    ticket_id=ticket_id,
                    assigner=user,
                    assignee_id=assignee_id
                )
                
                messages.success(
                    request, 
                    f"Ticket has been assigned successfully to {updated_ticket.assigned_to.get_full_name() or updated_ticket.assigned_to.username}."
                )
            except ValueError as e:
                messages.error(request, str(e))
        
        return redirect('ticket_detail', ticket.ticket_id)
        
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('ticket_list')
    except PermissionError:
        messages.error(request, "You don't have permission to view this ticket.")
        return redirect('ticket_list')


# AJAX Views for Dynamic Form Fields
@login_required
def get_categories_view(request):
    """AJAX view to get categories for a department."""
    department_id = request.GET.get('department_id')
    
    if not department_id:
        return JsonResponse({'categories': []})
    
    categories = Category.objects.filter(
        department_id=department_id,
        is_active=True
    ).values('id', 'name')
    
    return JsonResponse({'categories': list(categories)})


@login_required
def get_subcategories_view(request):
    """AJAX view to get subcategories for a category."""
    category_id = request.GET.get('category_id')
    
    if not category_id:
        return JsonResponse({'subcategories': []})
    
    subcategories = SubCategory.objects.filter(
        category_id=category_id,
        is_active=True
    ).values('id', 'name')
    
    return JsonResponse({'subcategories': list(subcategories)})

# Department Management Views
@staff_member_required
def department_list_view(request):
    """Display list of departments."""
    departments = Department.objects.all().order_by('name')
    return render(request, 'ticket_system/admin/department_list.html', {'departments': departments})


@staff_member_required
def create_department_view(request):
    """Handle department creation."""
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            
            # Log department creation
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='admin',
                action='Created department',
                details=f'Name: {department.name}'
            )
            
            messages.success(request, f"Department '{department.name}' has been created successfully.")
            return redirect('department_list')
    else:
        form = DepartmentForm()
    
    return render(request, 'ticket_system/admin/department_form.html', {
        'form': form,
        'title': 'Create Department'
    })


@staff_member_required
def edit_department_view(request, pk):
    """Handle department editing."""
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            department = form.save()
            
            # Log department update
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='admin',
                action='Updated department',
                details=f'Name: {department.name}'
            )
            
            messages.success(request, f"Department '{department.name}' has been updated successfully.")
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=department)
    
    return render(request, 'ticket_system/admin/department_form.html', {
        'form': form,
        'department': department,
        'title': 'Edit Department'
    })


@staff_member_required
def delete_department_view(request, pk):
    """Handle department deletion."""
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        name = department.name
        
        # Check if department has tickets
        if Ticket.objects.filter(department=department).exists():
            messages.error(request, f"Cannot delete department '{name}' because it has associated tickets.")
            return redirect('department_list')
        
        # Check if department has categories
        if Category.objects.filter(department=department).exists():
            messages.error(request, f"Cannot delete department '{name}' because it has associated categories.")
            return redirect('department_list')
        
        # Delete department
        department.delete()
        
        # Log department deletion
        SystemLog.objects.create(
            user=request.user,
            level='warning',
            component='admin',
            action='Deleted department',
            details=f'Name: {name}'
        )
        
        messages.success(request, f"Department '{name}' has been deleted successfully.")
        return redirect('department_list')
    
    return render(request, 'ticket_system/admin/department_confirm_delete.html', {
        'department': department
    })


# Category Management Views
@staff_member_required
def category_list_view(request):
    """Display list of categories."""
    categories = Category.objects.all().select_related('department').order_by('department__name', 'name')
    return render(request, 'ticket_system/admin/category_list.html', {'categories': categories})


@staff_member_required
def create_category_view(request):
    """Handle category creation."""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            
            # Log category creation
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='admin',
                action='Created category',
                details=f'Name: {category.name}, Department: {category.department.name}'
            )
            
            messages.success(request, f"Category '{category.name}' has been created successfully.")
            return redirect('category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'ticket_system/admin/category_form.html', {
        'form': form,
        'title': 'Create Category'
    })


@staff_member_required
def edit_category_view(request, pk):
    """Handle category editing."""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            
            # Log category update
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='admin',
                action='Updated category',
                details=f'Name: {category.name}, Department: {category.department.name}'
            )
            
            messages.success(request, f"Category '{category.name}' has been updated successfully.")
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'ticket_system/admin/category_form.html', {
        'form': form,
        'category': category,
        'title': 'Edit Category'
    })


@staff_member_required
def delete_category_view(request, pk):
    """Handle category deletion."""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        name = category.name
        
        # Check if category has tickets
        if Ticket.objects.filter(category=category).exists():
            messages.error(request, f"Cannot delete category '{name}' because it has associated tickets.")
            return redirect('category_list')
        
        # Check if category has subcategories
        if SubCategory.objects.filter(category=category).exists():
            messages.error(request, f"Cannot delete category '{name}' because it has associated subcategories.")
            return redirect('category_list')
        
        # Delete category
        category.delete()
        
        # Log category deletion
        SystemLog.objects.create(
            user=request.user,
            level='warning',
            component='admin',
            action='Deleted category',
            details=f'Name: {name}'
        )
        
        messages.success(request, f"Category '{name}' has been deleted successfully.")
        return redirect('category_list')
    
    return render(request, 'ticket_system/admin/category_confirm_delete.html', {
        'category': category
    })


# SubCategory Management Views
@staff_member_required
def subcategory_list_view(request):
    """Display list of subcategories."""
    subcategories = SubCategory.objects.all().select_related('category', 'category__department').order_by(
        'category__department__name', 'category__name', 'name'
    )
    return render(request, 'ticket_system/admin/subcategory_list.html', {'subcategories': subcategories})


@staff_member_required
def create_subcategory_view(request):
    """Handle subcategory creation."""
    if request.method == 'POST':
        form = SubCategoryForm(request.POST)
        if form.is_valid():
            subcategory = form.save()
            
            # Log subcategory creation
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='admin',
                action='Created subcategory',
                details=f'Name: {subcategory.name}, Category: {subcategory.category.name}'
            )
            
            messages.success(request, f"Subcategory '{subcategory.name}' has been created successfully.")
            return redirect('subcategory_list')
    else:
        form = SubCategoryForm()
    
    return render(request, 'ticket_system/admin/subcategory_form.html', {
        'form': form,
        'title': 'Create Subcategory'
    })


@staff_member_required
def edit_subcategory_view(request, pk):
    """Handle subcategory editing."""
    subcategory = get_object_or_404(SubCategory, pk=pk)
    
    if request.method == 'POST':
        form = SubCategoryForm(request.POST, instance=subcategory)
        if form.is_valid():
            subcategory = form.save()
            
            # Log subcategory update
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='admin',
                action='Updated subcategory',
                details=f'Name: {subcategory.name}, Category: {subcategory.category.name}'
            )
            
            messages.success(request, f"Subcategory '{subcategory.name}' has been updated successfully.")
            return redirect('subcategory_list')
    else:
        form = SubCategoryForm(instance=subcategory)
    
    return render(request, 'ticket_system/admin/subcategory_form.html', {
        'form': form,
        'subcategory': subcategory,
        'title': 'Edit Subcategory'
    })


@staff_member_required
def delete_subcategory_view(request, pk):
    """Handle subcategory deletion."""
    subcategory = get_object_or_404(SubCategory, pk=pk)
    
    if request.method == 'POST':
        name = subcategory.name
        
        # Check if subcategory has tickets
        if Ticket.objects.filter(subcategory=subcategory).exists():
            messages.error(request, f"Cannot delete subcategory '{name}' because it has associated tickets.")
            return redirect('subcategory_list')
        
        # Delete subcategory
        subcategory.delete()
        
        # Log subcategory deletion
        SystemLog.objects.create(
            user=request.user,
            level='warning',
            component='admin',
            action='Deleted subcategory',
            details=f'Name: {name}'
        )
        
        messages.success(request, f"Subcategory '{name}' has been deleted successfully.")
        return redirect('subcategory_list')
    
    return render(request, 'ticket_system/admin/subcategory_confirm_delete.html', {
        'subcategory': subcategory
    })

# User Management Views
@staff_member_required
def user_list_view(request):
    """Display list of users."""
    users = User.objects.all().select_related('profile__department', 'profile__role').order_by('username')
    return render(request, 'ticket_system/admin/user_list.html', {'users': users})


@staff_member_required
def create_user_view(request):
    """Handle user creation."""
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user_profile = form.save()
            
            # Log user creation
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='admin',
                action='Created user',
                details=f'Username: {user_profile.user.username}, Role: {user_profile.role.name if user_profile.role else "None"}'
            )
            
            messages.success(request, f"User '{user_profile.user.username}' has been created successfully.")
            return redirect('user_list')
    else:
        form = AdminUserCreateForm()
    
    return render(request, 'ticket_system/admin/user_form.html', {
        'form': form,
        'title': 'Create User'
    })


@staff_member_required
def edit_user_view(request, pk):
    """Handle user editing."""
    user = get_object_or_404(User, pk=pk)
    
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        # Create a profile if it doesn't exist
        profile = UserProfile.objects.create(user=user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save()
            
            # Update role-based permissions
            if profile.role:
                user.is_staff = profile.role.is_staff
                user.is_superuser = profile.role.is_admin
                user.save(update_fields=['is_staff', 'is_superuser'])
            
            # Log user update
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='admin',
                action='Updated user',
                details=f'Username: {user.username}, Role: {profile.role.name if profile.role else "None"}'
            )
            
            messages.success(request, f"User '{user.username}' has been updated successfully.")
            return redirect('user_list')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'ticket_system/admin/user_form.html', {
        'form': form,
        'user_obj': user,
        'title': 'Edit User'
    })


@staff_member_required
def delete_user_view(request, pk):
    """Handle user deletion or deactivation."""
    user = get_object_or_404(User, pk=pk)
    
    # Prevent self-deletion
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user_list')
    
    if request.method == 'POST':
        username = user.username
        action = request.POST.get('action', 'deactivate')
        
        if action == 'delete':
            # Check if user has associated tickets
            if Ticket.objects.filter(created_by=user).exists() or Ticket.objects.filter(assigned_to=user).exists():
                messages.error(request, f"Cannot delete user '{username}' because they have associated tickets. Deactivate instead.")
                return redirect('user_list')
            
            # Delete user
            user.delete()
            
            # Log user deletion
            SystemLog.objects.create(
                user=request.user,
                level='warning',
                component='admin',
                action='Deleted user',
                details=f'Username: {username}'
            )
            
            messages.success(request, f"User '{username}' has been deleted successfully.")
        else:
            # Deactivate user
            user.is_active = False
            user.save(update_fields=['is_active'])
            
            # Log user deactivation
            SystemLog.objects.create(
                user=request.user,
                level='warning',
                component='admin',
                action='Deactivated user',
                details=f'Username: {username}'
            )
            
            messages.success(request, f"User '{username}' has been deactivated successfully.")
        
        return redirect('user_list')
    
    return render(request, 'ticket_system/admin/user_confirm_delete.html', {
        'user_obj': user
    })


# Role Management Views
@staff_member_required
def role_list_view(request):
    """Display list of roles."""
    roles = Role.objects.all().order_by('name')
    return render(request, 'ticket_system/admin/role_list.html', {'roles': roles})


@staff_member_required
def create_role_view(request):
    """Handle role creation."""
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()
            
            # Log role creation
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='admin',
                action='Created role',
                details=f'Name: {role.name}, Staff: {role.is_staff}, Admin: {role.is_admin}'
            )
            
            messages.success(request, f"Role '{role.name}' has been created successfully.")
            return redirect('role_list')
    else:
        form = RoleForm()
    
    return render(request, 'ticket_system/admin/role_form.html', {
        'form': form,
        'title': 'Create Role'
    })


@staff_member_required
def edit_role_view(request, pk):
    """Handle role editing."""
    role = get_object_or_404(Role, pk=pk)
    
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            old_is_staff = role.is_staff
            old_is_admin = role.is_admin
            
            role = form.save()
            
            # Update users with this role if staff/admin status changed
            if old_is_staff != role.is_staff or old_is_admin != role.is_admin:
                users = User.objects.filter(profile__role=role)
                for user in users:
                    user.is_staff = role.is_staff
                    user.is_superuser = role.is_admin
                    user.save(update_fields=['is_staff', 'is_superuser'])
            
            # Log role update
            SystemLog.objects.create(
                user=request.user,
                level='info',
                component='admin',
                action='Updated role',
                details=f'Name: {role.name}, Staff: {role.is_staff}, Admin: {role.is_admin}'
            )
            
            messages.success(request, f"Role '{role.name}' has been updated successfully.")
            return redirect('role_list')
    else:
        form = RoleForm(instance=role)
    
    return render(request, 'ticket_system/admin/role_form.html', {
        'form': form,
        'role': role,
        'title': 'Edit Role'
    })


@staff_member_required
def delete_role_view(request, pk):
    """Handle role deletion."""
    role = get_object_or_404(Role, pk=pk)
    
    if request.method == 'POST':
        name = role.name
        
        # Check if role is assigned to users
        if UserProfile.objects.filter(role=role).exists():
            messages.error(request, f"Cannot delete role '{name}' because it is assigned to users.")
            return redirect('role_list')
        
        # Delete role
        role.delete()
        
        # Log role deletion
        SystemLog.objects.create(
            user=request.user,
            level='warning',
            component='admin',
            action='Deleted role',
            details=f'Name: {name}'
        )
        
        messages.success(request, f"Role '{name}' has been deleted successfully.")
        return redirect('role_list')
    
    return render(request, 'ticket_system/admin/role_confirm_delete.html', {
        'role': role
    })


# Notification Views
@login_required
def notification_list_view(request):
    """Display user notifications."""
    user = request.user
    notifications = Notification.objects.filter(user=user).order_by('-created_at')
    
    # Paginate notifications
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Count unread notifications
    unread_count = notifications.filter(is_read=False).count()
    
    return render(request, 'ticket_system/notifications/notification_list.html', {
        'notifications': page_obj,
        'paginator': paginator,
        'unread_count': unread_count
    })


@login_required
def mark_notification_read_view(request, pk):
    """Mark a notification as read."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    
    # Redirect back to previous page or notification list
    next_url = request.GET.get('next', 'notification_list')
    return redirect(next_url)


@login_required
def mark_all_notifications_read_view(request):
    """Mark all user notifications as read."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications have been marked as read.")
    
    # Redirect back to previous page or notification list
    next_url = request.GET.get('next', 'notification_list')
    return redirect(next_url)


# Reports Views
@staff_member_required
def reports_view(request):
    """Display reports dashboard."""
    return render(request, 'ticket_system/reports/reports_dashboard.html')


@staff_member_required
def ticket_stats_report_view(request):
    """Display ticket statistics report."""
    form = DateRangeForm(request.GET or None)
    
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        department = form.cleaned_data.get('department')
        
        # Get ticket statistics
        department_id = department.id if department else None
        stats = TicketService.get_ticket_stats(
            department_id=department_id,
            start_date=start_date,
            end_date=end_date
        )
    else:
        # Default to last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=30)
        stats = TicketService.get_ticket_stats(
            start_date=start_date,
            end_date=end_date
        )
    
    return render(request, 'ticket_system/reports/ticket_stats_report.html', {
        'form': form,
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date
    })


@staff_member_required
def sla_performance_report_view(request):
    """Display SLA performance report."""
    form = DateRangeForm(request.GET or None)
    
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        department = form.cleaned_data.get('department')
        
        # Get SLA performance
        department_id = department.id if department else None
        performance = TicketService.get_sla_performance(
            department_id=department_id,
            start_date=start_date,
            end_date=end_date
        )
    else:
        # Default to last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=30)
        performance = TicketService.get_sla_performance(
            start_date=start_date,
            end_date=end_date
        )
    
    return render(request, 'ticket_system/reports/sla_performance_report.html', {
        'form': form,
        'performance': performance,
        'start_date': start_date,
        'end_date': end_date
    })


@staff_member_required
def ai_performance_report_view(request):
    """Display AI model performance report."""
    # Get model usage statistics
    performance = AIService.get_model_performance(days=30)
    
    return render(request, 'ticket_system/reports/ai_performance_report.html', {
        'performance': performance
    })


@staff_member_required
def system_logs_view(request):
    """Display system logs."""
    # Filter options
    level = request.GET.get('level')
    component = request.GET.get('component')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Base query
    logs = SystemLog.objects.all()
    
    # Apply filters
    if level:
        logs = logs.filter(level=level)
    
    if component:
        logs = logs.filter(component=component)
    
    if from_date:
        try:
            from_date = timezone.datetime.strptime(from_date, '%Y-%m-%d').date()
            logs = logs.filter(created_at__date__gte=from_date)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_date = timezone.datetime.strptime(to_date, '%Y-%m-%d').date()
            logs = logs.filter(created_at__date__lte=to_date)
        except ValueError:
            pass
    
    # Order by creation date (newest first)
    logs = logs.order_by('-created_at')
    
    # Paginate results
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available filter options
    level_choices = SystemLog.LOG_LEVELS
    component_choices = SystemLog.objects.values_list('component', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'level_choices': level_choices,
        'component_choices': component_choices,
        'current_level': level,
        'current_component': component,
        'current_from_date': from_date,
        'current_to_date': to_date,
    }
    
    return render(request, 'ticket_system/admin/system_logs.html', context)

# API Views
class IsStaffUser(permissions.BasePermission):
    """Permission class for staff users."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            hasattr(request.user, 'profile') and 
            request.user.profile.role and 
            request.user.profile.role.is_staff
        )


class IsAdminUser(permissions.BasePermission):
    """Permission class for admin users."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            hasattr(request.user, 'profile') and 
            request.user.profile.role and 
            request.user.profile.role.is_admin
        )


class TicketListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating tickets."""
    permission_classes = [IsAuthenticated]
    serializer_class = TicketListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['ticket_id', 'title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        # Base queryset depends on user role
        if user.profile.role and user.profile.role.is_admin:
            # Admins see all tickets
            queryset = Ticket.objects.all()
        elif user.profile.role and user.profile.role.is_staff:
            # Staff see tickets in their department and assigned to them
            department = user.profile.department
            if department:
                queryset = Ticket.objects.filter(
                    Q(department=department) | Q(assigned_to=user)
                ).distinct()
            else:
                queryset = Ticket.objects.filter(assigned_to=user)
        else:
            # Regular users see only their tickets
            queryset = Ticket.objects.filter(created_by=user)
        
        # Apply filters
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        department_id = self.request.query_params.get('department_id')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        is_escalated = self.request.query_params.get('is_escalated')
        if is_escalated == 'true':
            queryset = queryset.filter(is_escalated=True)
        
        sla_breach = self.request.query_params.get('sla_breach')
        if sla_breach == 'true':
            queryset = queryset.filter(sla_breach=True)
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TicketCreateUpdateSerializer
        return TicketListSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by_id=self.request.user.id)


class TicketRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    """API view for retrieving and updating a ticket."""
    permission_classes = [IsAuthenticated]
    lookup_field = 'ticket_id'
    
    def get_queryset(self):
        return Ticket.objects.all()
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TicketCreateUpdateSerializer
        return TicketDetailSerializer
    
    def get_object(self):
        ticket_id = self.kwargs.get('ticket_id')
        try:
            # Use service to get ticket with permission check
            return TicketService.get_ticket_by_id(ticket_id, self.request.user)
        except (ValueError, PermissionError) as e:
            raise Http404(str(e))


class TicketCommentListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating ticket comments."""
    permission_classes = [IsAuthenticated]
    serializer_class = TicketCommentSerializer
    
    def get_queryset(self):
        ticket_id = self.kwargs.get('ticket_id')
        user = self.request.user
        
        try:
            # Use service to get ticket with permission check
            ticket = TicketService.get_ticket_by_id(ticket_id, user)
            
            # Staff/admin can see all comments, regular users only see non-internal comments
            if user.profile.role and (user.profile.role.is_staff or user.profile.role.is_admin):
                return ticket.comments.all().order_by('created_at')
            else:
                return ticket.comments.filter(is_internal=False).order_by('created_at')
        except (ValueError, PermissionError):
            return TicketComment.objects.none()
    
    def perform_create(self, serializer):
        ticket_id = self.kwargs.get('ticket_id')
        user = self.request.user
        
        try:
            # Use service to get ticket with permission check
            ticket = TicketService.get_ticket_by_id(ticket_id, user)
            
            # Check if internal comment is allowed
            is_internal = serializer.validated_data.get('is_internal', False)
            if is_internal and not (user.profile.role and (user.profile.role.is_staff or user.profile.role.is_admin)):
                is_internal = False
            
            serializer.save(
                ticket=ticket,
                user=user,
                user_id=user.id,
                is_internal=is_internal
            )
            
            # If this is the first staff response, update first_response_time
            if (user.profile.role and (user.profile.role.is_staff or user.profile.role.is_admin) and
                user != ticket.created_by and 
                not ticket.first_response_time):
                
                ticket.first_response_time = timezone.now() - ticket.created_at
                ticket.save(update_fields=['first_response_time'])
            
        except (ValueError, PermissionError) as e:
            raise ValidationError(str(e))


class UserListAPIView(generics.ListAPIView):
    """API view for listing users."""
    permission_classes = [IsAuthenticated, IsStaffUser]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        """Filter users based on user role."""
        user = self.request.user
        
        # Admins see all users
        if hasattr(user, 'profile') and user.profile.role and user.profile.role.is_admin:
            return User.objects.all()
        
        # Staff see users in their department
        if hasattr(user, 'profile') and user.profile.role and user.profile.role.is_staff:
            if user.profile.department:
                return User.objects.filter(
                    profile__department=user.profile.department
                )
        
        # Regular users see only themselves
        return User.objects.filter(pk=user.pk)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password."""
        user_service = UserService()
        
        try:
            current_password = request.data.get('current_password')
            new_password = request.data.get('new_password')
            
            if not current_password or not new_password:
                return Response(
                    {'error': 'Both current and new password are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user_service.change_password(
                user=request.user,
                current_password=current_password,
                new_password=new_password
            )
            
            return Response(
                {'message': 'Password changed successfully'},
                status=status.HTTP_200_OK
            )
        except (ValueError, PermissionError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        """Request password reset."""
        user_service = UserService()
        
        try:
            email = request.data.get('email')
            
            if not email:
                return Response(
                    {'error': 'Email is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user_service.send_password_reset(email)
            
            return Response(
                {'message': 'Password reset instructions sent'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            # Return success even if user not found to prevent email enumeration
            return Response(
                {'message': 'Password reset instructions sent if email exists'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def verify_token(self, request, token=None):
        """Verify password reset token."""
        user_service = UserService()
        
        try:
            valid = user_service.verify_password_reset_token(token)
            
            if valid:
                return Response(
                    {'message': 'Token is valid'},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'Invalid or expired token'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def performance(self, request):
        """Get user performance metrics."""
        user = self.request.user
        user_service = UserService()
        
        try:
            # Ensure only admins, the user themselves, or their direct manager can see this
            if (request.user.pk != user.pk and 
                not (hasattr(request.user, 'profile') and 
                    request.user.profile.role and 
                    request.user.profile.role.is_admin)):
                raise PermissionDenied("You don't have permission to view this user's performance")
            
            metrics = user_service.get_performance_metrics(user)
            
            return Response(metrics, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Category model."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsStaffUser]
    filterset_fields = ['department', 'is_active']
    
    def get_queryset(self):
        """Filter categories based on user role."""
        user = self.request.user
        queryset = Category.objects.all()
        
        # Filter by user department unless admin
        if (hasattr(user, 'profile') and 
            user.profile.role and 
            not user.profile.role.is_admin and
            user.profile.department):
            queryset = queryset.filter(department=user.profile.department)
        
        # Apply additional filters
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        return queryset


class DepartmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Department model."""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]
    
    def get_permissions(self):
        """Return appropriate permissions."""
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsStaffUser()]


class ReportViewSet(viewsets.ViewSet):
    """ViewSet for generating reports."""
    permission_classes = [IsAuthenticated, IsStaffUser]
    
    @action(detail=False, methods=['get'])
    def ticket_stats(self, request):
        """Get ticket statistics."""
        ticket_service = TicketService()
        
        try:
            # Get date filter if provided
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            # Get stats
            stats = ticket_service.get_ticket_stats(
                start_date=start_date,
                end_date=end_date
            )
            
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def sla_compliance(self, request):
        """Get SLA compliance report."""
        ticket_service = TicketService()
        
        try:
            # Get date filter if provided
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            # Get SLA report
            report = ticket_service.get_sla_performance(
                start_date=start_date,
                end_date=end_date
            )
            
            return Response(report, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def staff_performance(self, request):
        """Get staff performance report."""
        user_service = UserService()
        
        try:
            # Get department filter if provided
            department_id = request.query_params.get('department_id')
            
            # Get date filter if provided
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            # Get staff metrics
            metrics = user_service.get_staff_performance_report(
                department_id=department_id, 
                start_date=start_date,
                end_date=end_date
            )
            
            return Response(metrics, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SystemStatusViewSet(viewsets.ViewSet):
    """ViewSet for system status and health checks."""
    permission_classes = [IsAuthenticated, IsStaffUser]
    
    @action(detail=False, methods=['get'])
    def health(self, request):
        """Get system health status."""
        try:
            # Check database connection
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_status = cursor.fetchone()[0] == 1
            
            # Check cache if using Redis
            cache_status = True
            if 'redis' in settings.CACHES['default']['BACKEND'].lower():
                from django.core.cache import cache
                cache_key = 'health_check'
                cache.set(cache_key, 'ok', 10)
                cache_status = cache.get(cache_key) == 'ok'
            
            # Check AI services
            ai_service = AIService()
            ai_status = ai_service.check_health()
            
            return Response({
                'status': 'ok' if (db_status and cache_status and ai_status) else 'degraded',
                'database': 'connected' if db_status else 'error',
                'cache': 'connected' if cache_status else 'error',
                'ai_services': 'available' if ai_status else 'unavailable',
                'version': getattr(settings, 'APP_VERSION', 'unknown'),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get system usage statistics."""
        try:
            # Ticket counts
            total_tickets = Ticket.objects.count()
            open_tickets = Ticket.objects.filter(
                status__in=['new', 'assigned', 'in_progress', 'reopened']
            ).count()
            
            # User counts
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            
            # AI usage stats
            ai_stats = ModelUsageStats.objects.values('model_name').annotate(
                total_requests=Sum('request_count'),
                total_tokens=Sum('tokens_used'),
                avg_response_time=Avg('average_response_time')
            )
            
            return Response({
                'system': {
                    'total_tickets': total_tickets,
                    'open_tickets': open_tickets,
                    'total_users': total_users,
                    'active_users': active_users,
                },
                'ai_usage': ai_stats,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIAnalysisViewSet(viewsets.ModelViewSet):
    """ViewSet for AI analysis functions."""
    queryset = AIAnalysis.objects.all()
    permission_classes = []  # No authentication during development
    authentication_classes = []  # No authentication required for AI endpoints
    
    @action(detail=False, methods=['post'], url_path='suggest-category')
    def suggest_category(self, request):
        """Suggest a category for ticket text."""
        try:
            ai_service = AIService()
            text = request.data.get('text', '')
            
            if not text:
                return Response({
                    'suggested_category': None,
                    'confidence': 0
                })
                
            category_name, confidence = ai_service._fallback_classification(text)
            
            # Try to find matching category in database
            category = None
            if category_name:
                category = Category.objects.filter(
                    name__icontains=category_name
                ).first()
            
            return Response({
                'suggested_category': category_name,
                'category_id': category.id if category else None,
                'confidence': confidence
            })
        except Exception as e:
            print(f"Error in category suggestion: {e}")
            # Provide a safe fallback response
            return Response({
                'suggested_category': 'General',
                'category_id': None,
                'confidence': 0.5
            })
    
    @action(detail=False, methods=['post'], url_path='suggest-priority')
    def suggest_priority(self, request):
        """Suggest a priority for ticket text."""
        ai_service = AIService()
        
        try:
            text = request.data.get('text')
            
            if not text:
                return Response(
                    {'error': 'Text content is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            sentiment = ai_service._analyze_sentiment(text)
            priority = ai_service._suggest_priority(text, sentiment)
            
            return Response({
                'suggested_priority': priority,
                'sentiment_score': sentiment
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def accuracy_metrics(self, request):
        """Get AI accuracy metrics."""
        try:
            # Get metrics from feedback
            metrics = AIFeedback.objects.values('feedback_type').annotate(
                total=Count('id'),
                correct=Sum(Case(
                    When(is_correct=True, then=1),
                    default=0,
                    output_field=IntegerField()
                )),
                incorrect=Sum(Case(
                    When(is_correct=False, then=1),
                    default=0,
                    output_field=IntegerField()
                ))
            )
            
            # Calculate accuracy
            for item in metrics:
                total = item['total']
                if total > 0:
                    item['accuracy'] = item['correct'] / total
                else:
                    item['accuracy'] = 0
            
            return Response(metrics, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def generate_response(self, request):
        """Generate an automated response for a ticket."""
        ai_service = AIService()
        
        try:
            text = request.data.get('text')
            ticket_id = request.data.get('ticket_id')
            
            if not text:
                return Response(
                    {'error': 'Text content is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if ticket_id:
                ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
                response = ai_service.generate_response(ticket)
            else:
                response = ai_service.generate_response_from_text(text)
            
            return Response({
                'response': response
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_ticket_fields_api(request):
    """API endpoint for AI to suggest fields based on title/description."""
    title = request.data.get('title', '')
    description = request.data.get('description', '')

    if not title and not description:
        return Response({}) # Return empty if no input

    # Initialize Vertex AI service
    vertex_ai = VertexAIService()
    suggestions = vertex_ai.suggest_initial_fields(title, description)

    response_data = {
        'suggested_department_name': None,
        'suggested_category_name': None,
        'suggested_priority': None,
        'suggested_department_id': None,
        'suggested_category_id': None,
    }

    if suggestions:
        response_data['suggested_department_name'] = suggestions.get('suggested_department_name')
        response_data['suggested_category_name'] = suggestions.get('suggested_category_name')
        response_data['suggested_priority'] = suggestions.get('suggested_priority')

        # Try to find matching DB objects
        if response_data['suggested_department_name']:
            dept = Department.objects.filter(name__iexact=response_data['suggested_department_name']).first()
            if dept:
                response_data['suggested_department_id'] = dept.id

        if response_data['suggested_category_name']:
            cat = Category.objects.filter(name__iexact=response_data['suggested_category_name']).first()
            if cat:
                response_data['suggested_category_id'] = cat.id
                # Ensure suggested category belongs to suggested department if both found
                if response_data['suggested_department_id'] and cat.department_id != response_data['suggested_department_id']:
                    response_data['suggested_category_id'] = None # Invalidate category if dept mismatch

    return Response(response_data)


@login_required
def close_ticket_view(request, ticket_id):
    """Close a ticket."""
    user = request.user
    
    if request.method == 'POST':
        try:
            # Get ticket with permission check
            ticket = TicketService.get_ticket_by_id(ticket_id, user)
            
            # Update ticket status to closed
            TicketService.update_ticket(
                ticket_id=ticket_id,
                user=user,
                status='closed',
                comment="Ticket closed by user."
            )
            
            messages.success(request, f"Ticket {ticket_id} has been closed.")
        except (ValueError, PermissionError) as e:
            messages.error(request, str(e))
    
    return redirect('ticket_detail', ticket_id=ticket_id)


@login_required
def reopen_ticket_view(request, ticket_id):
    """Reopen a closed ticket."""
    user = request.user
    
    if request.method == 'POST':
        try:
            # Check if user has permission to reopen tickets
            if not user.profile.role.is_staff and not user.profile.role.is_admin:
                raise PermissionError("You don't have permission to reopen tickets.")
                
            # Get ticket with permission check
            ticket = TicketService.get_ticket_by_id(ticket_id, user)
            
            # Update ticket status to reopened
            TicketService.update_ticket(
                ticket_id=ticket_id,
                user=user,
                status='reopened',
                comment="Ticket reopened by staff."
            )
            
            messages.success(request, f"Ticket {ticket_id} has been reopened.")
        except (ValueError, PermissionError) as e:
            messages.error(request, str(e))
    
    return redirect('ticket_detail', ticket_id=ticket_id)


@login_required
def update_status_view(request, ticket_id):
    """Update a ticket's status."""
    user = request.user
    
    if request.method == 'POST':
        try:
            # Check if user has permission to update status
            if not user.profile.role.is_staff and not user.profile.role.is_admin:
                raise PermissionError("You don't have permission to update ticket status.")
                
            # Get ticket with permission check
            ticket = TicketService.get_ticket_by_id(ticket_id, user)
            
            # Get new status from form
            new_status = request.POST.get('status')
            if not new_status:
                raise ValueError("Status is required.")
                
            # Update ticket status
            TicketService.update_ticket(
                ticket_id=ticket_id,
                user=user,
                status=new_status,
                comment=f"Status updated to {new_status}."
            )
            
            messages.success(request, f"Ticket status updated to {new_status}.")
        except (ValueError, PermissionError) as e:
            messages.error(request, str(e))
    
    return redirect('ticket_detail', ticket_id=ticket_id)


@login_required
def update_priority_view(request, ticket_id):
    """Update a ticket's priority."""
    user = request.user
    
    if request.method == 'POST':
        try:
            # Check if user has permission to update priority
            if not user.profile.role.is_staff and not user.profile.role.is_admin:
                raise PermissionError("You don't have permission to update ticket priority.")
                
            # Get ticket with permission check
            ticket = TicketService.get_ticket_by_id(ticket_id, user)
            
            # Get new priority from form
            new_priority = request.POST.get('priority')
            if not new_priority:
                raise ValueError("Priority is required.")
                
            # Update ticket priority
            TicketService.update_ticket(
                ticket_id=ticket_id,
                user=user,
                priority=new_priority,
                comment=f"Priority updated to {new_priority}."
            )
            
            messages.success(request, f"Ticket priority updated to {new_priority}.")
        except (ValueError, PermissionError) as e:
            messages.error(request, str(e))
    
    return redirect('ticket_detail', ticket_id=ticket_id)
