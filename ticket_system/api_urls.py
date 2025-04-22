"""
API URL Configuration for the ticket management system.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import only the ViewSets that actually exist
from ticket_system.views import (
    CategoryViewSet, DepartmentViewSet,
    ReportViewSet, SystemStatusViewSet, AIAnalysisViewSet
)

# Create a router for our viewsets
router = DefaultRouter()
# Register only the ViewSets that exist
router.register(r'categories', CategoryViewSet)
router.register(r'departments', DepartmentViewSet)
router.register(r'reports', ReportViewSet, basename='reports')
router.register(r'system', SystemStatusViewSet, basename='system')
router.register(r'ai-analysis', AIAnalysisViewSet, basename='ai-analysis')

urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('auth/', include('rest_framework.urls')),
    
    # Custom API endpoints temporarily commented out
    # path('tickets/<str:ticket_id>/escalate/', TicketViewSet.as_view({'post': 'escalate'})),
    # path('tickets/<str:ticket_id>/assign/', TicketViewSet.as_view({'post': 'assign'})),
    # path('tickets/<str:ticket_id>/comment/', TicketViewSet.as_view({'post': 'add_comment'})),
    # path('tickets/<str:ticket_id>/attachments/', TicketViewSet.as_view({'post': 'add_attachment'})),
    # path('tickets/<str:ticket_id>/ai-analyze/', TicketViewSet.as_view({'post': 'ai_analyze'})),
    
    # User-specific endpoints temporarily commented out
    # path('users/me/', UserViewSet.as_view({'get': 'me'})),
    # path('users/change-password/', UserViewSet.as_view({'post': 'change_password'})),
    # path('users/reset-password/', UserViewSet.as_view({'post': 'reset_password'})),
    # path('users/verify-token/<str:token>/', UserViewSet.as_view({'get': 'verify_token'})),
    # path('users/<int:pk>/performance/', UserViewSet.as_view({'get': 'performance'})),
    
    # AI and analytics endpoints
    path('ai/suggest-category/', AIAnalysisViewSet.as_view({'post': 'suggest_category'})),
    path('ai/suggest-priority/', AIAnalysisViewSet.as_view({'post': 'suggest_priority'})),
    path('ai/accuracy-metrics/', AIAnalysisViewSet.as_view({'get': 'accuracy_metrics'})),
    path('ai/generate-response/', AIAnalysisViewSet.as_view({'post': 'generate_response'})),
]
