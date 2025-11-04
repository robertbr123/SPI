from django.contrib import admin

from .models import Pescador, Endereco, Documento, Mensalidade, AssociacaoConfig, CaixaLancamento


class EnderecoInline(admin.StackedInline):
    model = Endereco
    can_delete = False
    extra = 0


class DocumentoInline(admin.TabularInline):
    model = Documento
    extra = 0


class MensalidadeInline(admin.TabularInline):
    model = Mensalidade
    extra = 0
    fields = ("competencia", "valor", "status", "data_pagamento")


@admin.register(Pescador)
class PescadorAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "rgp", "telefone", "data_associacao")
    search_fields = ("nome", "cpf", "rgp")
    inlines = [EnderecoInline, DocumentoInline, MensalidadeInline]


@admin.register(AssociacaoConfig)
class AssociacaoConfigAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "telefone", "email")


@admin.register(CaixaLancamento)
class CaixaLancamentoAdmin(admin.ModelAdmin):
    list_display = ("data", "tipo", "categoria", "valor")
    list_filter = ("tipo", "categoria")
    search_fields = ("descricao", "categoria")

