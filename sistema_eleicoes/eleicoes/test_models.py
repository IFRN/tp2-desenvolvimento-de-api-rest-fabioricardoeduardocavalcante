from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from eleicoes.models import Eleicao, Eleitor, Candidato

class EleicaoModelTest(TestCase):
    
    def setUp(self):
        """Configuração inicial dos testes"""
        # Criar eleitor administrador
        self.admin = Eleitor.objects.create(
            nome='Admin Teste',
            email='admin@teste.com',
            cpf='123.456.789-09',
            data_nascimento=timezone.now().date() - timedelta(days=30*365),
            ativo=True
        )
        
        # Dados base da eleição
        self.dados_eleicao = {
            'titulo': 'Eleição Teste',
            'descricao': 'Descrição da eleição teste',
            'tipo': Eleicao.TipoEleicao.ESTUDANTIL,
            'data_inicio': timezone.now() + timedelta(days=1),
            'data_fim': timezone.now() + timedelta(days=8),
            'status': Eleicao.StatusEleicao.RASCUNHO,
            'permite_branco': True,
            'criada_por': self.admin
        }
    
    def test_criar_eleicao_valida(self):
        """Testa criação de eleição com dados válidos"""
        eleicao = Eleicao.objects.create(**self.dados_eleicao)
        
        self.assertEqual(eleicao.titulo, 'Eleição Teste')
        self.assertEqual(eleicao.status, Eleicao.StatusEleicao.RASCUNHO)
        self.assertEqual(eleicao.criada_por, self.admin)
        self.assertIsNotNone(eleicao.created_at)
    
    def test_validar_data_fim_maior_que_data_inicio(self):
        """Testa validação de data_fim > data_inicio"""
        dados_invalidos = self.dados_eleicao.copy()
        dados_invalidos['data_fim'] = timezone.now() + timedelta(days=1)
        dados_invalidos['data_inicio'] = timezone.now() + timedelta(days=8)
        
        with self.assertRaises(ValidationError):
            eleicao = Eleicao(**dados_invalidos)
            eleicao.full_clean()
    
    def test_transicao_status_permitida(self):
        """Testa transição de status permitida"""
        eleicao = Eleicao.objects.create(**self.dados_eleicao)
        
        # Rascunho -> Aberta (válido)
        eleicao.status = Eleicao.StatusEleicao.ABERTA
        eleicao.save()  # Não deve lançar exceção
        
        # Aberta -> Encerrada (válido)
        eleicao.status = Eleicao.StatusEleicao.ENCERRADA
        eleicao.save()  # Não deve lançar exceção
        
        # Encerrada -> Apurada (válido)
        eleicao.status = Eleicao.StatusEleicao.APURADA
        eleicao.save()  # Não deve lançar exceção
    
    def test_transicao_status_invalida(self):
        """Testa transição de status inválida (voltar ou pular)"""
        eleicao = Eleicao.objects.create(**self.dados_eleicao)
        
        # Tentar pular de rascunho para encerrada (inválido)
        eleicao.status = Eleicao.StatusEleicao.ENCERRADA
        with self.assertRaises(ValidationError):
            eleicao.save()
        
        # Tentar voltar de aberta para rascunho (inválido)
        eleicao.status = Eleicao.StatusEleicao.ABERTA
        eleicao.save()
        
        eleicao.status = Eleicao.StatusEleicao.RASCUNHO
        with self.assertRaises(ValidationError):
            eleicao.save()
    
    def test_nao_abrir_sem_candidatos(self):
        """Testa que não pode abrir eleição sem pelo menos 2 candidatos"""
        eleicao = Eleicao.objects.create(**self.dados_eleicao)
        
        # Tentar abrir sem candidatos
        eleicao.status = Eleicao.StatusEleicao.ABERTA
        with self.assertRaises(ValidationError):
            eleicao.full_clean()
        
        # Adicionar candidatos
        Candidato.objects.create(
            eleicao=eleicao,
            nome='Candidato 1',
            numero=1
        )
        Candidato.objects.create(
            eleicao=eleicao,
            nome='Candidato 2',
            numero=2
        )
        
        # Agora deve funcionar
        eleicao.status = Eleicao.StatusEleicao.ABERTA
        eleicao.full_clean()  # Não deve lançar exceção
        eleicao.save()
    
    def test_propriedade_esta_ativa(self):
        """Testa propriedade esta_ativa"""
        # Eleição futura
        eleicao_futura = Eleicao.objects.create(**self.dados_eleicao)
        eleicao_futura.status = Eleicao.StatusEleicao.ABERTA
        eleicao_futura.save()
        self.assertFalse(eleicao_futura.esta_ativa)  # Ainda não começou
        
        # Eleição ativa
        eleicao_ativa = Eleicao.objects.create