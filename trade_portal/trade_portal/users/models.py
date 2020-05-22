from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    def __str__(self):
        fullname = f"{self.first_name} {self.last_name}".strip()
        return fullname or self.email or self.username or super().__str__()
