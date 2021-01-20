from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from trade_portal.users.models import Organisation, OrgMembership

class Command(BaseCommand):
    help = (
        'Creates a new test user, with org and verified email'
    )

    # def add_arguments(self, parser):
        # parser.add_argument('username', type=str)
        # parser.add_argument('password', type=str)

    def handle(self, *args, **kwargs):
        user, created = get_user_model().objects.get_or_create(username='test_user')#kwargs['username'])
        user.set_password('test_user@test.com')#string_or_b64kms(kwargs['password']))
        user.first_name = 'Testy'
        user.last_name = 'McTestface'
        user.email = 'test_user@test.com'#kwargs['username']
        user.initial_business_id = '0123456789'
        user.mobile_number = '+61412345678'
        user.is_superuser = False
        user.is_staff = False
        user.save()

        if created:
            self.stdout.write("User created\n")
        else:
            self.stdout.write("User details reset\n")

        org, created = Organisation.objects.get_or_create(business_id='0123456789')
        org.name = f'ABN {org.business_id}'
        org.dot_separated_id = f'org.{org.business_id}.ABN'
        org.initial_business_id = '0123456789'
        org.is_trader = True
        org.is_chambers = True
        org.is_regulator = False
        org.save()

        if created:
            self.stdout.write("Org created\n")
        else:
            self.stdout.write("Org details reset\n")

        org_membership, created = OrgMembership.objects.get_or_create(user=user,org=org)
        # org_membership.since=datetime.now()
        org_membership.role = OrgMembership.ROLE_USER
        org_membership.save()
        if created:
            self.stdout.write("Org membership created\n")
        else:
            self.stdout.write("Org membership reset\n")

        email_address, created = EmailAddress.objects.get_or_create(email=user.email, user=user)
        email_address.verified = True
        email_address.primary = True
        email_address.save()

        if created:
            self.stdout.write("Email address record created\n")
        else:
            self.stdout.write("Email address record reset\n")

