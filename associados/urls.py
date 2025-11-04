from django.urls import path
from . import views

app_name = "associados"

urlpatterns = [
    path("", views.PescadorListView.as_view(), name="pescador_list"),
    path("pescador/novo/", views.PescadorCreateView.as_view(), name="pescador_create"),
    path("pescador/<int:pk>/editar/", views.PescadorUpdateView.as_view(), name="pescador_update"),
    path("pescador/<int:pk>/", views.PescadorDetailView.as_view(), name="pescador_detail"),
    path("pescador/<int:pk>/ficha/", views.PescadorFichaView.as_view(), name="pescador_ficha"),
    path("pescador/<int:pk>/dossie-defeso/", views.defeso_dossie_pdf, name="defeso_dossie_pdf"),

    path("pescador/<int:pk>/documento/novo/", views.DocumentoCreateView.as_view(), name="documento_create"),
    path("pescador/<int:pk>/mensalidade/adicionar/", views.mensalidade_adicionar, name="mensalidade_adicionar"),
    path("pescador/<int:pk>/mensalidade/gerar-ano/", views.mensalidades_gerar_ano, name="mensalidades_gerar_ano"),
    path("mensalidade/<int:pk>/pagar/", views.mensalidade_pagar, name="mensalidade_pagar"),
    path("mensalidade/<int:pk>/recibo/", views.recibo_pdf, name="recibo_pdf"),
    path("mensalidade/<int:pk>/excluir/", views.mensalidade_excluir, name="mensalidade_excluir"),

    path("associacao/", views.AssociacaoConfigUpdateView.as_view(), name="associacao_config"),
    path("relatorios/", views.RelatoriosView.as_view(), name="relatorios"),
    path("caixa/", views.CaixaView.as_view(), name="caixa"),
    path("caixa/<int:pk>/editar/", views.CaixaEditView.as_view(), name="caixa_editar"),
    path("caixa/<int:pk>/excluir/", views.caixa_excluir, name="caixa_excluir"),
]
