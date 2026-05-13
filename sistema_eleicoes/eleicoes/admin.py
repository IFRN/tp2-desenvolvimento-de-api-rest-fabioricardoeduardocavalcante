from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Eleicao, Candidato

class CandidatoInline(admin.TabularInline):
    """
    Inline para candidatos no admin de eleição
    """
    model = Candidato
    extra = 2
    fields = ['nome', 'numero', 'partido']
    show_change_link = True

@admin.register(Eleicao)
class EleicaoAdmin(admin.ModelAdmin):
    """
    Configuração do admin para o modelo Eleicao
    """
    list_display = [
        'titulo', 'tipo_tag', 'status_tag', 'periodo_formatado_admin',
        'criada_por_link', 'total_candidatos_admin', 'esta_ativa_admin'
    ]
    
    list_filter = [
        'status', 'tipo', 'permite_branco',
        ('data_inicio', admin.DateFieldListFilter),
        ('data_fim', admin.DateFieldListFilter)
    ]
    
    search_fields = ['titulo', 'descricao', 'criada_por__nome', 'criada_por__email']
    
    readonly_fields = [
        'created_at', 'updated_at', 'status_history_admin'
    ]
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('titulo', 'descricao', 'tipo', 'permite_branco')
        }),
        ('Período de Votação', {
            'fields': ('data_inicio', 'data_fim'),
            'classes': ('wide',)
        }),
        ('Status e Controle', {
            'fields': ('status', 'criada_por', 'status_history_admin'),
            'classes': ('wide',)
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CandidatoInline]
    
    actions = ['abrir_eleicoes', 'encerrar_eleicoes', 'apurar_eleicoes']
    
    def tipo_tag(self, obj):
        """Exibe tipo com badge colorido"""
        cores = {
            'estudantil': 'blue',
            'sindical': 'green',
            'associacao': 'orange',
            'condominio': 'purple',
            'conselho': 'red',
            'outra': 'gray'
        }
        cor = cores.get(obj.tipo, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
            cor, obj.get_tipo_display()
        )
    tipo_tag.short_description = 'Tipo'
    
    def status_tag(self, obj):
        """Exibe status com badge colorido"""
        cores = {
            'rascunho': 'gray',
            'aberta': 'green',
            'encerrada': 'orange',
            'apurada': 'blue'
        }
        cor = cores.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
            cor, obj.get_status_display()
        )
    status_tag.short_description = 'Status'
    
    def periodo_formatado_admin(self, obj):
        """Exibe período formatado"""
        return obj.periodo_votacao
    periodo_formatado_admin.short_description = 'Período'
    
    def criada_por_link(self, obj):
        """Link para o eleitor que criou"""
        if obj.criada_por:
            url = reverse('admin:eleicoes_eleitor_change', args=[obj.criada_por.id])
            return format_html('<a href="{}">{}</a>', url, obj.criada_por.nome)
        return '-'
    criada_por_link.short_description = 'Criada por'
    
    def total_candidatos_admin(self, obj):
        """Total de candidatos"""
        count = obj.candidatos.count()
        url = reverse('admin:eleicoes_candidato_changelist')
        url += f'?eleicao__id__exact={obj.id}'
        return format_html('<a href="{}">{} candidato(s)</a>', url, count)
    total_candidatos_admin.short_description = 'Candidatos'
    
    def esta_ativa_admin(self, obj):
        """Indica se está ativa"""
        if obj.esta_ativa:
            return format_html('<span style="color: green;">✓ Ativa</span>')
        return format_html('<span style="color: red;">✗ Inativa</span>')
    esta_ativa_admin.short_description = 'Ativa?'
    
    def status_history_admin(self, obj):
        """Histórico de status (simulado)"""
        return format_html(
            '<div style="font-family: monospace;">'
            '<strong>Fluxo permitido:</strong> rascunho → aberta → encerrada → apurada<br>'
            '<strong>Status atual:</strong> {}<br>'
            '<strong>Não é possível retroceder!</strong>'
            '</div>',
            obj.get_status_display()
        )
    status_history_admin.short_description = 'Histórico de Status'
    
    def abrir_eleicoes(self, request, queryset):
        """Abre as eleições selecionadas"""
        abertas = 0
        erros = 0
        
        for eleicao in queryset:
            if eleicao.abrir():
                abertas += 1
            else:
                erros += 1
        
        self.message_user(
            request,
            f"{abertas} eleição(ões) aberta(s) com sucesso. {erros} falha(s)."
        )
    abrir_eleicoes.short_description = "Abrir eleições selecionadas"
    
    def encerrar_eleicoes(self, request, queryset):
        """Encerra as eleições selecionadas"""
        encerradas = 0
        erros = 0
        
        for eleicao in queryset:
            if eleicao.encerrar():
                encerradas += 1
            else:
                erros += 1
        
        self.message_user(
            request,
            f"{encerradas} eleição(ões) encerrada(s) com sucesso. {erros} falha(s)."
        )
    encerrar_eleicoes.short_description = "Encerrar eleições selecionadas"
    
    def apurar_eleicoes(self, request, queryset):
        """Apura as eleições selecionadas"""
        apuradas = 0
        erros = 0
        
        for eleicao in queryset:
            if eleicao.apurar():
                apuradas += 1
            else:
                erros += 1
        
        self.message_user(
            request,
            f"{apuradas} eleição(ões) apurada(s) com sucesso. {erros} falha(s)."
        )
    apurar_eleicoes.short_description = "Apurar eleições selecionadas"
    
    def save_model(self, request, obj, form, change):
        """Define criada_por automaticamente na criação"""
        if not change and not obj.criada_por:
            # Buscar eleitor associado ao usuário admin
            try:
                from .models import Eleitor
                eleitor = Eleitor.objects.get(email=request.user.email)
                obj.criada_por = eleitor
            except Eleitor.DoesNotExist:
                pass
        
        super().save_model(request, obj, form, change)