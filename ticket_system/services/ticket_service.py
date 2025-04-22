"""
Ticket Service module for handling ticket-related business logic.
"""
import logging
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from django.conf import settings

from ticket_system.models import (
    Ticket, TicketUpdate, TicketAttachment, SystemLog,
    Category, Department, SLA, Notification, User
)

logger = logging.getLogger(__name__)


class TicketService:
    """Service class for ticket-related operations."""
    
    @staticmethod
    def create_ticket(user, title, description, priority=None, category=None, 
                     department=None, attachments=None):
        """
        Create a new ticket with proper validation and logging.
        
        Args:
            user: User creating the ticket
            title: Ticket title
            description: Ticket description
            priority: Ticket priority (optional)
            category: Ticket category (optional)
            department: Ticket department (optional)
            attachments: List of file attachments (optional)
            
        Returns:
            Created Ticket object
        """
        try:
            with transaction.atomic():
                # Create the ticket
                ticket = Ticket.objects.create(
                    created_by=user,
                    title=title,
                    description=description,
                    priority=priority or 'medium',
                    category=category,
                    department=department,
                    status='new'
                )
                
                # Process attachments if any
                if attachments:
                    for attachment in attachments:
                        TicketAttachment.objects.create(
                            ticket=ticket,
                            file=attachment,
                            uploaded_by=user
                        )
                
                # Create initial ticket update
                TicketUpdate.objects.create(
                    ticket=ticket,
                    updated_by=user,
                    comment="Ticket created",
                    status='new',
                    internal=False
                )
                
                # Set SLA deadline based on priority
                TicketService._set_sla_deadline(ticket)
                
                # Create notification for admins/managers
                TicketService._notify_new_ticket(ticket)
                
                # Log ticket creation
                SystemLog.objects.create(
                    level='info',
                    component='ticket',
                    action=f'Ticket created: {ticket.ticket_id}',
                    user=user,
                    details=f'Title: {title}, Priority: {priority}, Category: {category}'
                )
                
                return ticket
                
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            raise
    
    @staticmethod
    def update_ticket(ticket_id, user, status=None, priority=None, category=None,
                     assigned_to=None, comment=None, internal=False, attachments=None):
        """
        Update an existing ticket with changes and comments.
        
        Args:
            ticket_id: ID of the ticket to update
            user: User making the update
            status: New status (optional)
            priority: New priority (optional)
            category: New category (optional)
            assigned_to: New assignee (optional)
            comment: Update comment (optional)
            internal: Whether the comment is internal-only
            attachments: List of file attachments (optional)
            
        Returns:
            Updated Ticket object
        """
        try:
            ticket = Ticket.objects.get(ticket_id=ticket_id)
            
            with transaction.atomic():
                # Record previous values for logging
                previous_status = ticket.status
                previous_priority = ticket.priority
                previous_assignee = ticket.assigned_to
                
                # Update ticket fields if provided
                if status and status != ticket.status:
                    ticket.status = status
                    
                    # If status changed to closed, set resolved time
                    if status == 'closed' and not ticket.resolved_at:
                        ticket.resolved_at = timezone.now()
                
                if priority and priority != ticket.priority:
                    ticket.priority = priority
                    # Update SLA deadline based on new priority
                    TicketService._set_sla_deadline(ticket)
                
                if category and category != ticket.category:
                    ticket.category = category
                
                if assigned_to is not None and assigned_to != ticket.assigned_to:
                    ticket.assigned_to = assigned_to
                    
                    # If the ticket is being assigned for the first time
                    if previous_assignee is None and assigned_to is not None:
                        ticket.first_assigned_at = timezone.now()
                    
                    # If the ticket is changing from assigned to unassigned
                    if previous_assignee is not None and assigned_to is None:
                        ticket.first_assigned_at = None
                
                # Save ticket changes
                ticket.save()
                
                # Process attachments if any
                if attachments:
                    for attachment in attachments:
                        TicketAttachment.objects.create(
                            ticket=ticket,
                            file=attachment,
                            uploaded_by=user
                        )
                
                # Create ticket update record
                update = TicketUpdate.objects.create(
                    ticket=ticket,
                    updated_by=user,
                    comment=comment or "",
                    status=ticket.status,
                    internal=internal
                )
                
                # Generate notification for relevant users
                if status != previous_status or assigned_to != previous_assignee:
                    TicketService._notify_ticket_update(ticket, user, previous_status, previous_assignee)
                
                # Log ticket update
                changes = []
                if status != previous_status:
                    changes.append(f"Status: {previous_status} -> {status}")
                if priority and priority != previous_priority:
                    changes.append(f"Priority: {previous_priority} -> {priority}")
                if assigned_to != previous_assignee:
                    old_name = previous_assignee.username if previous_assignee else "Unassigned"
                    new_name = assigned_to.username if assigned_to else "Unassigned"
                    changes.append(f"Assignee: {old_name} -> {new_name}")
                
                SystemLog.objects.create(
                    level='info',
                    component='ticket',
                    action=f'Ticket updated: {ticket.ticket_id}',
                    user=user,
                    details=", ".join(changes) if changes else "Comment added"
                )
                
                return ticket
                
        except Ticket.DoesNotExist:
            logger.error(f"Ticket not found: {ticket_id}")
            raise ValueError(f"Ticket not found: {ticket_id}")
        except Exception as e:
            logger.error(f"Error updating ticket: {e}")
            raise
    
    @staticmethod
    def _set_sla_deadline(ticket):
        """
        Set the SLA deadline based on ticket priority.
        
        Args:
            ticket: Ticket object
        """
        try:
            # Get SLA for the ticket's priority
            sla = SLA.objects.filter(
                priority=ticket.priority,
                is_active=True
            ).first()
            
            if not sla:
                # Use default SLA values if no specific SLA is defined
                if ticket.priority == 'critical':
                    hours = 2
                elif ticket.priority == 'high':
                    hours = 8
                elif ticket.priority == 'medium':
                    hours = 24
                else:  # low
                    hours = 48
            else:
                hours = sla.response_time_hours
            
            # Calculate deadline
            now = timezone.now()
            deadline = now + timedelta(hours=hours)
            
            # Update ticket SLA deadline
            ticket.sla_deadline = deadline
            ticket.save(update_fields=['sla_deadline'])
            
        except Exception as e:
            logger.error(f"Error setting SLA deadline: {e}")
    
    @staticmethod
    def _notify_new_ticket(ticket):
        """
        Create notifications for a new ticket.
        
        Args:
            ticket: New Ticket object
        """
        try:
            # Notify managers of the department if assigned
            if ticket.department:
                managers = User.objects.filter(
                    profile__department=ticket.department,
                    profile__role__is_manager=True,
                    is_active=True
                )
                
                for manager in managers:
                    Notification.objects.create(
                        user=manager,
                        title=f"New Ticket: {ticket.ticket_id}",
                        message=f"A new ticket has been created in your department: {ticket.title}",
                        notification_type='ticket_created',
                        related_object_id=ticket.id,
                        related_object_type='ticket'
                    )
            
            # Notify system admins
            admins = User.objects.filter(
                profile__role__is_admin=True,
                is_active=True
            )
            
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    title=f"New Ticket: {ticket.ticket_id}",
                    message=f"A new ticket has been created: {ticket.title}",
                    notification_type='ticket_created',
                    related_object_id=ticket.id,
                    related_object_type='ticket'
                )
                
        except Exception as e:
            logger.error(f"Error creating notifications for new ticket: {e}")
    
    @staticmethod
    def _notify_ticket_update(ticket, user, previous_status, previous_assignee):
        """
        Create notifications for ticket updates.
        
        Args:
            ticket: Updated Ticket object
            user: User who made the update
            previous_status: Previous ticket status
            previous_assignee: Previous assignee
        """
        try:
            # Notify ticket creator
            if ticket.created_by != user:
                Notification.objects.create(
                    user=ticket.created_by,
                    title=f"Ticket Updated: {ticket.ticket_id}",
                    message=f"Your ticket has been updated. Status: {ticket.get_status_display()}",
                    notification_type='ticket_updated',
                    related_object_id=ticket.id,
                    related_object_type='ticket'
                )
            
            # Notify previous assignee if different
            if (previous_assignee and 
                previous_assignee != user and 
                previous_assignee != ticket.assigned_to):
                
                Notification.objects.create(
                    user=previous_assignee,
                    title=f"Ticket Reassigned: {ticket.ticket_id}",
                    message=f"A ticket previously assigned to you has been reassigned.",
                    notification_type='ticket_reassigned',
                    related_object_id=ticket.id,
                    related_object_type='ticket'
                )
            
            # Notify new assignee
            if (ticket.assigned_to and 
                ticket.assigned_to != user and 
                ticket.assigned_to != previous_assignee):
                
                Notification.objects.create(
                    user=ticket.assigned_to,
                    title=f"Ticket Assigned: {ticket.ticket_id}",
                    message=f"A new ticket has been assigned to you: {ticket.title}",
                    notification_type='ticket_assigned',
                    related_object_id=ticket.id,
                    related_object_type='ticket'
                )
            
            # If status changed to 'closed', notify creator and department managers
            if previous_status != 'closed' and ticket.status == 'closed':
                Notification.objects.create(
                    user=ticket.created_by,
                    title=f"Ticket Closed: {ticket.ticket_id}",
                    message=f"Your ticket has been closed.",
                    notification_type='ticket_closed',
                    related_object_id=ticket.id,
                    related_object_type='ticket'
                )
                
                if ticket.department:
                    managers = User.objects.filter(
                        profile__department=ticket.department,
                        profile__role__is_manager=True,
                        is_active=True
                    )
                    
                    for manager in managers:
                        if manager != user and manager != ticket.created_by:
                            Notification.objects.create(
                                user=manager,
                                title=f"Ticket Closed: {ticket.ticket_id}",
                                message=f"A ticket in your department has been closed.",
                                notification_type='ticket_closed',
                                related_object_id=ticket.id,
                                related_object_type='ticket'
                            )
                
        except Exception as e:
            logger.error(f"Error creating notifications for ticket update: {e}")
    
    @staticmethod
    def get_tickets_by_status(status, user=None, department=None):
        """
        Get tickets filtered by status and optionally by user or department.
        
        Args:
            status: Ticket status to filter by
            user: Optional user to filter by (tickets created by or assigned to)
            department: Optional department to filter by
            
        Returns:
            QuerySet of filtered tickets
        """
        query = Ticket.objects.filter(status=status)
        
        if user:
            # Get tickets created by or assigned to the user
            query = query.filter(
                created_by=user
            ) | query.filter(
                assigned_to=user
            )
        
        if department:
            query = query.filter(department=department)
        
        return query.order_by('-created_at')
    
    @staticmethod
    def get_overdue_tickets():
        """
        Get tickets that have passed their SLA deadline without resolution.
        
        Returns:
            QuerySet of overdue tickets
        """
        now = timezone.now()
        return Ticket.objects.filter(
            status__in=['new', 'assigned', 'in_progress', 'reopened'],
            sla_deadline__lt=now
        ).order_by('sla_deadline')
    
    @staticmethod
    def get_ticket_by_id(ticket_id, user):
        """
        Get a ticket by ID with permission checking.
        
        Args:
            ticket_id: The ticket ID to retrieve
            user: The user requesting the ticket
            
        Returns:
            Ticket object if found and user has permission
            
        Raises:
            ValueError: If ticket is not found
            PermissionError: If user doesn't have permission to view the ticket
        """
        try:
            # First try to find the ticket
            ticket = Ticket.objects.get(ticket_id=ticket_id)
            
            # Check permissions based on user role
            if user.profile.role and (user.profile.role.is_admin or user.profile.role.is_staff):
                # Admin and staff can view all tickets
                return ticket
            elif ticket.created_by == user or ticket.assigned_to == user:
                # User can view tickets they created or are assigned to
                return ticket
            elif user.profile.department and user.profile.department == ticket.department:
                # User can view tickets in their department
                return ticket
            else:
                # No permission
                raise PermissionError("You don't have permission to view this ticket")
                
        except Ticket.DoesNotExist:
            raise ValueError(f"Ticket not found: {ticket_id}")
        except Exception as e:
            logger.error(f"Error retrieving ticket {ticket_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_tickets_for_dashboard(user):
        """
        Get ticket statistics for the user dashboard.
        
        Args:
            user: User object
            
        Returns:
            Dictionary with ticket statistics
        """
        result = {
            'assigned_to_user': 0,
            'created_by_user': 0,
            'open_tickets': 0,
            'closed_tickets': 0,
            'overdue_tickets': 0,
            'critical_tickets': 0,
            'recent_updates': []
        }
        
        # Tickets assigned to user
        result['assigned_to_user'] = Ticket.objects.filter(
            assigned_to=user,
            status__in=['new', 'assigned', 'in_progress', 'reopened']
        ).count()
        
        # Tickets created by user
        result['created_by_user'] = Ticket.objects.filter(
            created_by=user
        ).count()
        
        # Open tickets (for admins and managers)
        if user.profile.role.is_admin or user.profile.role.is_manager:
            departments = []
            if user.profile.role.is_manager:
                departments = [user.profile.department]
            
            open_query = Ticket.objects.filter(
                status__in=['new', 'assigned', 'in_progress', 'reopened']
            )
            
            if departments:
                open_query = open_query.filter(department__in=departments)
            
            result['open_tickets'] = open_query.count()
            
            # Closed tickets
            closed_query = Ticket.objects.filter(
                status='closed'
            )
            
            if departments:
                closed_query = closed_query.filter(department__in=departments)
            
            result['closed_tickets'] = closed_query.count()
            
            # Overdue tickets
            now = timezone.now()
            overdue_query = Ticket.objects.filter(
                status__in=['new', 'assigned', 'in_progress', 'reopened'],
                sla_deadline__lt=now
            )
            
            if departments:
                overdue_query = overdue_query.filter(department__in=departments)
            
            result['overdue_tickets'] = overdue_query.count()
            
            # Critical tickets
            critical_query = Ticket.objects.filter(
                status__in=['new', 'assigned', 'in_progress', 'reopened'],
                priority='critical'
            )
            
            if departments:
                critical_query = critical_query.filter(department__in=departments)
            
            result['critical_tickets'] = critical_query.count()
        
        # Recent updates (limited to 5)
        updates = TicketUpdate.objects.filter(
            ticket__created_by=user
        ).order_by('-created_at')[:5]
        
        result['recent_updates'] = [
            {
                'ticket_id': update.ticket.ticket_id,
                'status': update.get_status_display(),
                'updated_by': update.updated_by.get_full_name() or update.updated_by.username,
                'created_at': update.created_at,
                'comment': update.comment
            }
            for update in updates
        ]
        
        return result
    
    @staticmethod
    def escalate_ticket(ticket_id, user, reason):
        """
        Escalate a ticket to higher priority and notify managers.
        
        Args:
            ticket_id: ID of the ticket to escalate
            user: User requesting the escalation
            reason: Reason for escalation
            
        Returns:
            Escalated Ticket object
        """
        try:
            ticket = Ticket.objects.get(ticket_id=ticket_id)
            
            with transaction.atomic():
                # Record previous priority
                previous_priority = ticket.priority
                
                # Increase priority
                if previous_priority == 'low':
                    ticket.priority = 'medium'
                elif previous_priority == 'medium':
                    ticket.priority = 'high'
                elif previous_priority == 'high':
                    ticket.priority = 'critical'
                
                # Only update if priority actually changed
                if previous_priority != ticket.priority:
                    # Update SLA deadline based on new priority
                    TicketService._set_sla_deadline(ticket)
                    
                    # Save changes
                    ticket.save()
                    
                    # Create ticket update record
                    TicketUpdate.objects.create(
                        ticket=ticket,
                        updated_by=user,
                        comment=f"Ticket escalated: {reason}",
                        status=ticket.status,
                        internal=True
                    )
                    
                    # Notify department managers
                    if ticket.department:
                        managers = User.objects.filter(
                            profile__department=ticket.department,
                            profile__role__is_manager=True,
                            is_active=True
                        )
                        
                        for manager in managers:
                            Notification.objects.create(
                                user=manager,
                                title=f"Ticket Escalated: {ticket.ticket_id}",
                                message=f"A ticket has been escalated to {ticket.get_priority_display()}. Reason: {reason}",
                                notification_type='ticket_escalated',
                                related_object_id=ticket.id,
                                related_object_type='ticket'
                            )
                    
                    # If escalated to critical, notify all admins
                    if ticket.priority == 'critical':
                        admins = User.objects.filter(
                            profile__role__is_admin=True,
                            is_active=True
                        )
                        
                        for admin in admins:
                            if admin not in managers if ticket.department else []:
                                Notification.objects.create(
                                    user=admin,
                                    title=f"Critical Ticket: {ticket.ticket_id}",
                                    message=f"A ticket has been escalated to Critical priority. Reason: {reason}",
                                    notification_type='ticket_escalated',
                                    related_object_id=ticket.id,
                                    related_object_type='ticket'
                                )
                    
                    # Log escalation
                    SystemLog.objects.create(
                        level='warning',
                        component='ticket',
                        action=f'Ticket escalated: {ticket.ticket_id}',
                        user=user,
                        details=f"Priority: {previous_priority} -> {ticket.priority}. Reason: {reason}"
                    )
                
                return ticket
                
        except Ticket.DoesNotExist:
            logger.error(f"Ticket not found: {ticket_id}")
            raise ValueError(f"Ticket not found: {ticket_id}")
        except Exception as e:
            logger.error(f"Error escalating ticket: {e}")
            raise
    
    @staticmethod
    def generate_reports(start_date, end_date, department=None):
        """
        Generate ticket reports for a date range.
        
        Args:
            start_date: Start date for the report period
            end_date: End date for the report period
            department: Optional department to filter by
            
        Returns:
            Dictionary with report data
        """
        tickets = Ticket.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        if department:
            tickets = tickets.filter(department=department)
        
        # Total tickets
        total_tickets = tickets.count()
        
        # Tickets by status
        status_counts = {
            'new': tickets.filter(status='new').count(),
            'assigned': tickets.filter(status='assigned').count(),
            'in_progress': tickets.filter(status='in_progress').count(),
            'closed': tickets.filter(status='closed').count(),
            'reopened': tickets.filter(status='reopened').count()
        }
        
        # Tickets by priority
        priority_counts = {
            'low': tickets.filter(priority='low').count(),
            'medium': tickets.filter(priority='medium').count(),
            'high': tickets.filter(priority='high').count(),
            'critical': tickets.filter(priority='critical').count()
        }
        
        # Tickets by category
        category_counts = {}
        for category in Category.objects.all():
            count = tickets.filter(category=category).count()
            if count > 0:
                category_counts[category.name] = count
        
        # Tickets by department
        department_counts = {}
        for dept in Department.objects.all():
            count = tickets.filter(department=dept).count()
            if count > 0:
                department_counts[dept.name] = count
        
        # SLA compliance
        tickets_with_sla = tickets.exclude(sla_deadline=None)
        total_with_sla = tickets_with_sla.count()
        
        # Count tickets that were closed before SLA deadline
        if total_with_sla > 0:
            compliant_tickets = tickets_with_sla.filter(
                resolved_at__lte=models.F('sla_deadline')
            ).count()
            
            sla_compliance_rate = (compliant_tickets / total_with_sla) * 100
        else:
            sla_compliance_rate = 0
        
        # Average resolution time
        closed_tickets = tickets.filter(
            status='closed',
            resolved_at__isnull=False
        )
        
        if closed_tickets.exists():
            resolution_times = []
            for ticket in closed_tickets:
                resolution_time = ticket.resolved_at - ticket.created_at
                resolution_times.append(resolution_time.total_seconds() / 3600)  # Convert to hours
            
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
        else:
            avg_resolution_time = 0
        
        # Return compiled report data
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'total_tickets': total_tickets,
            'status_counts': status_counts,
            'priority_counts': priority_counts,
            'category_counts': category_counts,
            'department_counts': department_counts,
            'sla_compliance_rate': sla_compliance_rate,
            'avg_resolution_time': avg_resolution_time,
            'resolution_time_unit': 'hours'
        }
