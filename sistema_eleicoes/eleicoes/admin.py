from django.contrib import admin
from django.utils.html import format_html
from .models import Eleitor

@admin.register(Eleitor)
class EleitorAdmin(admin.ModelAdmin):
    """
    Configuração do admin para o modelo Eleitor
    """
    list_display = ['nome', 'cpf_formatado_admin', 'email', 'idade_admin', 'ativo', 'pode_votar_admin', 'data_cadastro']
    list_filter = ['ativo', 'data_cadastro', 'data_nascimento']
    search_fields = ['nome', 'cpf', 'email']
    readonly_fields = ['data_cadastro', 'cpf_formatado_admin', 'idade_admin']
    
    fieldsets = (
        ('Dados Pessoais', {
            'fields': ('nome', 'email', 'cpf', 'data_nascimento')
        }),
        ('Situação', {
            'fields': ('ativo',),
            'classes': ('wide',)
        }),
        ('Metadados', {
            'fields': ('data_cadastro',),
            'classes': ('collapse',)
        }),
    )
    
    def cpf_formatado_admin(self, obj):
        """Exibe CPF formatado no admin"""
        return obj.cpf_formatado
    cpf_formatado_admin.short_description = 'CPF'
    
    def idade_admin(self, obj):
        """Exibe idade no admin"""
        return f"{obj.idade} anos" if obj.idade else "N/A"
    idade_admin.short_description = 'Idade'
    
    def pode_votar_admin(self, obj):
        """Indica se pode votar"""
        if obj.pode_votar:
            return format_html('<span style="color: green;">✓ Sim</span>')
        return format_html('<span style="color: red;">✗ Não</span>')
    pode_votar_admin.short_description = 'Pode Votar'
    
    actions = ['ativar_eleitores', 'desativar_eleitores']
    
    def ativar_eleitores(self, request, queryset):
        """Ativa eleitores selecionados"""
        queryset.update(ativo=True)
        self.message_user(request, f"{queryset.count()} eleitores ativados com sucesso.")
    ativar_eleitores.short_description = "Ativar eleitores selecionados"
    
    def desativar_eleitores(self, request, queryset):
        """Desativa eleitores selecionados"""
        queryset.update(ativo=False)
        self.message_user(request, f"{queryset.count()} eleitores desativados com sucesso.")
    desativar_eleitores.short_description = "Desativar eleitores selecionados"