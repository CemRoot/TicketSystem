from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Department, Role, UserProfile, Category, SubCategory,
    Ticket, TicketComment, TicketAttachment, TicketEscalation,
    Notification, SystemLog, AIAnalysis, ModelUsageStats
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_staff', 'is_admin', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('is_staff', 'is_admin', 'created_at')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'department', 'role', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    list_filter = ('department', 'role', 'created_at')
    raw_id_fields = ('user',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('department', 'is_active', 'created_at')


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('category', 'is_active', 'created_at')


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    fields = ('user', 'content', 'is_internal', 'created_at')
    readonly_fields = ('created_at',)


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    fields = ('file', 'file_name', 'file_type', 'file_size', 'uploaded_by', 'created_at')
    readonly_fields = ('created_at',)


class TicketEscalationInline(admin.TabularInline):
    model = TicketEscalation
    extra = 0
    fields = ('from_department', 'to_department', 'from_user', 'to_user', 'reason', 'is_auto_escalated', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'title', 'status', 'priority_badge', 'department', 
                   'created_by', 'assigned_to', 'created_at', 'is_escalated', 'sla_breach')
    search_fields = ('ticket_id', 'title', 'description', 'created_by__username', 'assigned_to__username')
    list_filter = ('status', 'priority', 'department', 'category', 'source', 
                  'is_escalated', 'sla_breach', 'created_at')
    readonly_fields = ('ticket_id', 'created_at', 'updated_at', 'resolved_at', 'closed_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('ticket_id', 'title', 'description', 'status', 'priority', 'source')
        }),
        ('Category and Classification', {
            'fields': ('department', 'category', 'subcategory')
        }),
        ('User Information', {
            'fields': ('created_by', 'assigned_to')
        }),
        ('Dates and Timestamps', {
            'fields': ('created_at', 'updated_at', 'due_date', 'resolved_at', 'closed_at')
        }),
        ('SLA and Tracking', {
            'fields': ('is_escalated', 'sla_breach', 'first_response_time', 'resolution_time')
        }),
    )
    inlines = [TicketCommentInline, TicketAttachmentInline, TicketEscalationInline]
    
    def priority_badge(self, obj):
        priority_colors = {
            1: 'green',
            2: 'blue',
            3: 'orange',
            4: 'red',
            5: 'darkred',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 7px; border-radius: 10px;">{}</span>',
            priority_colors.get(obj.priority, 'gray'),
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new ticket
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'user', 'content_preview', 'is_internal', 'created_at')
    search_fields = ('ticket__ticket_id', 'user__username', 'content')
    list_filter = ('is_internal', 'created_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'file_name', 'file_type', 'file_size_display', 'uploaded_by', 'created_at')
    search_fields = ('ticket__ticket_id', 'file_name', 'uploaded_by__username')
    list_filter = ('file_type', 'created_at')
    
    def file_size_display(self, obj):
        """Display file size in human-readable format."""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0 or unit == 'GB':
                break
            size /= 1024.0
        return f"{size:.2f} {unit}"
    file_size_display.short_description = 'File Size'


@admin.register(TicketEscalation)
class TicketEscalationAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'from_department', 'to_department', 'from_user', 'to_user', 
                   'is_auto_escalated', 'created_at')
    search_fields = ('ticket__ticket_id', 'from_department__name', 'to_department__name',
                    'from_user__username', 'to_user__username', 'reason')
    list_filter = ('from_department', 'to_department', 'is_auto_escalated', 'created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'ticket', 'title', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    list_filter = ('notification_type', 'is_read', 'created_at')


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('level', 'component', 'action', 'user', 'ip_address', 'created_at')
    search_fields = ('component', 'action', 'details', 'user__username')
    list_filter = ('level', 'component', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'sentiment_score', 'category_confidence', 
                   'suggested_department', 'suggested_priority', 'processing_time')
    search_fields = ('ticket__ticket_id',)
    list_filter = ('suggested_department', 'suggested_priority', 'created_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ModelUsageStats)
class ModelUsageStatsAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'api_name', 'date', 'request_count', 
                   'successful_predictions', 'failed_predictions', 'tokens_used')
    search_fields = ('model_name', 'api_name')
    list_filter = ('model_name', 'api_name', 'date')
    readonly_fields = ('date',)
