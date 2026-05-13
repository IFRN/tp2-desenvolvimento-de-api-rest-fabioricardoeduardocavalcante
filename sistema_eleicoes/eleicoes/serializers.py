from rest_framework import serializers
from django.utils import timezone
from .models import Eleicao, Candidato, Eleitor

class EleicaoSerializer(serializers.ModelSerializer):
    """
    Serializer para a entidade Eleicao
    """
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    criada_por_nome = serializers.CharField(source='criada_por.nome', read_only=True)
    periodo_formatado = serializers.CharField(source='periodo_votacao', read_only=True)
    esta_ativa = serializers.BooleanField(read_only=True)
    total_candidatos = serializers.SerializerMethodField()
    total_votos = serializers.SerializerMethodField()
    total_eleitores_aptos = serializers.SerializerMethodField()
    
    class Meta:
        model = Eleicao
        fields = [
            'id', 'titulo', 'descricao', 'tipo', 'tipo_display',
            'data_inicio', 'data_fim', 'status', 'status_display',
            'permite_branco', 'criada_por', 'criada_por_nome',
            'periodo_formatado', 'esta_ativa', 'total_candidatos',
            'total_votos', 'total_eleitores_aptos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_candidatos(self, obj):
        return obj.candidatos.count()
    
    def get_total_votos(self, obj):
        from .models import Voto
        return Voto.objects.filter(eleicao=obj).count()
    
    def get_total_eleitores_aptos(self, obj):
        from .models import RegistroVotacao
        return RegistroVotacao.objects.filter(eleicao=obj).count()
    
    def validate_data_inicio(self, value):
        """
        Validação da data de início
        """
        if value and value < timezone.now():
            # Permitir data passada apenas se status for rascunho
            if self.instance and self.instance.status != Eleicao.StatusEleicao.RASCUNHO:
                raise serializers.ValidationError(
                    'A data de início não pode ser no passado para eleições que não estão em rascunho.'
                )
        return value
    
    def validate_data_fim(self, value):
        """
        Validação da data de fim
        """
        data_inicio = self.initial_data.get('data_inicio') or (self.instance.data_inicio if self.instance else None)
        
        if data_inicio and value:
            # Converter para datetime se necessário
            if isinstance(data_inicio, str):
                from dateutil.parser import parse
                data_inicio = parse(data_inicio)
            
            if value <= data_inicio:
                raise serializers.ValidationError(
                    'A data e hora de término deve ser posterior à data e hora de início.'
                )
        
        return value
    
    def validate_status(self, value):
        """
        Validação do status
        """
        if self.instance:
            # Verificar transição permitida
            transicoes_permitidas = Eleicao.STATUS_TRANSITIONS.get(self.instance.status, [])
            if value not in transicoes_permitidas and value != self.instance.status:
                status_anterior = self.instance.get_status_display()
                status_novo = dict(Eleicao.StatusEleicao.choices).get(value)
                raise serializers.ValidationError(
                    f'Não é permitido alterar o status de "{status_anterior}" para "{status_novo}". '
                    f'Fluxo permitido: rascunho → aberta → encerrada → apurada (sem voltar).'
                )
        
        return value
    
    def validate(self, data):
        """
        Validações que envolvem múltiplos campos
        """
        # Validar número mínimo de candidatos se estiver abrindo
        if data.get('status') == Eleicao.StatusEleicao.ABERTA:
            if self.instance:
                total_candidatos = self.instance.candidatos.count()
            else:
                # Para nova eleição, verificar se candidatos foram enviados
                total_candidatos = len(self.initial_data.get('candidatos', []))
            
            if total_candidatos < 2:
                raise serializers.ValidationError({
                    'status': 'Não é possível abrir uma eleição com menos de 2 candidatos.'
                })
        
        # Validar datas
        data_inicio = data.get('data_inicio') or (self.instance.data_inicio if self.instance else None)
        data_fim = data.get('data_fim') or (self.instance.data_fim if self.instance else None)
        
        if data_inicio and data_fim and data_fim <= data_inicio:
            raise serializers.ValidationError({
                'data_fim': 'A data e hora de término deve ser posterior à data e hora de início.'
            })
        
        return data
    
    def create(self, validated_data):
        """
        Criação de eleição
        """
        # Garantir que criada_por está definido
        if 'criada_por' not in validated_data:
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                # Buscar eleitor associado ao usuário
                try:
                    eleitor = Eleitor.objects.get(email=request.user.email)
                    validated_data['criada_por'] = eleitor
                except Eleitor.DoesNotExist:
                    pass
        
        return super().create(validated_data)


class CandidatoSerializer(serializers.ModelSerializer):
    """
    Serializer para a entidade Candidato
    """
    eleicao_titulo = serializers.CharField(source='eleicao.titulo', read_only=True)
    total_votos = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidato
        fields = [
            'id', 'eleicao', 'eleicao_titulo', 'nome', 'numero', 
            'partido', 'foto_url', 'descricao', 'total_votos'
        ]
    
    def get_total_votos(self, obj):
        from .models import Voto
        return Voto.objects.filter(candidato=obj).count()


class EleitorSerializer(serializers.ModelSerializer):
    """
    Serializer para a entidade Eleitor
    """
    idade = serializers.IntegerField(read_only=True)
    cpf_formatado = serializers.CharField(source='cpf_formatado', read_only=True)
    pode_votar = serializers.BooleanField(read_only=True)
    total_votos = serializers.SerializerMethodField()
    
    class Meta:
        model = Eleitor
        fields = [
            'id', 'nome', 'email', 'cpf', 'cpf_formatado', 'data_nascimento',
            'idade', 'ativo', 'pode_votar', 'data_cadastro', 'total_votos'
        ]
        read_only_fields = ['data_cadastro', 'idade', 'cpf_formatado', 'pode_votar']
    
    def get_total_votos(self, obj):
        return obj.registros_votacao.count()