"""
Script to fix missing data in the PostgreSQL database
"""
import os
import sqlite3
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from ticket_system.models import Department, Category, UserProfile

def create_basic_data():
    """Create basic required data for the system to function."""
    # Create department if it doesn't exist
    dept, created = Department.objects.get_or_create(
        id=1,
        defaults={
            'name': 'General',
            'description': 'General Department'
        }
    )
    if created:
        print(f"Created department: {dept.name}")
    else:
        print(f"Department {dept.name} already exists")
    
    # Create category if it doesn't exist
    cat, created = Category.objects.get_or_create(
        id=1,
        defaults={
            'name': 'IT Support',
            'description': 'IT Support Issues',
            'department': dept
        }
    )
    if created:
        print(f"Created category: {cat.name}")
    else:
        print(f"Category {cat.name} already exists")

def migrate_users_from_sqlite():
    """Migrate users from SQLite to PostgreSQL."""
    # Connect to SQLite database
    sqlite_conn = sqlite3.connect('db.sqlite3')
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()
    
    # Get all users from SQLite
    cursor.execute("SELECT * FROM auth_user")
    users = cursor.fetchall()
    print(f"Found {len(users)} users in SQLite database")
    
    # Migrate each user
    for user_data in users:
        try:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User(
                    username=user_data['username'],
                    password=user_data['password'],  # This preserves the hashed password
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    email=user_data['email'],
                    is_staff=bool(user_data['is_staff']),
                    is_active=bool(user_data['is_active']),
                    is_superuser=bool(user_data['is_superuser']),
                    date_joined=user_data['date_joined'],
                    last_login=user_data['last_login'] if user_data['last_login'] else None
                )
                user.save()
                
                # Create user profile
                dept = Department.objects.first()  # Get the first department
                UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'department': dept,
                        'phone_number': '',
                        'job_title': 'User',
                        'timezone': 'UTC'
                    }
                )
                
                print(f"Migrated user: {user.username}")
            else:
                print(f"User {user_data['username']} already exists, skipping")
        except Exception as e:
            print(f"Error migrating user {user_data['username']}: {e}")
    
    # Close SQLite connection
    sqlite_conn.close()

if __name__ == '__main__':
    print("Creating basic data...")
    create_basic_data()
    
    print("\nMigrating users from SQLite...")
    migrate_users_from_sqlite()
    
    print("\nDone!")
