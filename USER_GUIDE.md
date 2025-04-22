# Ticket Management System - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [User Roles](#user-roles)
4. [Regular User Guide](#regular-user-guide)
5. [Staff User Guide](#staff-user-guide)
6. [Administrator Guide](#administrator-guide)
7. [AI Features](#ai-features)
8. [API Integration](#api-integration)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

## Introduction

The Ticket Management System is a comprehensive solution for handling support requests and service tickets. It provides an efficient way to create, track, and resolve tickets with advanced features like AI-powered ticket routing, SLA tracking, and detailed reporting.

### Key Features

- Role-based access control with different permission levels
- Ticket creation, tracking, and management
- Department and category organization
- AI-powered ticket classification and routing
- SLA monitoring and breach alerts
- Comprehensive reporting and analytics
- RESTful API for integration with other systems
- Real-time notifications
- File attachments
- Escalation workflow

## Getting Started

### Accessing the System

1. Open your web browser and navigate to the system URL (e.g., `https://tickets.yourdomain.com`)
2. You'll be presented with the login screen
3. If you don't have an account, click on the "Register" link to create one

### Registration

1. Fill in your personal details (name, email, username)
2. Choose a strong password
3. Select your department from the dropdown menu
4. Accept the terms and conditions
5. Click "Register"
6. You may need approval from an administrator before your account is activated

### Logging In

1. Enter your username and password
2. Optionally check "Remember me" for a longer session
3. Click "Login"
4. If you forgot your password, click on "Forgot your password?" to reset it

### Dashboard Overview

After logging in, you'll land on the dashboard which displays:

- Quick statistics relevant to your role
- Recent tickets
- Notifications
- SLA warnings
- Charts showing ticket distribution (by status, priority, etc.)

## User Roles

The system has three main user roles:

### Regular User

- Can create and view their own tickets
- Can comment on their tickets
- Can view ticket status and updates
- Can close their own tickets

### Staff User

- All regular user capabilities
- Can view tickets assigned to their department
- Can respond to tickets
- Can update ticket status, priority, and category
- Can assign tickets to other staff members
- Can view internal notes and add internal comments

### Administrator

- All staff user capabilities
- Can manage users, departments, and categories
- Can view and modify all tickets
- Can access system reports and analytics
- Can configure system settings
- Can view system logs

## Regular User Guide

### Creating a New Ticket

1. Click the "Create New Ticket" button on the dashboard or ticket list page
2. Fill in the ticket details:
   - Title: A brief summary of the issue
   - Department: Select the relevant department
   - Category: Choose the appropriate category based on your issue
   - Priority: Select the priority level
   - Description: Provide a detailed description of the issue
3. Add attachments if needed (screenshots, documents, etc.)
4. Click "Submit Ticket"

### Viewing Your Tickets

1. Click on "My Tickets" in the navigation menu
2. The list shows all your tickets with status, priority, and creation date
3. Use the filters to sort and find specific tickets
4. Click on any ticket ID or title to view its details

### Ticket Detail View

The ticket detail page shows:

- Ticket information (ID, status, priority, etc.)
- Full description
- Attachments
- Comment thread
- SLA information

### Adding Comments

1. Scroll to the comment section at the bottom of the ticket detail page
2. Type your comment in the text box
3. Click "Submit Comment"

### Closing a Ticket

1. Open the ticket you wish to close
2. Click the "Close Ticket" button on the right side
3. Optionally, add a final comment explaining why you're closing the ticket
4. Confirm the action

## Staff User Guide

### Viewing Assigned Tickets

1. Navigate to the dashboard or ticket list
2. By default, you'll see tickets assigned to you and your department
3. Use filters to sort by status, priority, SLA breach, etc.

### Responding to Tickets

1. Open the ticket you want to respond to
2. Add your comment in the comment box
3. Check "Mark as internal note" if you don't want the comment to be visible to the requester
4. Click "Submit Comment"

### Updating Ticket Status

1. Open the ticket
2. Use the status dropdown in the actions panel
3. Select the new status
4. Click "Update Status"
5. Common status transitions:
   - New → In Progress (when you start working on it)
   - In Progress → Pending (when waiting for user input)
   - Pending → In Progress (when continuing work)
   - In Progress → Resolved (when the issue is fixed)
   - Resolved → Closed (final state, usually after user confirmation)

### Assigning Tickets

1. Open the ticket
2. Use the assign dropdown in the actions panel
3. Select the staff member to assign the ticket to
4. Click "Assign"

### Changing Ticket Priority

1. Open the ticket
2. Use the priority dropdown in the actions panel
3. Select the new priority level
4. Click "Update Priority"

### Handling SLA Breaches

1. Tickets approaching SLA breach will be highlighted in yellow
2. Tickets that have breached SLA will be highlighted in red
3. Prioritize tickets based on SLA status
4. For breached tickets, consider escalation or reassignment

### Escalating Tickets

1. Open the ticket that needs escalation
2. Click the "Escalate Ticket" button
3. Provide a reason for escalation
4. The ticket will be escalated to a higher priority and flagged for management attention

## Administrator Guide

### User Management

1. Navigate to Admin → User Management
2. View a list of all users
3. Actions available:
   - Create new users
   - Edit existing user details
   - Activate/deactivate users
   - Reset passwords
   - Change roles
   - Assign departments

### Department and Category Management

1. Navigate to Admin → Departments or Admin → Categories
2. View existing items
3. Add new departments/categories
4. Edit or deactivate existing ones
5. Associate categories with departments

### System Settings

1. Navigate to Admin → System Settings
2. Configure:
   - SLA definitions
   - Email notification settings
   - Automatic assignment rules
   - AI configuration
   - System appearance

### Reports and Analytics

1. Navigate to Admin → Reports
2. View predefined reports:
   - Ticket volume over time
   - Resolution time averages
   - SLA compliance
   - Staff performance
   - Department workload
3. Generate custom reports by selecting parameters and filters
4. Export reports to CSV or PDF

### System Logs

1. Navigate to Admin → System Logs
2. View logs of system activities for auditing purposes
3. Filter logs by date, user, action type, etc.

## AI Features

### AI-Powered Classification

The system uses advanced AI to automatically:
- Analyze the sentiment of tickets
- Suggest appropriate categories
- Recommend priority levels
- Suggest staff members for assignment

### Viewing AI Suggestions

1. Open a ticket
2. Look for the AI badge icon next to the ticket title
3. Click on the badge to view AI suggestions
4. Suggestions include:
   - Sentiment analysis
   - Suggested category
   - Suggested priority
   - Recommended assignee

### Providing AI Feedback

1. After reviewing AI suggestions, you can provide feedback on their accuracy
2. Click the "Provide Feedback" link in the AI analysis panel
3. Select whether the suggestion was correct or incorrect
4. If incorrect, provide the correct value
5. This feedback helps improve the AI model over time

## API Integration

The system provides a RESTful API for integration with other applications:

### Authentication

```
POST /api/token/
```
Request body:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

Response:
```json
{
  "access": "access_token_value",
  "refresh": "refresh_token_value"
}
```

### List Tickets

```
GET /api/tickets/
```

Headers:
```
Authorization: Bearer your_access_token
```

### Create Ticket

```
POST /api/tickets/
```

Headers:
```
Authorization: Bearer your_access_token
Content-Type: application/json
```

Request body:
```json
{
  "title": "Ticket title",
  "description": "Detailed description",
  "priority": "medium",
  "department": 1,
  "category": 2
}
```

### More API Documentation

For full API documentation, refer to `/api/docs/` when logged in as an administrator.

## Troubleshooting

### Common Issues

#### Can't Login

- Verify your username and password
- Check if your account is activated
- Check if your account is locked due to too many failed attempts
- Try the password reset function

#### Missing Tickets

- Check if the correct filters are applied
- Verify you have the correct permissions
- Check if you're looking in the right department

#### Notification Issues

- Check your browser notifications settings
- Verify your email address is correct in your profile
- Check your email spam folder

#### Attachment Problems

- Ensure the file size is under the limit (usually 5MB)
- Check that the file type is supported
- Try compressing the file if it's too large

### Getting Help

If you encounter issues that aren't covered here:

1. Click on the "Help" link in the footer
2. Check the knowledge base for solutions
3. Contact system administrators using the support form
4. Email support at support@yourdomain.com

## FAQ

**Q: How do I change my password?**

A: Click on your username in the top-right corner, select "My Profile", then "Change Password".

**Q: Can I edit a ticket after submitting it?**

A: Regular users can edit tickets only if they haven't been assigned to staff yet. Staff and administrators can edit tickets at any time.

**Q: How are SLA targets determined?**

A: SLA targets are based on the ticket priority and category. Higher priority tickets have shorter resolution time targets.

**Q: What happens when a ticket is escalated?**

A: Escalated tickets are flagged for management attention, given a higher priority, and may be reassigned to more experienced staff.

**Q: Can I bulk update multiple tickets?**

A: Administrators and staff can select multiple tickets in the ticket list view and apply batch actions like status updates or reassignment.

**Q: How does the AI ticket classification work?**

A: The system uses natural language processing to analyze the ticket content, compare it with historical data, and suggest appropriate categorization and routing.

**Q: Can I use the system on mobile devices?**

A: Yes, the system is fully responsive and works on smartphones and tablets.
