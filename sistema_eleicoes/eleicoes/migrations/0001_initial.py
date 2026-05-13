# Generated migration para o modelo Eleitor e outros modelos do app eleicoes
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Eleicao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200)),
                ('descricao', models.TextField(blank=True)),
                ('data_inicio', models.DateTimeField()),
                ('data_fim', models.DateTimeField()),
                ('status', models.CharField(choices=[('RASCUNHO', 'Rascunho'), ('ABERTA', 'Aberta'), ('ENCERRADA', 'Encerrada'), ('APURADA', 'Apurada')], default='RASCUNHO', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Eleitor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, verbose_name='Nome Completo')),
                ('email', models.EmailField(error_messages={'unique': 'Este e-mail já está cadastrado no sistema.'}, help_text='E-mail único do eleitor', max_length=254, unique=True, verbose_name='E-mail')),
                ('cpf', models.CharField(error_messages={'unique': 'Este CPF já está cadastrado no sistema.'}, help_text='Formato: 000.000.000-00', max_length=14, unique=True, verbose_name='CPF')),
                ('data_nascimento', models.DateField(help_text='Data de nascimento do eleitor', verbose_name='Data de Nascimento')),
                ('ativo', models.BooleanField(default=True, help_text='Define se o eleitor está ativo no sistema', verbose_name='Ativo')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, help_text='Data e hora do cadastro (preenchido automaticamente)', verbose_name='Data de Cadastro')),
            ],
            options={
                'verbose_name': 'Eleitor',
                'verbose_name_plural': 'Eleitores',
                'ordering': ['nome'],
                'indexes': [
                    models.Index(fields=['email'], name='eleicoes_el_email_3702e4_idx'),
                    models.Index(fields=['cpf'], name='eleicoes_el_cpf_f0a9d7_idx'),
                    models.Index(fields=['ativo'], name='eleicoes_el_ativo_1b267a_idx'),
                    models.Index(fields=['data_cadastro'], name='eleicoes_el_data_ca_d104be_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Candidato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=200)),
                ('numero', models.PositiveIntegerField()),
                ('partido', models.CharField(blank=True, max_length=100)),
                ('foto_url', models.URLField(blank=True)),
                ('descricao', models.TextField(blank=True)),
                ('eleicao', models.ForeignKey(on_delete=models.CASCADE, related_name='candidatos', to='eleicoes.eleicao')),
            ],
            options={
                'unique_together': {('eleicao', 'numero')},
                'ordering': ['numero'],
            },
        ),
        migrations.CreateModel(
            name='Voto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('voto_em_branco', models.BooleanField(default=False)),
                ('hash_comprovante', models.CharField(max_length=64, unique=True)),
                ('data_hora_voto', models.DateTimeField(auto_now_add=True)),
                ('candidato', models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, related_name='votos', to='eleicoes.candidato')),
                ('eleicao', models.ForeignKey(on_delete=models.CASCADE, related_name='votos', to='eleicoes.eleicao')),
            ],
            options={
                'verbose_name': 'Voto',
                'verbose_name_plural': 'Votos',
                'indexes': [models.Index(fields=['eleicao', 'data_hora_voto'], name='eleicoes_vo_eleicao_5a9f5f_idx')],
            },
        ),
        migrations.CreateModel(
            name='RegistroVotacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_hora_registro', models.DateTimeField(auto_now_add=True)),
                ('eleicao', models.ForeignKey(on_delete=models.CASCADE, related_name='registros_votacao', to='eleicoes.eleicao')),
                ('eleitor', models.ForeignKey(on_delete=models.CASCADE, related_name='registros_votacao', to='eleicoes.eleitor')),
            ],
            options={
                'verbose_name': 'Registro de Votação',
                'verbose_name_plural': 'Registros de Votação',
                'unique_together': {('eleicao', 'eleitor')},
            },
        ),
    ]
