from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Eleicao, Candidato, Eleitor, RegistroVotacao, Voto
from .serializers import (
    VotoRequestSerializer,
    ResultadoEleicaoSerializer,
    EleicaoSerializer,
    CandidatoSerializer,
    EleitorSerializer
)
from .utils import gerar_token_comprovante, gerar_hash_token, gerar_qrcode_comprovante


class EleicaoViewSet(viewsets.ModelViewSet):
    queryset = Eleicao.objects.all()
    serializer_class = EleicaoSerializer
    permission_classes = [AllowAny]


class CandidatoViewSet(viewsets.ModelViewSet):
    queryset = Candidato.objects.all()
    serializer_class = CandidatoSerializer
    permission_classes = [AllowAny]


class EleitorViewSet(viewsets.ModelViewSet):
    queryset = Eleitor.objects.all()
    serializer_class = EleitorSerializer
    permission_classes = [AllowAny]


class VotarView(generics.CreateAPIView):
    """
    Endpoint de votação - Executa DUAS operações em uma transação:
    1. Cria RegistroVotacao (eleitor + eleicao) com constraint UNIQUE TOGETHER
    2. Cria Voto (apenas eleição + candidato + data/hora + hash)

    IMPORTANTE: As duas tabelas NÃO possuem qualquer relação entre si!
    """
    permission_classes = [AllowAny]
    serializer_class = VotoRequestSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dados = serializer.validated_data

        # Buscar objetos
        try:
            eleicao = Eleicao.objects.get(id=dados['eleicao_id'])
            eleitor = Eleitor.objects.get(id=dados['eleitor_id'])

            if not eleicao.pode_votar():
                return Response(
                    {'erro': 'Eleição não está aberta para votação'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            candidato = None
            if not dados.get('voto_em_branco', False):
                candidato = Candidato.objects.get(
                    id=dados['candidato_id'],
                    eleicao=eleicao
                )

        except Eleicao.DoesNotExist:
            return Response(
                {'erro': 'Eleição não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Eleitor.DoesNotExist:
            return Response(
                {'erro': 'Eleitor não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Candidato.DoesNotExist:
            return Response(
                {'erro': 'Candidato não encontrado nesta eleição'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            RegistroVotacao.objects.create(
                eleicao=eleicao,
                eleitor=eleitor
            )
        except Exception:
            return Response(
                {'erro': 'Eleitor já registrou voto nesta eleição'},
                status=status.HTTP_400_BAD_REQUEST
            )

        token = gerar_token_comprovante()
        hash_comprovante = gerar_hash_token(token)

        voto = Voto.objects.create(
            eleicao=eleicao,
            candidato=candidato,
            voto_em_branco=dados.get('voto_em_branco', False),
            hash_comprovante=hash_comprovante
        )

        dados_comprovante = {
            'data_hora': voto.data_hora_voto,
            'candidato_nome': 'VOTO EM BRANCO' if voto.voto_em_branco else candidato.nome,
            'eleicao_titulo': eleicao.titulo
        }

        qrcode_base64 = gerar_qrcode_comprovante(token, dados_comprovante)

        return Response({
            'mensagem': 'Voto registrado com sucesso!',
            'comprovante': {
                'token': token,
                'qrcode_base64': qrcode_base64,
                'data_voto': voto.data_hora_voto.isoformat(),
                'eleicao': eleicao.titulo,
                'candidato': dados_comprovante['candidato_nome']
            },
            'aviso': 'Guarde este comprovante! O token não é armazenado em nosso sistema.'
        }, status=status.HTTP_201_CREATED)


class ResultadoEleicaoView(generics.RetrieveAPIView):
    """
    Relatório público da eleição
    Exibe APENAS percentuais e totais - NUNCA dados individuais
    """
    permission_classes = [AllowAny]

    def get(self, request, eleicao_id):
        try:
            eleicao = Eleicao.objects.get(id=eleicao_id)
        except Eleicao.DoesNotExist:
            return Response(
                {'erro': 'Eleição não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

        if eleicao.status not in ['ENCERRADA', 'APURADA']:
            return Response(
                {'erro': 'Resultados disponíveis apenas após o encerramento da eleição'},
                status=status.HTTP_400_BAD_REQUEST
            )

        total_eleitores = eleicao.registros_votacao.count()
        total_votos = eleicao.votos.count()

        resultados = []
        for candidato in eleicao.candidatos.all():
            votos_candidato = candidato.votos.count()
            percentual = (votos_candidato / total_votos * 100) if total_votos > 0 else 0
            resultados.append({
                'candidato': candidato.nome,
                'numero': candidato.numero,
                'votos': votos_candidato,
                'percentual': round(percentual, 2)
            })

        votos_branco = eleicao.votos.filter(voto_em_branco=True).count()
        percentual_branco = (votos_branco / total_votos * 100) if total_votos > 0 else 0
        total_aptos = total_eleitores

        resultado_data = {
            'eleicao_id': eleicao.id,
            'eleicao_titulo': eleicao.titulo,
            'total_eleitores_aptos': total_aptos,
            'total_compareceram': total_eleitores,
            'total_votos_validos': total_votos,
            'abstencoes': total_aptos - total_eleitores,
            'percentual_comparecimento': round((total_eleitores / total_aptos * 100), 2) if total_aptos > 0 else 0,
            'percentual_abstencao': round(((total_aptos - total_eleitores) / total_aptos * 100), 2) if total_aptos > 0 else 0,
            'resultados_por_candidato': resultados,
            'voto_branco': {
                'quantidade': votos_branco,
                'percentual': round(percentual_branco, 2)
            }
        }

        serializer = ResultadoEleicaoSerializer(resultado_data)
        return Response(serializer.data)


class ComprovanteConsultaView(generics.RetrieveAPIView):
    """
    Consulta se um comprovante é válido
    O eleitor usa o token que recebeu no momento do voto
    """
    permission_classes = [AllowAny]

    def get(self, request, token):
        from .utils import gerar_hash_token

        hash_token = gerar_hash_token(token)

        try:
            voto = Voto.objects.get(hash_comprovante=hash_token)
            return Response({
                'valido': True,
                'data_voto': voto.data_hora_voto,
                'eleicao': voto.eleicao.titulo,
                'candidato': 'VOTO EM BRANCO' if voto.voto_em_branco else voto.candidato.nome,
                'mensagem': 'Comprovante válido - Este voto foi registrado em nosso sistema'
            })
        except Voto.DoesNotExist:
            return Response({
                'valido': False,
                'mensagem': 'Comprovante inválido - Nenhum voto encontrado com este token'
            }, status=status.HTTP_404_NOT_FOUND)