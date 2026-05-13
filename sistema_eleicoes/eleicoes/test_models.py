from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from eleicoes.models import Eleitor

class EleitorModelTest(TestCase):
    
    def setUp(self):
        """Configuração inicial dos testes"""
        self.dados_eleitor = {
            'nome': 'João Silva Santos',
            'email': 'joao.silva@email.com',
            'cpf': '123.456.789-09',
            'data_nascimento': timezone.now().date() - timedelta(days=18*365),  # 18 anos
            'ativo': True
        }
    
    def test_criar_eleitor_valido(self):
        """Testa criação de eleitor com dados válidos"""
        eleitor = Eleitor.objects.create(**self.dados_eleitor)
        
        self.assertEqual(eleitor.nome, 'João Silva Santos')
        self.assertEqual(eleitor.email, 'joao.silva@email.com')
        self.assertEqual(eleitor.cpf, '123.456.789-09')
        self.assertEqual(eleitor.ativo, True)
        self.assertIsNotNone(eleitor.data_cadastro)
        self.assertTrue(eleitor.pode_votar)
        self.assertGreaterEqual(eleitor.idade, 16)
    
    def test_cpf_unique(self):
        """Testa que CPF deve ser único"""
        Eleitor.objects.create(**self.dados_eleitor)
        
        # Tentar criar outro eleitor com mesmo CPF
        with self.assertRaises(Exception):
            Eleitor.objects.create(
                nome='Outro Nome',
                email='outro@email.com',
                cpf='123.456.789-09',  # Mesmo CPF
                data_nascimento=timezone.now().date() - timedelta(days=20*365)
            )
    
    def test_email_unique(self):
        """Testa que email deve ser único"""
        Eleitor.objects.create(**self.dados_eleitor)
        
        # Tentar criar outro eleitor com mesmo email
        with self.assertRaises(Exception):
            Eleitor.objects.create(
                nome='Outro Nome',
                email='joao.silva@email.com',  # Mesmo email
                cpf='987.654.321-00',
                data_nascimento=timezone.now().date() - timedelta(days=20*365)
            )
    
    def test_cpf_invalido(self):
        """Testa validação de CPF inválido"""
        dados_invalidos = self.dados_eleitor.copy()
        dados_invalidos['cpf'] = '111.111.111-11'  # CPF inválido (dígitos repetidos)
        
        with self.assertRaises(ValidationError):
            eleitor = Eleitor(**dados_invalidos)
            eleitor.full_clean()
    
    def test_cpf_sem_formatacao(self):
        """Testa CPF sem formatação (apenas números)"""
        eleitor = Eleitor(
            nome='Maria Souza',
            email='maria@email.com',
            cpf='12345678909',  # Sem formatação
            data_nascimento=timezone.now().date() - timedelta(days=20*365)
        )
        eleitor.full_clean()
        eleitor.save()
        
        # Verificar que foi formatado automaticamente
        self.assertEqual(eleitor.cpf, '123.456.789-09')
    
    def test_idade_minima(self):
        """Testa validação de idade mínima (16 anos)"""
        # Eleitor com 15 anos
        dados_menor = self.dados_eleitor.copy()
        dados_menor['data_nascimento'] = timezone.now().date() - timedelta(days=15*365)
        
        with self.assertRaises(ValidationError):
            eleitor = Eleitor(**dados_menor)
            eleitor.full_clean()
    
    def test_data_nascimento_futura(self):
        """Testa que data de nascimento não pode ser futura"""
        dados_futuro = self.dados_eleitor.copy()
        dados_futuro['data_nascimento'] = timezone.now().date() + timedelta(days=365)
        
        with self.assertRaises(ValidationError):
            eleitor = Eleitor(**dados_futuro)
            eleitor.full_clean()
    
    def test_propriedade_idade(self):
        """Testa propriedade de idade"""
        eleitor = Eleitor.objects.create(**self.dados_eleitor)
        self.assertIsNotNone(eleitor.idade)
        self.assertGreaterEqual(eleitor.idade, 16)
    
    def test_propriedade_pode_votar(self):
        """Testa propriedade pode_votar"""
        # Eleitor ativo e maior de 16
        eleitor1 = Eleitor.objects.create(**self.dados_eleitor)
        self.assertTrue(eleitor1.pode_votar)
        
        # Eleitor inativo
        eleitor2 = Eleitor.objects.create(
            nome='Inativo',
            email='inativo@email.com',
            cpf='987.654.321-00',
            data_nascimento=timezone.now().date() - timedelta(days=20*365),
            ativo=False
        )
        self.assertFalse(eleitor2.pode_votar)
        
        # Eleitor menor de 16 anos
        eleitor3 = Eleitor.objects.create(
            nome='Menor',
            email='menor@email.com',
            cpf='456.789.123-00',
            data_nascimento=timezone.now().date() - timedelta(days=15*365),
            ativo=True
        )
        self.assertFalse(eleitor3.pode_votar)