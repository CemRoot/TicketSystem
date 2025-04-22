from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ticket_system.models import UserProfile, Department, Role


class Command(BaseCommand):
    help = 'Creates missing UserProfile records for users that don\'t have them'

    def handle(self, *args, **options):
        users_without_profiles = []
        
        # Get default role and department (or create them if they don't exist)
        default_role, created = Role.objects.get_or_create(
            name="User",
            defaults={
                'description': 'Regular user role',
                'is_admin': False,
                'is_staff': False,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created default role: {default_role.name}'))
        
        default_department, created = Department.objects.get_or_create(
            name="General",
            defaults={
                'description': 'General department',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created default department: {default_department.name}'))

        # Find users without profiles
        for user in User.objects.all():
            try:
                # Try to access the profile
                profile = user.profile
            except UserProfile.DoesNotExist:
                users_without_profiles.append(user)
        
        # Create missing profiles
        for user in users_without_profiles:
            UserProfile.objects.create(
                user=user,
                department=default_department,
                role=default_role,
                phone_number=""
            )
            self.stdout.write(self.style.SUCCESS(f'Created profile for user: {user.username}'))
        
        if not users_without_profiles:
            self.stdout.write(self.style.SUCCESS('No missing profiles found!'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created {len(users_without_profiles)} missing profiles'))
