"""
Serializers for the ticket management system API.
"""
from rest_framework import serializers
from django.contrib.auth.models import User

from .models import (
    Ticket, TicketComment, TicketAttachment, Department,
    Category, SubCategory, UserProfile, Notification,
    TicketEscalation, AIAnalysis
)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profiles."""
    
    class Meta:
        model = UserProfile
        fields = ('department', 'role', 'phone_number')


class UserSerializer(serializers.ModelSerializer):
    """Serializer for users."""
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                'full_name', 'profile', 'is_active')
        read_only_fields = ('id', 'username', 'is_active')
    
    def get_full_name(self, obj):
        """Return user's full name."""
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for departments."""
    
    class Meta:
        model = Department
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for categories."""
    department_name = serializers.ReadOnlyField(source='department.name')
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'department', 'department_name', 
                'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class SubCategorySerializer(serializers.ModelSerializer):
    """Serializer for subcategories."""
    category_name = serializers.ReadOnlyField(source='category.name')
    
    class Meta:
        model = SubCategory
        fields = ('id', 'name', 'description', 'category', 'category_name', 
                'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class TicketCommentSerializer(serializers.ModelSerializer):
    """Serializer for ticket comments."""
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = TicketComment
        fields = ('id', 'ticket', 'user', 'user_id', 'content', 
                'is_internal', 'created_at', 'updated_at')
        read_only_fields = ('id', 'ticket', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        """Create and return a new ticket comment."""
        user_id = validated_data.pop('user_id')
        user = User.objects.get(pk=user_id)
        return TicketComment.objects.create(user=user, **validated_data)


class TicketAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for ticket attachments."""
    uploaded_by = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TicketAttachment
        fields = ('id', 'ticket', 'file', 'file_url', 'file_name', 'file_type', 
                'file_size', 'uploaded_by', 'created_at')
        read_only_fields = ('id', 'ticket', 'file_name', 'file_type', 
                         'file_size', 'created_at')
    
    def get_file_url(self, obj):
        """Get the URL for the file."""
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url') and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class TicketEscalationSerializer(serializers.ModelSerializer):
    """Serializer for ticket escalations."""
    from_department = DepartmentSerializer(read_only=True)
    to_department = DepartmentSerializer(read_only=True)
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    
    class Meta:
        model = TicketEscalation
        fields = ('id', 'ticket', 'from_department', 'to_department',
                'from_user', 'to_user', 'reason', 'is_auto_escalated', 'created_at')
        read_only_fields = ('id', 'ticket', 'from_department', 'to_department',
                         'from_user', 'to_user', 'created_at')


class AIAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for AI analysis results."""
    
    class Meta:
        model = AIAnalysis
        fields = ('id', 'ticket', 'sentiment_score', 'category_confidence',
                'suggested_department', 'suggested_category', 'suggested_priority',
                'suggested_assignee', 'automated_response', 'processing_time',
                'created_at', 'updated_at')
        read_only_fields = ('id', 'ticket', 'created_at', 'updated_at')


class TicketListSerializer(serializers.ModelSerializer):
    """Serializer for ticket list view."""
    department_name = serializers.ReadOnlyField(source='department.name')
    category_name = serializers.ReadOnlyField(source='category.name')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')
    assigned_to_name = serializers.SerializerMethodField()
    status_display = serializers.ReadOnlyField(source='get_status_display')
    priority_display = serializers.ReadOnlyField(source='get_priority_display')
    
    class Meta:
        model = Ticket
        fields = ('ticket_id', 'title', 'status', 'status_display', 'priority',
                'priority_display', 'department', 'department_name', 'category',
                'category_name', 'created_by', 'created_by_name', 'assigned_to',
                'assigned_to_name', 'created_at', 'is_escalated', 'sla_breach')
        read_only_fields = fields
    
    def get_assigned_to_name(self, obj):
        """Get the assigned user's full name."""
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return None


class TicketDetailSerializer(serializers.ModelSerializer):
    """Serializer for ticket detail view."""
    department = DepartmentSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    subcategory = SubCategorySerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    status_display = serializers.ReadOnlyField(source='get_status_display')
    priority_display = serializers.ReadOnlyField(source='get_priority_display')
    source_display = serializers.ReadOnlyField(source='get_source_display')
    comments = TicketCommentSerializer(many=True, read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    escalations = TicketEscalationSerializer(many=True, read_only=True)
    ai_analysis = AIAnalysisSerializer(read_only=True)
    
    class Meta:
        model = Ticket
        fields = ('ticket_id', 'title', 'description', 'status', 'status_display',
                'priority', 'priority_display', 'source', 'source_display',
                'department', 'category', 'subcategory', 'created_by', 'assigned_to',
                'created_at', 'updated_at', 'due_date', 'resolved_at', 'closed_at',
                'is_escalated', 'sla_breach', 'first_response_time', 'resolution_time',
                'comments', 'attachments', 'escalations', 'ai_analysis')
        read_only_fields = ('ticket_id', 'created_at', 'updated_at',
                         'first_response_time', 'resolution_time')


class TicketCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating tickets."""
    department_id = serializers.IntegerField(write_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    subcategory_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    created_by_id = serializers.IntegerField(write_only=True)
    assigned_to_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Ticket
        fields = ('title', 'description', 'status', 'priority', 'source',
                'department_id', 'category_id', 'subcategory_id', 'created_by_id',
                'assigned_to_id', 'due_date')
    
    def create(self, validated_data):
        """Create and return a new ticket."""
        department_id = validated_data.pop('department_id')
        department = Department.objects.get(pk=department_id)
        
        created_by_id = validated_data.pop('created_by_id')
        created_by = User.objects.get(pk=created_by_id)
        
        # Get optional foreign keys
        if 'category_id' in validated_data:
            category_id = validated_data.pop('category_id')
            category = Category.objects.get(pk=category_id) if category_id else None
        else:
            category = None
        
        if 'subcategory_id' in validated_data:
            subcategory_id = validated_data.pop('subcategory_id')
            subcategory = SubCategory.objects.get(pk=subcategory_id) if subcategory_id else None
        else:
            subcategory = None
        
        if 'assigned_to_id' in validated_data:
            assigned_to_id = validated_data.pop('assigned_to_id')
            assigned_to = User.objects.get(pk=assigned_to_id) if assigned_to_id else None
        else:
            assigned_to = None
        
        # Create the ticket
        return Ticket.objects.create(
            department=department,
            category=category,
            subcategory=subcategory,
            created_by=created_by,
            assigned_to=assigned_to,
            **validated_data
        )
    
    def update(self, instance, validated_data):
        """Update and return an existing ticket."""
        # Update foreign keys if provided
        if 'department_id' in validated_data:
            department_id = validated_data.pop('department_id')
            instance.department = Department.objects.get(pk=department_id)
        
        if 'category_id' in validated_data:
            category_id = validated_data.pop('category_id')
            instance.category = Category.objects.get(pk=category_id) if category_id else None
        
        if 'subcategory_id' in validated_data:
            subcategory_id = validated_data.pop('subcategory_id')
            instance.subcategory = SubCategory.objects.get(pk=subcategory_id) if subcategory_id else None
        
        if 'assigned_to_id' in validated_data:
            assigned_to_id = validated_data.pop('assigned_to_id')
            instance.assigned_to = User.objects.get(pk=assigned_to_id) if assigned_to_id else None
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""
    user = UserSerializer(read_only=True)
    ticket_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ('id', 'user', 'ticket', 'ticket_title', 'notification_type',
                'title', 'message', 'is_read', 'created_at')
        read_only_fields = ('id', 'user', 'ticket', 'notification_type',
                         'title', 'message', 'created_at')
    
    def get_ticket_title(self, obj):
        """Get the ticket title if ticket exists."""
        if obj.ticket:
            return obj.ticket.title
        return None
