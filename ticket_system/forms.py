"""
Forms for the ticket management system.
"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Ticket, TicketComment, Department, Category, SubCategory,
    Role, UserProfile, TicketAttachment
)


class UserRegistrationForm(UserCreationForm):
    """Form for user registration."""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=20, required=False)
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="Select Department"
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 
                'password1', 'password2', 'phone_number', 'department')

    def clean_email(self):
        """Validate that the email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email address already in use.")
        return email

    def save(self, commit=True):
        """Override save to create user profile."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create profile
            UserProfile.objects.create(
                user=user,
                department=self.cleaned_data.get('department'),
                phone_number=self.cleaned_data.get('phone_number', '')
            )
        return user


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile."""
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = ('department', 'role', 'phone_number', 'profile_picture')
        
    def __init__(self, *args, **kwargs):
        """Initialize with user data."""
        instance = kwargs.get('instance')
        if instance:
            kwargs.setdefault('initial', {})
            kwargs['initial'].update({
                'first_name': instance.user.first_name,
                'last_name': instance.user.last_name,
                'email': instance.user.email,
            })
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        """Save user and profile data."""
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            profile.save()
        return profile


class AdminUserCreateForm(forms.ModelForm):
    """Form for administrators to create users."""
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput, required=True)
    is_active = forms.BooleanField(initial=True, required=False)
    
    class Meta:
        model = UserProfile
        fields = ('department', 'role', 'phone_number', 'profile_picture')
        
    def clean_username(self):
        """Validate that the username is unique."""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already in use.")
        return username
        
    def clean_email(self):
        """Validate that the email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email address already in use.")
        return email
        
    def clean(self):
        """Validate that passwords match."""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        
        return cleaned_data
        
    def save(self, commit=True):
        """Create user and profile."""
        profile = super().save(commit=False)
        
        # Create the user
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            is_active=self.cleaned_data['is_active']
        )
        
        # Set staff/admin status based on role
        if profile.role:
            user.is_staff = profile.role.is_staff
            user.is_superuser = profile.role.is_admin
            user.save()
        
        profile.user = user
        
        if commit:
            profile.save()
        
        return profile


class TicketForm(forms.ModelForm):
    """Form for creating and editing tickets."""
    is_urgent = forms.BooleanField(required=False)
    
    # Add dropdown choices for priority with better names
    PRIORITY_CHOICES = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('critical', 'Critical/Urgent')
    ]
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, required=False)
    
    class Meta:
        model = Ticket
        fields = ('title', 'description', 'department', 'category', 'subcategory', 'priority', 'source')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'source': forms.HiddenInput(),  # Hide source field and set default in __init__
            'department': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'subcategory': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with dynamic category/subcategory choices."""
        super().__init__(*args, **kwargs)
        
        # Set default source to 'web'
        self.initial['source'] = 'web'
        
        # Make some fields not required to allow for AI suggestions
        self.fields['priority'].required = False
        self.fields['category'].required = False
        self.fields['department'].required = False
        
        # Improve field labels and help text
        self.fields['priority'].help_text = "AI will suggest a priority if you leave this blank"
        self.fields['category'].help_text = "AI will suggest a category if you leave this blank"
        self.fields['department'].help_text = "Select the department for your ticket"
        
        # If department is selected, filter categories
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['category'].queryset = Category.objects.filter(
                    department_id=department_id, is_active=True
                )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.department:
            # If editing existing ticket, filter by its department
            self.fields['category'].queryset = Category.objects.filter(
                department=self.instance.department, is_active=True
            )
        else:
            # Otherwise, show all active categories
            self.fields['category'].queryset = Category.objects.filter(is_active=True)
        
        # If category is selected, filter subcategories
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['subcategory'].queryset = SubCategory.objects.filter(
                    category_id=category_id, is_active=True
                )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.category:
            self.fields['subcategory'].queryset = SubCategory.objects.filter(
                category=self.instance.category, is_active=True
            )
        
    def clean(self):
        """Validate that start date is before end date."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date must be before end date.")
        
        return cleaned_data


class TicketCommentForm(forms.ModelForm):
    """Form for adding comments to tickets."""
    
    class Meta:
        model = TicketComment
        fields = ('content', 'is_internal')
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
        }


class TicketAttachmentForm(forms.ModelForm):
    """Form for uploading attachments to tickets."""
    
    class Meta:
        model = TicketAttachment
        fields = ('file',)
        
    def save(self, commit=True, ticket=None, user=None):
        """Save attachment with file metadata."""
        instance = super().save(commit=False)
        
        if ticket:
            instance.ticket = ticket
        
        if user:
            instance.uploaded_by = user
        
        # Get file metadata
        file = self.cleaned_data['file']
        instance.file_name = file.name
        instance.file_type = file.content_type
        instance.file_size = file.size
        
        if commit:
            instance.save()
        
        return instance


class TicketFilterForm(forms.Form):
    """Form for filtering tickets."""
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Ticket.STATUS_CHOICES),
        required=False
    )
    priority = forms.ChoiceField(
        choices=[('', 'All Priorities')] + list(Ticket.PRIORITY_CHOICES),
        required=False
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="All Departments"
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories"
    )
    created_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    created_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    keyword = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search in title and description'})
    )
    is_escalated = forms.BooleanField(required=False)
    sla_breach = forms.BooleanField(required=False)


class DepartmentForm(forms.ModelForm):
    """Form for creating and editing departments."""
    
    class Meta:
        model = Department
        fields = ('name', 'description')


class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories."""
    
    class Meta:
        model = Category
        fields = ('name', 'description', 'department', 'is_active')


class SubCategoryForm(forms.ModelForm):
    """Form for creating and editing subcategories."""
    
    class Meta:
        model = SubCategory
        fields = ('name', 'description', 'category', 'is_active')


class RoleForm(forms.ModelForm):
    """Form for creating and editing roles."""
    
    class Meta:
        model = Role
        fields = ('name', 'description', 'is_staff', 'is_admin')
    
    def clean(self):
        """Validate that admin roles are also staff roles."""
        cleaned_data = super().clean()
        is_admin = cleaned_data.get('is_admin')
        is_staff = cleaned_data.get('is_staff')
        
        if is_admin and not is_staff:
            # If role is admin, it must also be staff
            cleaned_data['is_staff'] = True
            self.data = self.data.copy()
            self.data['is_staff'] = True
        
        return cleaned_data


class DateRangeForm(forms.Form):
    """Form for selecting a date range for reports."""
    start_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=lambda: (timezone.now() - timezone.timedelta(days=30)).date()
    )
    end_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().date
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="All Departments"
    )

    def clean(self):
        """Validate that start date is before end date."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date must be before end date.")
        
        return cleaned_data
