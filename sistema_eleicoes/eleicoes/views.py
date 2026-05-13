from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.views import APIView
from django.utils import timezone
from .models import Eleicao, Candidato, Eleitor
from .serializers import EleicaoSerializer, CandidatoSerializer, EleitorSerializer

class EleicaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de eleições
    """
    queryset = Eleicao.objects.all()
    serializer_class = EleicaoSerializer
    
    def get_queryset(self):
        """
        Filtragem por tipo e status
        """
        queryset = super().get_queryset()
        
        # Filtrar por tipo
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        # Filtrar por status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filtrar por ativas (abertas e dentro do período)
        ativas = self.request.query_params.get('ativas')
        if ativas and ativas.lower() == 'true':
            agora = timezone.now()
            queryset = queryset.filter(
                status=Eleicao.StatusEleicao.ABERTA,
                data_inicio__lte=agora,
                data_fim__gte=agora
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def abrir(self, request, pk=None):
        """
        Endpoint para abrir uma eleição
        """
        eleicao = self.get_object()
        
        if eleicao.abrir():
            serializer = self.get_serializer(eleicao)
            return Response({
                'mensagem': 'Eleição aberta com sucesso!',
                'eleicao': serializer.data
            })
        else:
            return Response({
                'erro': 'Não foi possível abrir a eleição.',
                'motivo': 'Verifique se a eleição está em rascunho e possui pelo menos 2 candidatos.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def encerrar(self, request, pk=None):
        """
        Endpoint para encerrar uma eleição
        """
        eleicao = self.get_object()
        
        # Encerramento antecipado (opcional com justificativa)
        justificativa = request.data.get('justificativa', '')
        
        if eleicao.encerrar():
            serializer = self.get_serializer(eleicao)
            return Response({
                'mensagem': 'Eleição encerrada com sucesso!',
                'encerramento_antecipado': eleicao.data_fim > timezone.now(),
                'justificativa': justificativa if justificativa else None,
                'eleicao': serializer.data
            })
        else:
            return Response({
                'erro': 'Não foi possível encerrar a eleição.',
                'motivo': 'Apenas eleições abertas podem ser encerradas.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def apurar(self, request, pk=None):
        """
        Endpoint para apurar uma eleição
        """
        eleicao = self.get_object()
        
        if eleicao.apurar():
            serializer = self.get_serializer(eleicao)
            return Response({
                'mensagem': 'Eleição apurada com sucesso!',
                'eleicao': serializer.data
            })
        else:
            return Response({
                'erro': 'Não foi possível apurar a eleição.',
                'motivo': 'Apenas eleições encerradas podem ser apuradas.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def fluxo_status(self, request, pk=None):
        """
        Retorna o fluxo de status permitido para a eleição
        """
        eleicao = self.get_object()
        
        transicoes = []
        for status_anterior, status_permitidos in Eleicao.STATUS_TRANSITIONS.items():
            transicoes.append({
                'de': status_anterior,
                'de_display': dict(Eleicao.StatusEleicao.choices).get(status_anterior),
                'para': [{'valor': s, 'display': dict(Eleicao.StatusEleicao.choices).get(s)} for s in status_permitidos]
            })
        
        return Response({
            'status_atual': eleicao.status,
            'status_atual_display': eleicao.get_status_display(),
            'transicoes_permitidas': transicoes,
            'pode_abrir': eleicao.pode_ser_aberta,
            'pode_encerrar': eleicao.pode_ser_encerrada,
            'pode_apurar': eleicao.pode_ser_apurada
        })


class CandidatoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de candidatos
    """
    queryset = Candidato.objects.all()
    serializer_class = CandidatoSerializer
    
    def get_queryset(self):
        """
        Filtragem por eleição
        """
        queryset = super().get_queryset()
        
        eleicao_id = self.request.query_params.get('eleicao')
        if eleicao_id:
            queryset = queryset.filter(eleicao_id=eleicao_id)
        
        return queryset


class EleitorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de eleitores
    """
    queryset = Eleitor.objects.all()
    serializer_class = EleitorSerializer
    
    def get_queryset(self):
        """
        Filtragem por status ativo
        """
        queryset = super().get_queryset()
        
        ativo = self.request.query_params.get('ativo')
        if ativo is not None:
            ativo_bool = ativo.lower() == 'true'
            queryset = queryset.filter(ativo=ativo_bool)
        
        return queryset


class VotarView(APIView):
    """
    Endpoint para votação
    """
    def post(self, request):
        # Implementar lógica de votação
        return Response({'message': 'Voto registrado'}, status=status.HTTP_201_CREATED)


class ComprovanteConsultaView(APIView):
    """
    Endpoint para consulta de comprovante
    """
    def get(self, request, token):
        # Implementar lógica de consulta de comprovante
        return Response({'valido': True, 'message': 'Comprovante válido'})


class ResultadoEleicaoView(APIView):
    """
    Endpoint para resultados da eleição
    """
    def get(self, request, eleicao_id):
        # Implementar lógica de resultados
        return Response({'eleicao_id': eleicao_id, 'resultados': []})