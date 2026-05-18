from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_alter_transaction_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='alert',
            name='state_hash',
            field=models.CharField(max_length=16, blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='alert',
            name='alert_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('orcamento_80', 'Orçamento em Alerta'),
                    ('orcamento_100', 'Orçamento Estourado / No Limite'),
                    ('meta_prazo', 'Meta com Prazo Próximo'),
                    ('meta_vencida', 'Meta Vencida'),
                    ('meta_concluida', 'Meta Concluída'),
                    ('saldo_negativo', 'Saldo Negativo'),
                    ('saldo_projetado', 'Saldo Projetado Negativo'),
                ],
            ),
        ),
    ]