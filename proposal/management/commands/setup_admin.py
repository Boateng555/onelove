import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from proposal.models import SiteContent


class Command(BaseCommand):
    help = 'Create admin user and seed default template content'

    def add_arguments(self, parser):
        parser.add_argument('--username', default=os.environ.get('ADMIN_USERNAME', 'admin'))
        parser.add_argument('--password', default=os.environ.get('ADMIN_PASSWORD', 'nolove123'))
        parser.add_argument('--email', default=os.environ.get('ADMIN_EMAIL', 'admin@local.dev'))

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        password = options['password']
        email = options['email']

        SiteContent.load()
        self.stdout.write(self.style.SUCCESS('Default template content ready'))

        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.is_staff = True
        user.is_superuser = True
        if created:
            user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated admin user: {username}'))

        self.stdout.write('')
        self.stdout.write('Dashboard login:')
        self.stdout.write(f'  URL:      http://127.0.0.1:8000/dashboard/login/')
        self.stdout.write(f'  Username: {username}')
        self.stdout.write(f'  Password: {password}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Change your password after first login!'))
