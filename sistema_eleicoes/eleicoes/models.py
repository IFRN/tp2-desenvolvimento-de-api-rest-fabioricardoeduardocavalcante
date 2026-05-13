from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import secrets
import hashlib
import re

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models_eleitor import Eleitor  # Assumindo que Eleitor está em models_eleitor.py

class Eleicao(models.Model):
    """
    Entidade de Eleição conforme especificação do projeto.
    """
    
    # Choices para tipo de eleição
    class TipoEleicao(models.TextChoices):
        ESTUDANTIL = 'estudantil', 'Estudantil'
        SINDICAL = 'sindical', 'Sindical'
        ASSOCIACAO = 'associacao', 'Associação'
        CONDOMINIO = 'condominio', 'Condomínio'
        CONSELHO = 'conselho', 'Conselho'
        OUTRA = 'outra', 'Outra'
    
    # Choices para status da eleição
    class StatusEleicao(models.TextChoices):
        RASCUNHO = 'rascunho', 'Rascunho'
        ABERTA = 'aberta', 'Aberta'
        ENCERRADA = 'encerrada', 'Encerrada'
        APURADA = 'apurada', 'Apurada'
    
    # Fluxo permitido de status
    STATUS_TRANSITIONS = {
        StatusEleicao.RASCUNHO: [StatusEleicao.ABERTA],
        StatusEleicao.ABERTA: [StatusEleicao.ENCERRADA],
        StatusEleicao.ENCERRADA: [StatusEleicao.APURADA],
        StatusEleicao.APURADA: [],  # Terminal, não pode mudar
    }
    
    # Campos da entidade
    titulo = models.CharField(
        max_length=200,
        verbose_name='Título',
        help_text='Título da eleição'
    )
    
    descricao = models.TextField(
        blank=True,
        verbose_name='Descrição',
        help_text='Descrição detalhada da eleição'
    )
    
    tipo = models.CharField(
        max_length=20,
        choices=TipoEleicao.choices,
        verbose_name='Tipo de Eleição',
        help_text='Tipo da eleição (estudantil, sindical, associação, etc.)'
    )
    
    data_inicio = models.DateTimeField(
        verbose_name='Data e Hora de Início',
        help_text='Data e hora de início da votação'
    )
    
    data_fim = models.DateTimeField(
        verbose_name='Data e Hora de Término',
        help_text='Data e hora de término da votação'
    )
    
    status = models.CharField(
        max_length=20,
        choices=StatusEleicao.choices,
        default=StatusEleicao.RASCUNHO,
        verbose_name='Status',
        help_text='Status atual da eleição'
    )
    
    permite_branco = models.BooleanField(
        default=True,
        verbose_name='Permite Voto em Branco',
        help_text='Define se o voto em branco é permitido nesta eleição'
    )
    
    criada_por = models.ForeignKey(
        Eleitor,
        on_delete=models.PROTECT,  # PROTECT impede exclusão do administrador se criou eleições
        related_name='eleicoes_criadas',
        verbose_name='Criada por',
        help_text='Administrador responsável pela criação da eleição'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Data de Atualização'
    )
    
    class Meta:
        verbose_name = 'Eleição'
        verbose_name_plural = 'Eleições'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['tipo']),
            models.Index(fields=['data_inicio']),
            models.Index(fields=['data_fim']),
            models.Index(fields=['status', 'data_inicio']),  # Índice composto para consultas comuns
        ]
    
    def __str__(self):
        return f"{self.titulo} ({self.get_status_display()})"
    
    def clean(self):
        """
        Validações customizadas:
        1. data_fim > data_inicio
        2. Fluxo de status permitido
        3. Data de início não pode ser passada se status for rascunho
        4. Validações específicas por status
        """
        super().clean()
        
        # Validar período de votação
        if self.data_inicio and self.data_fim:
            if self.data_fim <= self.data_inicio:
                raise ValidationError({
                    'data_fim': 'A data e hora de término deve ser posterior à data e hora de início.'
                })
        
        # Validar fluxo de status
        if self.pk:  # Se for update (já existe no banco)
            self._validar_transicao_status()
        
        # Validações específicas por status
        self._validar_status_atual()
        
        # Validar datas conforme status
        self._validar_datas_por_status()
    
    def _validar_transicao_status(self):
        """
        Valida se a transição de status é permitida
        """
        if hasattr(self, '_original_status'):
            original_status = self._original_status
        else:
            # Buscar status original do banco
            try:
                original = Eleicao.objects.get(pk=self.pk)
                original_status = original.status
            except Eleicao.DoesNotExist:
                return  # Nova instância, não validar transição
        
        # Se status não mudou, não validar
        if original_status == self.status:
            return
        
        # Verificar se transição é permitida
        transicoes_permitidas = self.STATUS_TRANSITIONS.get(original_status, [])
        if self.status not in transicoes_permitidas:
            status_anterior = self.get_status_display(original_status)
            status_novo = self.get_status_display(self.status)
            
            raise ValidationError({
                'status': f'Não é permitido alterar o status de "{status_anterior}" para "{status_novo}". '
                         f'Fluxo permitido: rascunho → aberta → encerrada → apurada (sem voltar).'
            })
    
    def _validar_status_atual(self):
        """
        Valida regras específicas de cada status
        """
        if self.status == self.StatusEleicao.ABERTA:
            # Verificar se tem pelo menos 2 candidatos
            if hasattr(self, 'candidatos'):
                if self.candidatos.count() < 2:
                    raise ValidationError({
                        'status': 'Não é possível abrir uma eleição com menos de 2 candidatos.'
                    })
        
        elif self.status == self.StatusEleicao.ENCERRADA:
            # Verificar se data_fim já passou ou se foi forçado
            if self.data_fim and self.data_fim > timezone.now():
                # Permitir encerramento antecipado com validação específica
                pass
        
        elif self.status == self.StatusEleicao.APURADA:
            # Verificar se já está encerrada
            if hasattr(self, '_original_status'):
                if self._original_status != self.StatusEleicao.ENCERRADA:
                    raise ValidationError({
                        'status': 'Apenas eleições encerradas podem ser apuradas.'
                    })
    
    def _validar_datas_por_status(self):
        """
        Valida datas conforme o status da eleição
        """
        agora = timezone.now()
        
        if self.status == self.StatusEleicao.RASCUNHO:
            # Em rascunho, datas podem ser ajustadas livremente
            pass
        
        elif self.status == self.StatusEleicao.ABERTA:
            # Verificar se data_início não é futura demais (opcional)
            if self.data_inicio and self.data_inicio > agora + timezone.timedelta(days=365):
                raise ValidationError({
                    'data_inicio': 'A data de início não pode ser mais de 1 ano no futuro.'
                })
        
        elif self.status == self.StatusEleicao.ENCERRADA:
            # Se está encerrada, data_fim deve ser <= agora OU foi encerrada antecipadamente
            if self.data_fim and self.data_fim > agora:
                # Caso de encerramento antecipado - permitido, mas com aviso
                pass
        
        elif self.status == self.StatusEleicao.APURADA:
            # Apurada deve ter data_fim <= agora
            if self.data_fim and self.data_fim > agora:
                raise ValidationError({
                    'status': 'Eleições apuradas devem ter data de término já passada.'
                })
    
    def save(self, *args, **kwargs):
        """
        Sobrescrita do save para garantir validações e armazenar status original
        """
        # Armazenar status original para validação de transição
        if self.pk:
            try:
                original = Eleicao.objects.get(pk=self.pk)
                self._original_status = original.status
            except Eleicao.DoesNotExist:
                pass
        
        self.full_clean()  # Executa todas as validações
        super().save(*args, **kwargs)
    
    @property
    def periodo_votacao(self):
        """
        Retorna período de votação formatado
        """
        if self.data_inicio and self.data_fim:
            return f"{self.data_inicio.strftime('%d/%m/%Y %H:%M')} até {self.data_fim.strftime('%d/%m/%Y %H:%M')}"
        return "Período não definido"
    
    @property
    def esta_ativa(self):
        """
        Verifica se a eleição está ativa (aberta e dentro do período)
        """
        agora = timezone.now()
        return (self.status == self.StatusEleicao.ABERTA and 
                self.data_inicio <= agora <= self.data_fim)
    
    @property
    def pode_votar(self):
        """
        Alias para esta_ativa (semanticamente melhor para votação)
        """
        return self.esta_ativa
    
    @property
    def status_anterior_permitido(self):
        """
        Retorna o status anterior permitido (para uso em transições)
        """
        for status_anterior, transicoes in self.STATUS_TRANSITIONS.items():
            if self.status in transicoes:
                return status_anterior
        return None
    
    @property
    def pode_ser_aberta(self):
        """
        Verifica se a eleição pode ser aberta
        """
        return (self.status == self.StatusEleicao.RASCUNHO and 
                self.candidatos.count() >= 2)
    
    @property
    def pode_ser_encerrada(self):
        """
        Verifica se a eleição pode ser encerrada
        """
        return self.status == self.StatusEleicao.ABERTA
    
    @property
    def pode_ser_apurada(self):
        """
        Verifica se a eleição pode ser apurada
        """
        return self.status == self.StatusEleicao.ENCERRADA
    
    def abrir(self):
        """
        Método para abrir a eleição
        """
        if self.pode_ser_aberta:
            self.status = self.StatusEleicao.ABERTA
            self.save()
            return True
        return False
    
    def encerrar(self):
        """
        Método para encerrar a eleição
        """
        if self.pode_ser_encerrada:
            self.status = self.StatusEleicao.ENCERRADA
            self.save()
            return True
        return False
    
    def apurar(self):
        """
        Método para apurar a eleição
        """
        if self.pode_ser_apurada:
            self.status = self.StatusEleicao.APURADA
            self.save()
            return True
        return False
    
    class Meta:
        ordering = ['-created_at']
    
    def clean(self):
        if self.data_inicio and self.data_fim:
            if self.data_fim <= self.data_inicio:
                raise ValidationError('Data fim deve ser posterior à data início')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def pode_votar(self):
        agora = timezone.now()
        return self.status == 'ABERTA' and self.data_inicio <= agora <= self.data_fim
    
    def __str__(self):
        return self.titulo


class Candidato(models.Model):
    eleicao = models.ForeignKey(Eleicao, on_delete=models.CASCADE, related_name='candidatos')
    nome = models.CharField(max_length=200)
    numero = models.PositiveIntegerField()
    partido = models.CharField(max_length=100, blank=True)
    foto_url = models.URLField(blank=True)
    descricao = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['eleicao', 'numero']
        ordering = ['numero']
    
    def clean(self):
        if self.numero == 0:
            raise ValidationError('Número 0 é reservado para voto em branco')
    
    def __str__(self):
        return f"{self.numero} - {self.nome}"


class Eleitor(models.Model):
    """
    Entidade de Eleitor conforme especificação do projeto.
    """
    nome = models.CharField(
        max_length=150,
        verbose_name='Nome Completo',
        help_text='Nome completo do eleitor'
    )
    
    email = models.EmailField(
        unique=True,
        verbose_name='E-mail',
        help_text='E-mail único do eleitor',
        error_messages={
            'unique': 'Este e-mail já está cadastrado no sistema.',
        }
    )
    
    cpf = models.CharField(
        max_length=14,
        unique=True,
        verbose_name='CPF',
        help_text='Formato: 000.000.000-00',
        error_messages={
            'unique': 'Este CPF já está cadastrado no sistema.',
        }
    )
    
    data_nascimento = models.DateField(
        verbose_name='Data de Nascimento',
        help_text='Data de nascimento do eleitor'
    )
    
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo',
        help_text='Define se o eleitor está ativo no sistema'
    )
    
    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Cadastro',
        help_text='Data e hora do cadastro (preenchido automaticamente)'
    )
    
    class Meta:
        verbose_name = 'Eleitor'
        verbose_name_plural = 'Eleitores'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['cpf']),
            models.Index(fields=['ativo']),
            models.Index(fields=['data_cadastro']),
        ]
    
    def __str__(self):
        return f"{self.nome} - {self.cpf}"
    
    def clean(self):
        """
        Validações customizadas:
        1. Formato do CPF
        2. Validade do CPF (dígitos verificadores)
        3. Idade mínima (16 anos para votar)
        4. Formato do email
        """
        super().clean()
        
        # Validar formato do CPF
        if self.cpf:
            self.cpf = self._limpar_cpf(self.cpf)
            if not self._validar_cpf(self.cpf):
                raise ValidationError({'cpf': 'CPF inválido. Verifique os dígitos.'})
            
            # Formatar CPF para exibição
            self.cpf = self._formatar_cpf(self.cpf)
        
        # Validar idade mínima (16 anos para votar)
        if self.data_nascimento:
            idade = self._calcular_idade(self.data_nascimento)
            if idade < 16:
                raise ValidationError({
                    'data_nascimento': f'Eleitor deve ter no mínimo 16 anos. Idade atual: {idade} anos.'
                })
        
        # Validar formato do email (validação adicional)
        if self.email:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', self.email):
                raise ValidationError({'email': 'Formato de e-mail inválido.'})
    
    def save(self, *args, **kwargs):
        """
        Sobrescrita do save para garantir validações
        """
        self.full_clean()  # Executa todas as validações
        super().save(*args, **kwargs)
    
    def _limpar_cpf(self, cpf):
        """
        Remove caracteres não numéricos do CPF
        """
        return re.sub(r'[^0-9]', '', cpf)
    
    def _formatar_cpf(self, cpf):
        """
        Formata CPF para o padrão 000.000.000-00
        """
        cpf_limpo = self._limpar_cpf(cpf)
        if len(cpf_limpo) == 11:
            return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
        return cpf
    
    def _validar_cpf(self, cpf):
        """
        Valida os dígitos verificadores do CPF
        Algoritmo oficial de validação de CPF
        """
        cpf = self._limpar_cpf(cpf)
        
        # Verificar se tem 11 dígitos
        if len(cpf) != 11:
            return False
        
        # Verificar se todos os dígitos são iguais (CPF inválido)
        if cpf == cpf[0] * 11:
            return False
        
        # Calcular primeiro dígito verificador
        soma = 0
        for i in range(9):
            soma += int(cpf[i]) * (10 - i)
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto
        
        # Calcular segundo dígito verificador
        soma = 0
        for i in range(10):
            soma += int(cpf[i]) * (11 - i)
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto
        
        # Verificar dígitos
        return digito1 == int(cpf[9]) and digito2 == int(cpf[10])
    
    def _calcular_idade(self, data_nascimento):
        """
        Calcula idade com base na data de nascimento
        """
        hoje = timezone.now().date()
        idade = hoje.year - data_nascimento.year
        if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
            idade -= 1
        return idade
    
    @property
    def idade(self):
        """
        Propriedade para obter idade atual
        """
        if self.data_nascimento:
            return self._calcular_idade(self.data_nascimento)
        return None
    
    @property
    def cpf_formatado(self):
        """
        Retorna CPF formatado
        """
        return self._formatar_cpf(self.cpf)
    
    @property
    def pode_votar(self):
        """
        Verifica se o eleitor está apto a votar (ativo e maior de 16 anos)
        """
        return self.ativo and (self.idade >= 16 if self.idade else False)


class RegistroVotacao(models.Model):
    """
    ENTIDADE DE COMPROVAÇÃO - Sabe APENAS que o eleitor X já votou na eleição Y
    NÃO sabe em quem ele votou.
    Atende às regras: 'um voto por eleitor' e 'lista de quem compareceu'
    """
    eleicao = models.ForeignKey(Eleicao, on_delete=models.CASCADE, related_name='registros_votacao')
    eleitor = models.ForeignKey(Eleitor, on_delete=models.CASCADE, related_name='registros_votacao')
    data_hora_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Garante que cada eleitor vote apenas UMA vez por eleição
        unique_together = ['eleicao', 'eleitor']
        verbose_name = 'Registro de Votação'
        verbose_name_plural = 'Registros de Votação'
        # IMPORTANTE: NÃO há qualquer campo linkando ao Voto
    
    def __str__(self):
        return f"{self.eleitor.nome} votou em {self.eleicao.titulo} (momento: {self.data_hora_registro})"


class Voto(models.Model):
    """
    ENTIDADE DO VOTO - Sabe APENAS:
    - A qual eleição pertence
    - Em qual candidato (ou se foi em branco)
    - Quando foi registrado
    - Hash do comprovante
    
    NÃO sabe quem o emitiu - NÃO possui qualquer FK para Eleitor!
    """
    eleicao = models.ForeignKey(Eleicao, on_delete=models.CASCADE, related_name='votos')
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE, related_name='votos', null=True, blank=True)
    voto_em_branco = models.BooleanField(default=False)
    hash_comprovante = models.CharField(max_length=64, unique=True, db_index=True)
    data_hora_voto = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['eleicao', 'data_hora_voto']),
        ]
        verbose_name = 'Voto'
        verbose_name_plural = 'Votos'
    
    def clean(self):
        if not self.voto_em_branco and not self.candidato:
            raise ValidationError('Voto deve ter candidato ou ser em branco')
        if self.voto_em_branco and self.candidato:
            raise ValidationError('Voto em branco não pode ter candidato associado')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.voto_em_branco:
            return f"Voto em branco - Eleição {self.eleicao.id} - {self.data_hora_voto}"
        return f"Voto em {self.candidato.nome} - Eleição {self.eleicao.id} - {self.data_hora_voto}"