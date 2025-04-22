"""
URL routing for the ticket management system.
"""
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter

from . import views

# API Router
router = DefaultRouter()
# Commented out ViewSet registrations until they are reimplemented
# router.register(r'tickets', views.TicketViewSet)
# router.register(r'users', views.UserViewSet)
# router.register(r'categories', views.CategoryViewSet)
# router.register(r'departments', views.DepartmentViewSet)
# router.register(r'reports', views.ReportViewSet, basename='reports')
# router.register(r'system', views.SystemStatusViewSet, basename='system')
# router.register(r'ai-analysis', views.AIAnalysisViewSet)

# API URLs (non-viewset based endpoints)
api_patterns = [
    # JWT Authentication endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # AI suggestion endpoint
    path('suggest-fields/', views.suggest_ticket_fields_api, name='suggest_ticket_fields'),
    
    # Include router URLs
    path('', include(router.urls)),
]

urlpatterns = [
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('password-reset/', views.password_reset_view, name='password_reset'),

    # Dashboard URLs
    path('', views.dashboard_view, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    
    # Ticket Management URLs
    path('tickets/', views.ticket_list_view, name='ticket_list'),
    path('tickets/create/', views.create_ticket_view, name='create_ticket'),
    path('tickets/<str:ticket_id>/', views.ticket_detail_view, name='ticket_detail'),
    path('tickets/<str:ticket_id>/edit/', views.edit_ticket_view, name='edit_ticket'),
    path('tickets/<str:ticket_id>/comment/', views.add_comment_view, name='add_comment'),
    path('tickets/<str:ticket_id>/attachment/', views.add_attachment_view, name='add_attachment'),
    path('tickets/<str:ticket_id>/escalate/', views.escalate_ticket_view, name='escalate_ticket'),
    path('tickets/<str:ticket_id>/assign/', views.assign_ticket_view, name='assign_ticket'),
    path('tickets/<str:ticket_id>/close/', views.close_ticket_view, name='close_ticket'),
    path('tickets/<str:ticket_id>/reopen/', views.reopen_ticket_view, name='reopen_ticket'),
    path('tickets/<str:ticket_id>/update-status/', views.update_status_view, name='update_status'),
    path('tickets/<str:ticket_id>/update-priority/', views.update_priority_view, name='update_priority'),
    
    # Department, Category, and Subcategory Management URLs
    path('departments/', views.department_list_view, name='department_list'),
    path('departments/create/', views.create_department_view, name='create_department'),
    path('departments/<int:pk>/edit/', views.edit_department_view, name='edit_department'),
    path('departments/<int:pk>/delete/', views.delete_department_view, name='delete_department'),
    
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/create/', views.create_category_view, name='create_category'),
    path('categories/<int:pk>/edit/', views.edit_category_view, name='edit_category'),
    path('categories/<int:pk>/delete/', views.delete_category_view, name='delete_category'),
    
    path('subcategories/', views.subcategory_list_view, name='subcategory_list'),
    path('subcategories/create/', views.create_subcategory_view, name='create_subcategory'),
    path('subcategories/<int:pk>/edit/', views.edit_subcategory_view, name='edit_subcategory'),
    path('subcategories/<int:pk>/delete/', views.delete_subcategory_view, name='delete_subcategory'),
    
    # User Management URLs
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.create_user_view, name='create_user'),
    path('users/<int:pk>/edit/', views.edit_user_view, name='edit_user'),
    path('users/<int:pk>/delete/', views.delete_user_view, name='delete_user'),
    
    # Role Management URLs
    path('roles/', views.role_list_view, name='role_list'),
    path('roles/create/', views.create_role_view, name='create_role'),
    path('roles/<int:pk>/edit/', views.edit_role_view, name='edit_role'),
    path('roles/<int:pk>/delete/', views.delete_role_view, name='delete_role'),
    
    # Ajax endpoints
    path('ajax/get-categories/', views.get_categories_view, name='get_categories'),
    path('ajax/get-subcategories/', views.get_subcategories_view, name='get_subcategories'),
    
    # Notifications URLs
    path('notifications/', views.notification_list_view, name='notification_list'),
    path('notifications/mark-read/<int:pk>/', views.mark_notification_read_view, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read_view, name='mark_all_notifications_read'),
    
    # Reports URLs
    path('reports/', views.reports_view, name='reports'),
    path('reports/ticket-stats/', views.ticket_stats_report_view, name='ticket_stats_report'),
    path('reports/sla-performance/', views.sla_performance_report_view, name='sla_performance_report'),
    path('reports/ai-performance/', views.ai_performance_report_view, name='ai_performance_report'),
    
    # System logs
    path('system-logs/', views.system_logs_view, name='system_logs'),
    
    # API routes
    path('api/', include((api_patterns, 'api'), namespace='api')),
]
