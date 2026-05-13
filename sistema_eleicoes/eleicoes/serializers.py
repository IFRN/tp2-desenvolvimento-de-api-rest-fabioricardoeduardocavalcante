from rest_framework import serializers
from .models import Eleicao, Candidato, Eleitor, RegistroVotacao, Voto

class VotoRequestSerializer(serializers.Serializer):
    """
    Serializer para requisição de voto
    """
    eleicao_id = serializers.IntegerField()
    eleitor_id = serializers.IntegerField()
    candidato_id = serializers.IntegerField(required=False, allow_null=True)
    voto_em_branco = serializers.BooleanField(default=False)
    
    def validate(self, data):
        # Validar: ou voto em branco OU candidato específico
        if not data.get('voto_em_branco') and not data.get('candidato_id'):
            raise serializers.ValidationError(
                'É necessário informar candidato_id ou marcar voto_em_branco=True'
            )
        
        if data.get('voto_em_branco') and data.get('candidato_id'):
            raise serializers.ValidationError(
                'Não é possível informar candidato_id quando voto_em_branco=True'
            )
        
        return data


class EleicaoSerializer(serializers.ModelSerializer):
    candidatos = serializers.SerializerMethodField()
    total_votos = serializers.SerializerMethodField()
    total_compareceram = serializers.SerializerMethodField()
    
    class Meta:
        model = Eleicao
        fields = ['id', 'titulo', 'descricao', 'data_inicio', 'data_fim', 
                  'status', 'candidatos', 'total_votos', 'total_compareceram']
    
    def get_candidatos(self, obj):
        from .serializers import CandidatoSerializer
        return CandidatoSerializer(obj.candidatos.all(), many=True).data
    
    def get_total_votos(self, obj):
        return obj.votos.count()
    
    def get_total_compareceram(self, obj):
        return obj.registros_votacao.count()


class CandidatoSerializer(serializers.ModelSerializer):
    total_votos = serializers.SerializerMethodField()
    percentual = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidato
        fields = ['id', 'nome', 'numero', 'partido', 'foto_url', 
                  'descricao', 'total_votos', 'percentual']
    
    def get_total_votos(self, obj):
        return obj.votos.count()
    
    def get_percentual(self, obj):
        total_votos_eleicao = obj.eleicao.votos.count()
        if total_votos_eleicao == 0:
            return 0
        return round((obj.votos.count() / total_votos_eleicao) * 100, 2)

class EleitorSerializer(serializers.ModelSerializer):
    """
    Serializer para a entidade Eleitor com validações adicionais
    """
    idade = serializers.IntegerField(read_only=True)
    cpf_formatado = serializers.CharField(read_only=True)
    pode_votar = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Eleitor
        fields = [
            'id', 'nome', 'email', 'cpf', 'cpf_formatado', 
            'data_nascimento', 'idade', 'ativo', 'pode_votar',
            'data_cadastro'
        ]
        read_only_fields = ['data_cadastro', 'idade', 'cpf_formatado', 'pode_votar']
    
    def validate_cpf(self, value):
        """
        Validação específica do CPF no serializer
        """
        # Limpar CPF
        cpf_limpo = re.sub(r'[^0-9]', '', value)
        
        if len(cpf_limpo) != 11:
            raise serializers.ValidationError('CPF deve conter 11 dígitos.')
        
        # Verificar CPF duplicado (já tratado pelo unique=True no modelo)
        if Eleitor.objects.filter(cpf__icontains=cpf_limpo).exists():
            # Se for update, ignorar o próprio registro
            if self.instance:
                if self.instance.cpf != self._formatar_cpf(cpf_limpo):
                    raise serializers.ValidationError('Este CPF já está cadastrado.')
            else:
                raise serializers.ValidationError('Este CPF já está cadastrado.')
        
        return self._formatar_cpf(cpf_limpo)
    
    def validate_email(self, value):
        """
        Validação adicional de email
        """
        # Verificar formato
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise serializers.ValidationError('Formato de e-mail inválido.')
        
        # Verificar unicidade (já tratado pelo unique=True)
        if Eleitor.objects.filter(email=value).exists():
            if self.instance and self.instance.email == value:
                return value
            raise serializers.ValidationError('Este e-mail já está cadastrado.')
        
        return value
    
    def validate_data_nascimento(self, value):
        """
        Validação de data de nascimento
        """
        from datetime import date
        from django.utils import timezone
        
        # Verificar se data não é futura
        if value > timezone.now().date():
            raise serializers.ValidationError('Data de nascimento não pode ser futura.')
        
        # Calcular idade
        hoje = timezone.now().date()
        idade = hoje.year - value.year
        if (hoje.month, hoje.day) < (value.month, value.day):
            idade -= 1
        
        # Verificar idade mínima (16 anos)
        if idade < 16:
            raise serializers.ValidationError(
                f'Eleitor deve ter no mínimo 16 anos. Idade atual: {idade} anos.'
            )
        
        # Verificar idade máxima (opcional, 120 anos)
        if idade > 120:
            raise serializers.ValidationError(
                f'Idade fora do limite permitido (máximo 120 anos). Idade informada: {idade} anos.'
            )
        
        return value
    
    def _formatar_cpf(self, cpf):
        """
        Formata CPF para o padrão 000.000.000-00
        """
        cpf_limpo = re.sub(r'[^0-9]', '', cpf)
        if len(cpf_limpo) == 11:
            return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
        return cpf
    
    def create(self, validated_data):
        """
        Criação de eleitor com validação extra
        """
        # Garantir que CPF está formatado
        if 'cpf' in validated_data:
            validated_data['cpf'] = self._formatar_cpf(validated_data['cpf'])
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """
        Atualização de eleitor
        """
        if 'cpf' in validated_data:
            validated_data['cpf'] = self._formatar_cpf(validated_data['cpf'])
        
        return super().update(instance, validated_data)


class RegistroVotacaoSerializer(serializers.ModelSerializer):
    eleitor_nome = serializers.CharField(source='eleitor.nome', read_only=True)
    eleicao_titulo = serializers.CharField(source='eleicao.titulo', read_only=True)
    
    class Meta:
        model = RegistroVotacao
        fields = ['id', 'eleicao', 'eleicao_titulo', 'eleitor', 
                  'eleitor_nome', 'data_hora_registro']


class ResultadoEleicaoSerializer(serializers.Serializer):
    """
    Relatório público - APENAS percentuais e totais
    NUNCA exibe dados individualizados
    """
    eleicao_id = serializers.IntegerField()
    eleicao_titulo = serializers.CharField()
    total_eleitores_aptos = serializers.IntegerField()
    total_compareceram = serializers.IntegerField()
    total_votos_validos = serializers.IntegerField()
    abstencoes = serializers.IntegerField()
    percentual_comparecimento = serializers.DecimalField(max_digits=5, decimal_places=2)
    percentual_abstencao = serializers.DecimalField(max_digits=5, decimal_places=2)
    resultados_por_candidato = serializers.ListField()
    voto_branco = serializers.DictField()