from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Department(models.Model):
    """
    Model representing a company department.
    Used for categorizing tickets and managing escalations.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Role(models.Model):
    """
    Model representing user roles with associated permissions.
    Used for role-based access control.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class UserProfile(models.Model):
    """
    Extension of Django User model with additional fields for the ticket system.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"


class Category(models.Model):
    """
    Model representing ticket categories.
    Used for organizing and filtering tickets.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='categories')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'


class SubCategory(models.Model):
    """
    Model representing ticket subcategories.
    Used for more granular organization of tickets.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Subcategories'
        unique_together = ['name', 'category']


class Ticket(models.Model):
    """
    Core model for the ticket management system.
    Represents a support ticket with its status, priority, and metadata.
    """
    STATUS_CHOICES = [
        ('new', 'New'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    SOURCE_CHOICES = [
        ('web', 'Web Portal'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('chat', 'Chat'),
        ('other', 'Other'),
    ]

    # Basic Information
    ticket_id = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='web')
    
    # Category and Classification
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='tickets')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    
    # User Information
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tickets')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    
    # Dates and Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # SLA and Tracking
    is_escalated = models.BooleanField(default=False)
    sla_breach = models.BooleanField(default=False)
    first_response_time = models.DurationField(null=True, blank=True)
    resolution_time = models.DurationField(null=True, blank=True)
    sla_deadline = models.DateTimeField(null=True, blank=True)
    first_assigned_at = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    response_sla_breach = models.BooleanField(default=False)
    resolution_sla_breach = models.BooleanField(default=False)
    gemini_message_count = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        original_status = None
        if not is_new:
            try:
                # Get the status before this save operation
                original_status = Ticket.objects.get(pk=self.pk).status
            except Ticket.DoesNotExist:
                pass # Should not happen in save but handle gracefully

        # Generate a unique ticket ID if not already set
        if not self.ticket_id:
            year = timezone.now().year
            month = timezone.now().month
            # Get the count of tickets created in the current month
            count = Ticket.objects.filter(
                created_at__year=year,
                created_at__month=month
            ).count() + 1
            self.ticket_id = f"TKT-{year}{month:02d}-{count:04d}"
        
        # Calculate SLA deadline based on priority if not set
        if not self.sla_deadline and self.priority:
            now = timezone.now()
            # Set SLA deadlines based on priority
            if self.priority == 'critical':
                self.sla_deadline = now + timezone.timedelta(hours=2)
            elif self.priority == 'high':
                self.sla_deadline = now + timezone.timedelta(hours=8)
            elif self.priority == 'medium':
                self.sla_deadline = now + timezone.timedelta(hours=24)
            else:  # low
                self.sla_deadline = now + timezone.timedelta(hours=48)
        
        # Track first assignment time
        if self.assigned_to and not self.first_assigned_at:
            self.first_assigned_at = timezone.now()
            
        # --- Accurate SLA Time Calculation Logic ---
        now = timezone.now()

        # Set resolved_at and calculate resolution_time on transition to 'resolved'
        if self.status == 'resolved' and original_status != 'resolved':
            if not self.resolved_at: # Set only if not already set by another process
                self.resolved_at = now
                if self.created_at:
                    self.resolution_time = self.resolved_at - self.created_at

        # Set closed_at and handle resolution time on transition to 'closed'
        if self.status == 'closed' and original_status != 'closed':
            self.closed_at = now
            # If closing without resolving first, mark resolved_at as closed_at
            if not self.resolved_at:
                self.resolved_at = self.closed_at # Use closed_at as resolution time
                if self.created_at:
                    self.resolution_time = self.resolved_at - self.created_at

        # --- SLA Breach Status Update ---
        self.resolution_sla_breach = False # Default to false
        if self.status in ['resolved', 'closed']:
            # Check if it breached *before* resolution/closure
            if self.sla_deadline and self.resolved_at and self.resolved_at > self.sla_deadline:
                self.resolution_sla_breach = True
                self.sla_breach = True # Keep general breach flag true if needed
            else:
                # Resolved/Closed on time
                self.sla_breach = False # Set breach to False if resolved/closed on time
        else:
            # Still an open/active ticket, check against current time
            if self.sla_deadline and now > self.sla_deadline:
                self.sla_breach = True
            else:
                self.sla_breach = False

        super().save(*args, **kwargs) # Call the original save method

    def __str__(self):
        return f"{self.ticket_id} - {self.title}"

    class Meta:
        ordering = ['-created_at']


class TicketComment(models.Model):
    """
    Model representing comments on tickets.
    Can be internal (staff only) or external (visible to all).
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment on {self.ticket.ticket_id} by {self.user.username}"

    class Meta:
        ordering = ['created_at']


class TicketUpdate(models.Model):
    """
    Model representing updates to a ticket's status, priority, or assignment.
    Used for tracking ticket history and changes.
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='updates')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    previous_status = models.CharField(max_length=20, blank=True, null=True, choices=Ticket.STATUS_CHOICES)
    status = models.CharField(max_length=20, choices=Ticket.STATUS_CHOICES)
    comment = models.TextField(blank=True)
    internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Update to {self.ticket.ticket_id} by {self.updated_by.username}"

    def get_status_display(self):
        return dict(Ticket.STATUS_CHOICES).get(self.status, self.status)

    class Meta:
        ordering = ['-created_at']


class TicketAttachment(models.Model):
    """
    Model representing file attachments for tickets.
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='ticket_attachments/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100)
    file_size = models.IntegerField()  # Size in bytes
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.ticket.ticket_id}: {self.file_name}"


class TicketEscalation(models.Model):
    """
    Model tracking ticket escalations and department transfers.
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='escalations')
    from_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='outgoing_escalations')
    to_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='incoming_escalations')
    from_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='escalated_from')
    to_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalated_to')
    reason = models.TextField()
    is_auto_escalated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Escalation for {self.ticket.ticket_id} to {self.to_department}"

    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    """
    Model for user notifications about ticket events.
    """
    NOTIFICATION_TYPES = [
        ('assignment', 'Ticket Assignment'),
        ('comment', 'New Comment'),
        ('status_change', 'Status Change'),
        ('escalation', 'Ticket Escalation'),
        ('sla_breach', 'SLA Breach'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"

    class Meta:
        ordering = ['-created_at']


class SystemLog(models.Model):
    """
    Model for logging system activities and events.
    Used for auditing and debugging.
    """
    LOG_LEVELS = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    level = models.CharField(max_length=10, choices=LOG_LEVELS, default='info')
    component = models.CharField(max_length=100)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.level} - {self.component} - {self.action}"

    class Meta:
        ordering = ['-created_at']


class AIAnalysis(models.Model):
    """
    Model for storing AI analysis results for tickets.
    Used to track AI processing and suggestions.
    """
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='ai_analysis')
    sentiment_score = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)], 
        null=True, blank=True
    )
    category_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)], 
        null=True, blank=True
    )
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)], 
        null=True, blank=True
    )
    suggested_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    suggested_category = models.CharField(max_length=100, null=True, blank=True)
    suggested_priority = models.CharField(max_length=20, choices=Ticket.PRIORITY_CHOICES, null=True, blank=True)
    suggested_assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    suggested_staff = models.CharField(max_length=100, null=True, blank=True)
    automated_response = models.TextField(blank=True)
    processing_time = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI Analysis for {self.ticket.ticket_id}"


class ModelUsageStats(models.Model):
    """
    Model for tracking AI model performance and usage.
    """
    model_name = models.CharField(max_length=100)
    api_name = models.CharField(max_length=100)
    tokens_used = models.IntegerField(default=0)
    request_count = models.IntegerField(default=0)
    successful_predictions = models.IntegerField(default=0)
    failed_predictions = models.IntegerField(default=0)
    average_response_time = models.FloatField(null=True, blank=True)  # in milliseconds
    date = models.DateField(default=timezone.now)
    
    def __str__(self):
        return f"{self.model_name} - {self.date}"
    
    class Meta:
        unique_together = ['model_name', 'api_name', 'date']
        ordering = ['-date']


class SLA(models.Model):
    """
    Model defining Service Level Agreement parameters for different ticket priorities.
    """
    priority = models.CharField(max_length=20, choices=Ticket.PRIORITY_CHOICES, unique=True)
    response_time_hours = models.IntegerField()
    resolution_time_hours = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SLA for {self.get_priority_display()} priority tickets"

    def get_priority_display(self):
        return dict(Ticket.PRIORITY_CHOICES).get(self.priority, self.priority)

    class Meta:
        verbose_name = "SLA"
        verbose_name_plural = "SLAs"


class AIFeedback(models.Model):
    """
    Model for storing feedback about AI predictions and suggestions.
    Used to measure and improve AI accuracy.
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='ai_feedback')
    ai_analysis = models.ForeignKey(AIAnalysis, on_delete=models.CASCADE, related_name='feedback')
    feedback_type = models.CharField(max_length=20, choices=[
        ('category', 'Category'),
        ('priority', 'Priority'),
        ('staff', 'Staff Assignment')
    ])
    is_correct = models.BooleanField()
    corrected_value = models.CharField(max_length=100, blank=True, null=True)
    provided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI Feedback for {self.ticket.ticket_id} - {self.feedback_type}"

    class Meta:
        ordering = ['-created_at']


class LoginAttempt(models.Model):
    """
    Model for tracking user login attempts.
    Used for security monitoring.
    """
    username = models.CharField(max_length=150)
    successful = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "successful" if self.successful else "failed"
        return f"{status.capitalize()} login attempt for {self.username}"

    class Meta:
        ordering = ['-created_at']


class PasswordReset(models.Model):
    """
    Model for tracking password reset requests.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_resets')
    token = models.CharField(max_length=100, unique=True)
    is_used = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Used" if self.is_used else "Active" if not self.is_expired else "Expired"
        return f"{status} reset token for {self.user.username}"

    class Meta:
        ordering = ['-created_at']
