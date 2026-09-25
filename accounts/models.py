from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Пользователь системы мониторинга.

    Пока расширяет стандартного пользователя Django без дополнительных
    полей. Собственная модель создаётся сразу, чтобы в дальнейшем можно
    было безопасно добавлять необходимые данные и права.
    """

    def __str__(self):
        return self.get_full_name() or self.username
