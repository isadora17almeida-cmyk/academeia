from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    AREA_CHOICES = [
        ('direito', 'Direito'),
        ('medicina', 'Medicina'),
        ('ambos', 'Ambos'),
        ('geral', 'Geral'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField('nome completo', max_length=180, blank=True)
    study_area = models.CharField('área de estudo', max_length=20, choices=AREA_CHOICES, default='geral')
    college = models.CharField('faculdade', max_length=180, blank=True)
    objective = models.CharField('objetivo', max_length=220, blank=True)
    avatar = models.FileField('foto de perfil', upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil do usuário'
        verbose_name_plural = 'Perfis dos usuários'

    def __str__(self):
        return self.full_name or self.user.get_username()

    @property
    def display_name(self):
        return self.full_name or self.user.get_full_name() or self.user.get_username()

    @property
    def initials(self):
        source = self.display_name.strip() or self.user.get_username()
        parts = [part for part in source.replace('@', ' ').split() if part]
        if not parts:
            return 'AI'
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def avatar_url(self):
        try:
            if self.avatar:
                return self.avatar.url
        except Exception:
            return ''
        return ''


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, full_name=instance.get_full_name())
    else:
        Profile.objects.get_or_create(user=instance)
        instance.profile.save()
