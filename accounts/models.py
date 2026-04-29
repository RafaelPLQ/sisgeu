from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    curso = models.CharField(max_length=150, blank=True, null=True)
    instituicao = models.CharField(max_length=200, blank=True, null=True)
    data_nascimento = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username


@receiver(post_save, sender=User)
def criar_ou_salvar_perfil(sender, instance, created, **kwargs):
    """
    Cria o Perfil quando um User é criado.
    BUG CORRIGIDO: o signal anterior chamava instance.perfil.save() em todo post_save do User,
    o que causava um save() desnecessário (e potencial loop). Agora só cria se for novo.
    """
    if created:
        Perfil.objects.get_or_create(usuario=instance)
