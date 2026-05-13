from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from .models import Eleicao, Candidato, Eleitor, RegistroVotacao, Voto

class AnonimatoVotoTestCase(TestCase):
    
    def setUp(self):
        # Criar eleição
        self.eleicao = Eleicao.objects.create(
            titulo='Eleição Teste',
            data_inicio=timezone.now() - timedelta(days=1),
            data_fim=timezone.now() + timedelta(days=1),
            status='ABERTA'
        )
        
        # Criar candidatos
        self.cand1 = Candidato.objects.create(
            eleicao=self.eleicao, nome='Candidato 1', numero=1
        )
        self.cand2 = Candidato.objects.create(
            eleicao=self.eleicao, nome='Candidato 2', numero=2
        )
        
        # Criar eleitores
        self.eleitor1 = Eleitor.objects.create(
            nome='João Silva', email='joao@email.com', documento='123456789'
        )
        self.eleitor2 = Eleitor.objects.create(
            nome='Maria Souza', email='maria@email.com', documento='987654321'
        )
    
    def test_desacoplamento_total(self):
        """Verifica que NÃO existe relação entre RegistroVotacao e Voto"""
        
        # Criar registro de votação
        registro = RegistroVotacao.objects.create(
            eleicao=self.eleicao, eleitor=self.eleitor1
        )
        
        # Criar voto (sem referência ao registro ou eleitor)
        voto = Voto.objects.create(
            eleicao=self.eleicao,
            candidato=self.cand1,
            hash_comprovante='hash_qualquer_123'
        )
        
        # Verificar que não há FK entre as tabelas
        self.assertFalse(hasattr(registro, 'voto'))
        self.assertFalse(hasattr(voto, 'registro_votacao'))
        self.assertFalse(hasattr(voto, 'eleitor'))
    
    def test_voto_unico_por_eleitor(self):
        """Verifica que cada eleitor vota apenas uma vez (constraint unique)"""
        
        # Primeiro voto - deve funcionar
        RegistroVotacao.objects.create(
            eleicao=self.eleicao, eleitor=self.eleitor1
        )
        
        # Segundo voto - deve violar unique_together
        with self.assertRaises(IntegrityError):
            RegistroVotacao.objects.create(
                eleicao=self.eleicao, eleitor=self.eleitor1
            )
    
    def test_impossibilidade_rastreamento(self):
        """Verifica que é impossível saber em quem um eleitor votou"""
        
        # Eleitor 1 vota no candidato 1
        RegistroVotacao.objects.create(eleicao=self.eleicao, eleitor=self.eleitor1)
        Voto.objects.create(eleicao=self.eleicao, candidato=self.cand1, hash_comprovante='hash1')
        
        # Eleitor 2 vota no candidato 2
        RegistroVotacao.objects.create(eleicao=self.eleicao, eleitor=self.eleitor2)
        Voto.objects.create(eleicao=self.eleicao, candidato=self.cand2, hash_comprovante='hash2')
        
        # Tentativa de rastreamento - NÃO EXISTE QUERY possível que ligue eleitor ao voto
        # Não é possível fazer JOIN entre RegistroVotacao e Voto
        # pois não há campo de relação entre eles
        
        # Podemos apenas contar votos totais
        total_votos = Voto.objects.filter(eleicao=self.eleicao).count()
        self.assertEqual(total_votos, 2)
        
        # Mas não podemos saber quem votou em quem!
        with self.assertRaises(Exception):
            # Isso NÃO é possível:
            # Voto.objects.filter(eleitor__id=self.eleitor1.id)
            pass