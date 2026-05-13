from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('eleicoes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Candidato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.PositiveIntegerField(help_text='Número de identificação do candidato na urna (único por eleição)', validators=[django.core.validators.MinValueValidator(1, message='Número do candidato deve ser maior que zero.'), django.core.validators.MaxValueValidator(99999, message='Número do candidato muito grande.')], verbose_name='Número')),
                ('nome', models.CharField(help_text='Nome completo do candidato', max_length=150, verbose_name='Nome Completo')),
                ('nome_urna', models.CharField(help_text='Nome que aparecerá na urna eletrônica (máximo 50 caracteres)', max_length=50, verbose_name='Nome na Urna')),
                ('partido_ou_chapa', models.CharField(blank=True, help_text='Partido político ou chapa do candidato (opcional)', max_length=100, verbose_name='Partido/Chapa')),
                ('proposta', models.TextField(blank=True, help_text='Proposta ou plano de governo do candidato', verbose_name='Proposta')),
                ('foto_url', models.URLField(blank=True, help_text='URL da foto do candidato (opcional)', verbose_name='URL da Foto')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
                ('eleicao', models.ForeignKey(help_text='Eleição à qual o candidato pertence', on_delete=django.db.models.deletion.CASCADE, related_name='candidatos', to='eleicoes.eleicao', verbose_name='Eleição')),
            ],
            options={
                'verbose_name': 'Candidato',
                'verbose_name_plural': 'Candidatos',
                'ordering': ['eleicao', 'numero'],
                'indexes': [
                    models.Index(fields=['eleicao', 'numero'], name='eleicoes_ca_eleicao_146015_idx'),
                    models.Index(fields=['eleicao', 'nome'], name='eleicoes_ca_eleicao_c01332_idx'),
                    models.Index(fields=['nome_urna'], name='eleicoes_ca_nome_ur_612fff_idx'),
                ],
                'unique_together': {('eleicao', 'numero')},
            },
        ),
    ]