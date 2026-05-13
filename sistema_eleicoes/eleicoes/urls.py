from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'eleicoes', views.EleicaoViewSet)
router.register(r'candidatos', views.CandidatoViewSet)
router.register(r'eleitores', views.EleitorViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # Endpoint crítico de votação - realiza as 2 operações
    path('votar/', views.VotarView.as_view(), name='votar'),
    
    # Consulta de comprovante (usando token original)
    path('comprovante/<str:token>/', views.ComprovanteConsultaView.as_view(), name='comprovante'),
    
    # Resultados públicos (apenas agregados)
    path('resultados/<int:eleicao_id>/', views.ResultadoEleicaoView.as_view(), name='resultados'),
]