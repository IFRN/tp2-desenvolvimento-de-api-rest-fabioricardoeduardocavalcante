from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re
from datetime import date
from django.utils import timezone

def validar_cpf(valor):
    """
    Validador de CPF para uso em modelos Django
    """
    # Limpar CPF
    cpf = re.sub(r'[^0-9]', '', valor)
    
    # Verificar tamanho
    if len(cpf) != 11:
        raise ValidationError(
            _('CPF deve conter 11 dígitos.'),
            code='invalid_length'
        )
    
    # Verificar dígitos repetidos
    if cpf == cpf[0] * 11:
        raise ValidationError(
            _('CPF inválido.'),
            code='invalid_cpf'
        )
    
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
    if digito1 != int(cpf[9]) or digito2 != int(cpf[10]):
        raise ValidationError(
            _('CPF inválido. Dígitos verificadores não conferem.'),
            code='invalid_cpf'
        )
    
    # Formatar CPF
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def validar_idade_minima(data_nascimento, idade_minima=16):
    """
    Validador de idade mínima
    """
    hoje = timezone.now().date()
    idade = hoje.year - data_nascimento.year
    
    if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
        idade -= 1
    
    if idade < idade_minima:
        raise ValidationError(
            _(f'Eleitor deve ter no mínimo {idade_minima} anos. Idade atual: {idade} anos.'),
            code='min_age'
        )
    
    return data_nascimento