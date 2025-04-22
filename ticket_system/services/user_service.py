"""
User Service module for handling user-related business logic.
"""
import logging
from datetime import timedelta
import secrets
import string

from django.db import transaction
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from django.conf import settings

from ticket_system.models import (
    User, UserProfile, Role, Department, 
    PasswordReset, LoginAttempt, Notification, SystemLog
)

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user-related operations."""
    
    @staticmethod
    def create_user(username, email, password, first_name=None, last_name=None,
                   department_id=None, role_id=None):
        """
        Create a new user with associated profile.
        
        Args:
            username: Username for the new user
            email: Email address
            password: User password
            first_name: Optional first name
            last_name: Optional last name
            department_id: Optional department ID
            role_id: Optional role ID
            
        Returns:
            Created User object
        """
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create(
                    username=username,
                    email=email,
                    password=make_password(password),
                    first_name=first_name or '',
                    last_name=last_name or '',
                    is_active=True
                )
                
                # Get department and role if IDs provided
                department = None
                if department_id:
                    department = Department.objects.get(id=department_id)
                
                role = None
                if role_id:
                    role = Role.objects.get(id=role_id)
                
                # Create user profile
                UserProfile.objects.create(
                    user=user,
                    department=department,
                    role=role
                )
                
                # Log user creation
                SystemLog.objects.create(
                    level='info',
                    component='user',
                    action='User created',
                    user=user,
                    details=f'Username: {username}, Email: {email}, Department: {department.name if department else "None"}'
                )
                
                return user
                
        except Department.DoesNotExist:
            logger.error(f"Department with ID {department_id} not found")
            raise ValueError(f"Department with ID {department_id} not found")
        except Role.DoesNotExist:
            logger.error(f"Role with ID {role_id} not found")
            raise ValueError(f"Role with ID {role_id} not found")
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    @staticmethod
    def update_user(user_id, **kwargs):
        """
        Update user and profile information.
        
        Args:
            user_id: ID of the user to update
            **kwargs: Fields to update (username, email, first_name, last_name, 
                     department_id, role_id, is_active)
            
        Returns:
            Updated User object
        """
        try:
            with transaction.atomic():
                user = User.objects.get(id=user_id)
                
                # Track changes for logging
                changes = []
                
                # Update user fields
                user_fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
                for field in user_fields:
                    if field in kwargs and getattr(user, field) != kwargs[field]:
                        old_value = getattr(user, field)
                        setattr(user, field, kwargs[field])
                        changes.append(f"{field}: {old_value} -> {kwargs[field]}")
                
                # Save user if any changes
                if any(f in kwargs for f in user_fields):
                    user.save()
                
                # Update profile fields
                profile = user.profile
                
                # Update department if specified
                if 'department_id' in kwargs and kwargs['department_id'] != (profile.department.id if profile.department else None):
                    old_dept = profile.department.name if profile.department else "None"
                    if kwargs['department_id']:
                        department = Department.objects.get(id=kwargs['department_id'])
                        profile.department = department
                        changes.append(f"department: {old_dept} -> {department.name}")
                    else:
                        profile.department = None
                        changes.append(f"department: {old_dept} -> None")
                
                # Update role if specified
                if 'role_id' in kwargs and kwargs['role_id'] != (profile.role.id if profile.role else None):
                    old_role = profile.role.name if profile.role else "None"
                    if kwargs['role_id']:
                        role = Role.objects.get(id=kwargs['role_id'])
                        profile.role = role
                        changes.append(f"role: {old_role} -> {role.name}")
                    else:
                        profile.role = None
                        changes.append(f"role: {old_role} -> None")
                
                # Save profile if any changes
                if 'department_id' in kwargs or 'role_id' in kwargs:
                    profile.save()
                
                # Log the update
                if changes:
                    SystemLog.objects.create(
                        level='info',
                        component='user',
                        action='User updated',
                        details=", ".join(changes)
                    )
                
                return user
                
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found")
            raise ValueError(f"User with ID {user_id} not found")
        except Department.DoesNotExist:
            logger.error(f"Department with ID {kwargs['department_id']} not found")
            raise ValueError(f"Department with ID {kwargs['department_id']} not found")
        except Role.DoesNotExist:
            logger.error(f"Role with ID {kwargs['role_id']} not found")
            raise ValueError(f"Role with ID {kwargs['role_id']} not found")
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            raise
    
    @staticmethod
    def authenticate_user(username, password):
        """
        Authenticate a user with username and password.
        
        Args:
            username: Username or email
            password: Password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            # Try authenticating with username
            user = authenticate(username=username, password=password)
            
            # If that fails, try with email
            if user is None:
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            # Record login attempt
            successful = user is not None
            ip_address = None  # In a real system, would get from request
            
            LoginAttempt.objects.create(
                username=username,
                successful=successful,
                ip_address=ip_address
            )
            
            if successful:
                # Update last login time
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                # Log successful login
                SystemLog.objects.create(
                    level='info',
                    component='authentication',
                    action='User login',
                    user=user,
                    details=f'Username: {username}, IP: {ip_address or "unknown"}'
                )
            else:
                # Log failed login
                SystemLog.objects.create(
                    level='warning',
                    component='authentication',
                    action='Failed login',
                    details=f'Username: {username}, IP: {ip_address or "unknown"}'
                )
                
                # Check for multiple failed attempts
                recent_attempts = LoginAttempt.objects.filter(
                    username=username,
                    successful=False,
                    created_at__gte=timezone.now() - timedelta(hours=1)
                ).count()
                
                # If too many failed attempts, consider security measures
                if recent_attempts >= 5:
                    SystemLog.objects.create(
                        level='warning',
                        component='authentication',
                        action='Multiple failed login attempts',
                        details=f'Username: {username}, Count: {recent_attempts}'
                    )
                    
                    # Potential account lockout logic would go here
            
            return user
            
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return None
    
    @staticmethod
    def initiate_password_reset(email):
        """
        Initiate password reset process for a user.
        
        Args:
            email: User's email address
            
        Returns:
            PasswordReset object if successful, None if user not found
        """
        try:
            user = User.objects.get(email=email)
            
            # Generate a secure token
            alphabet = string.ascii_letters + string.digits
            token = ''.join(secrets.choice(alphabet) for _ in range(64))
            
            # Expire previous reset requests for this user
            PasswordReset.objects.filter(user=user, is_used=False).update(is_expired=True)
            
            # Create new reset request
            reset = PasswordReset.objects.create(
                user=user,
                token=token,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            
            # Log the password reset request
            SystemLog.objects.create(
                level='info',
                component='user',
                action='Password reset requested',
                user=user,
                details=f'Email: {email}'
            )
            
            return reset
            
        except User.DoesNotExist:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return None
        except Exception as e:
            logger.error(f"Error initiating password reset: {e}")
            raise
    
    @staticmethod
    def reset_password_with_token(token, new_password):
        """
        Complete password reset using token.
        
        Args:
            token: Reset token
            new_password: New password
            
        Returns:
            User object if successful, None if token invalid or expired
        """
        try:
            # Find valid reset request
            reset = PasswordReset.objects.filter(
                token=token,
                is_used=False,
                is_expired=False,
                expires_at__gt=timezone.now()
            ).first()
            
            if not reset:
                return None
            
            # Update user's password
            user = reset.user
            user.password = make_password(new_password)
            user.save(update_fields=['password'])
            
            # Mark reset as used
            reset.is_used = True
            reset.used_at = timezone.now()
            reset.save(update_fields=['is_used', 'used_at'])
            
            # Log password reset
            SystemLog.objects.create(
                level='info',
                component='user',
                action='Password reset completed',
                user=user
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return None
    
    @staticmethod
    def change_password(user_id, current_password, new_password):
        """
        Change a user's password with current password verification.
        
        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            True if successful, False if current password is incorrect
        """
        try:
            user = User.objects.get(id=user_id)
            
            # Verify current password
            if not authenticate(username=user.username, password=current_password):
                return False
            
            # Update password
            user.password = make_password(new_password)
            user.save(update_fields=['password'])
            
            # Log password change
            SystemLog.objects.create(
                level='info',
                component='user',
                action='Password changed',
                user=user
            )
            
            return True
            
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found")
            raise ValueError(f"User with ID {user_id} not found")
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            raise
    
    @staticmethod
    def get_user_notifications(user_id, mark_as_read=False, limit=None):
        """
        Get notifications for a user.
        
        Args:
            user_id: User ID
            mark_as_read: Whether to mark retrieved notifications as read
            limit: Optional limit on number of notifications
            
        Returns:
            QuerySet of notifications
        """
        try:
            # Get notifications for user
            notifications = Notification.objects.filter(
                user_id=user_id
            ).order_by('-created_at')
            
            if limit:
                notifications = notifications[:limit]
            
            # Mark as read if requested
            if mark_as_read:
                unread = notifications.filter(is_read=False)
                unread.update(is_read=True, read_at=timezone.now())
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error retrieving notifications: {e}")
            raise
    
    @staticmethod
    def get_users_by_department(department_id):
        """
        Get users in a specific department.
        
        Args:
            department_id: Department ID
            
        Returns:
            QuerySet of users
        """
        try:
            department = Department.objects.get(id=department_id)
            return User.objects.filter(profile__department=department)
            
        except Department.DoesNotExist:
            logger.error(f"Department with ID {department_id} not found")
            raise ValueError(f"Department with ID {department_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving users by department: {e}")
            raise
    
    @staticmethod
    def get_users_by_role(role_id):
        """
        Get users with a specific role.
        
        Args:
            role_id: Role ID
            
        Returns:
            QuerySet of users
        """
        try:
            role = Role.objects.get(id=role_id)
            return User.objects.filter(profile__role=role)
            
        except Role.DoesNotExist:
            logger.error(f"Role with ID {role_id} not found")
            raise ValueError(f"Role with ID {role_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving users by role: {e}")
            raise
    
    @staticmethod
    def get_staff_for_category(category_id):
        """
        Get staff users who can handle tickets in a specific category.
        
        Args:
            category_id: Category ID
            
        Returns:
            QuerySet of users
        """
        from ticket_system.models import Category
        
        try:
            category = Category.objects.get(id=category_id)
            
            # Get department associated with the category
            department = category.department
            
            if not department:
                return User.objects.none()
            
            # Find staff users in that department
            return User.objects.filter(
                profile__department=department,
                profile__role__is_staff=True,
                is_active=True
            )
            
        except Category.DoesNotExist:
            logger.error(f"Category with ID {category_id} not found")
            raise ValueError(f"Category with ID {category_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving staff for category: {e}")
            raise
    
    @staticmethod
    def get_user_performance(user_id, start_date=None, end_date=None):
        """
        Get performance metrics for a specific user.
        
        Args:
            user_id: User ID
            start_date: Optional start date for metrics
            end_date: Optional end date for metrics
            
        Returns:
            Dictionary of performance metrics
        """
        from django.db.models import Avg, Count, Q
        from ticket_system.models import Ticket
        
        try:
            user = User.objects.get(id=user_id)
            
            # Base query for assigned tickets
            query = Q(assigned_to=user)
            
            if start_date:
                query &= Q(created_at__gte=start_date)
            
            if end_date:
                query &= Q(created_at__lte=end_date)
            
            # Get assigned tickets
            assigned_tickets = Ticket.objects.filter(query)
            
            # Count total assigned
            total_assigned = assigned_tickets.count()
            
            # Count by status
            resolved = assigned_tickets.filter(status='closed').count()
            in_progress = assigned_tickets.filter(status__in=['assigned', 'in_progress']).count()
            
            # Calculate resolution rate
            if total_assigned > 0:
                resolution_rate = (resolved / total_assigned) * 100
            else:
                resolution_rate = 0
            
            # Average resolution time
            avg_resolution_time = assigned_tickets.filter(
                status='closed',
                resolution_time__isnull=False
            ).aggregate(avg=Avg('resolution_time'))['avg']
            
            # SLA compliance
            compliant_tickets = assigned_tickets.filter(
                status='closed',
                sla_breach=False
            ).count()
            
            if resolved > 0:
                sla_compliance_rate = (compliant_tickets / resolved) * 100
            else:
                sla_compliance_rate = 0
            
            # Return metrics
            return {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'name': user.get_full_name() or user.username
                },
                'total_assigned': total_assigned,
                'resolved': resolved,
                'in_progress': in_progress,
                'resolution_rate': resolution_rate,
                'avg_resolution_time': avg_resolution_time,
                'sla_compliance_rate': sla_compliance_rate
            }
            
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found")
            raise ValueError(f"User with ID {user_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving user performance: {e}")
            raise
