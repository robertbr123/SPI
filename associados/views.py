from datetime import date
import secrets
from io import BytesIO

from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from django.db import models
from django.db.models import Q
import qrcode

from .forms import (
    PescadorForm,
    EnderecoForm,
    DocumentoForm,
    MensalidadePagarForm,
    AssociacaoConfigForm,
    CaixaLancamentoForm,
)
from .models import Pescador, Endereco, Documento, Mensalidade, AssociacaoConfig, CaixaLancamento


class PescadorListView(ListView):
    model = Pescador
    template_name = "associados/pescador_list.html"
    context_object_name = "pescadores"

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(cpf__icontains=q) | Q(rgp__icontains=q))
        return qs


class PescadorCreateView(CreateView):
    model = Pescador
    form_class = PescadorForm
    template_name = "associados/pescador_form.html"

    def get_success_url(self):
        messages.success(self.request, "Pescador criado com sucesso.")
        return reverse("associados:pescador_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["endereco_form"] = EnderecoForm(self.request.POST or None)
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        endereco_form = EnderecoForm(self.request.POST)
        if endereco_form.is_valid():
            endereco = endereco_form.save(commit=False)
            endereco.pescador = self.object
            endereco.save()
        return response


class PescadorUpdateView(UpdateView):
    model = Pescador
    form_class = PescadorForm
    template_name = "associados/pescador_form.html"

    def get_success_url(self):
        messages.success(self.request, "Pescador atualizado com sucesso.")
        return reverse("associados:pescador_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        endereco = getattr(self.object, "endereco", None)
        ctx["endereco_form"] = EnderecoForm(self.request.POST or None, instance=endereco)
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        endereco_form = EnderecoForm(self.request.POST, instance=getattr(self.object, "endereco", None))
        if endereco_form.is_valid():
            endereco = endereco_form.save(commit=False)
            endereco.pescador = self.object
            endereco.save()
        return response


class PescadorDetailView(DetailView):
    model = Pescador
    template_name = "associados/pescador_detail.html"
    context_object_name = "pescador"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["documento_form"] = DocumentoForm()
        # Alerta Defeso: verificar 12 competências pagas no ano corrente
        ano_atual = date.today().year
        pagos_ano = self.object.mensalidades.filter(
            competencia__year=ano_atual, status="pago"
        ).count()
        ctx["defeso_ano"] = ano_atual
        ctx["defeso_total_pagas"] = pagos_ano
        ctx["defeso_pode"] = pagos_ano >= 12
        return ctx


class DocumentoCreateView(CreateView):
    model = Documento
    form_class = DocumentoForm
    template_name = "associados/documento_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.pescador = get_object_or_404(Pescador, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        doc = form.save(commit=False)
        doc.pescador = self.pescador
        doc.save()
        messages.success(self.request, "Documento enviado com sucesso.")
        return redirect("associados:pescador_detail", pk=self.pescador.pk)


def mensalidade_pagar(request, pk):
    mensalidade = get_object_or_404(Mensalidade, pk=pk)
    if request.method == "POST":
        form = MensalidadePagarForm(request.POST, instance=mensalidade)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.status = "pago"
            if not obj.data_pagamento:
                obj.data_pagamento = date.today()
            # Gerar número sequencial de recibo e token, se não existir
            if not obj.recibo_numero:
                last = Mensalidade.objects.exclude(recibo_numero__isnull=True).order_by('-recibo_numero').first()
                obj.recibo_numero = (last.recibo_numero + 1) if last and last.recibo_numero else 1
            if not obj.recibo_token:
                obj.recibo_token = secrets.token_hex(8)
            obj.save()
            # Lançar automaticamente receita no Caixa
            try:
                comp = obj.competencia.strftime('%m/%Y')
                descricao = f"Mensalidade {comp} - {obj.pescador.nome}"
                CaixaLancamento.objects.get_or_create(
                    tipo='receita',
                    categoria='Mensalidade',
                    descricao=descricao,
                    valor=obj.valor,
                    data=obj.data_pagamento,
                )
            except Exception:
                pass
            messages.success(request, "Pagamento registrado. Recibo disponível.")
            return redirect("associados:pescador_detail", pk=mensalidade.pescador.pk)
    else:
        form = MensalidadePagarForm(instance=mensalidade)
    return render(request, "associados/mensalidade_pagar.html", {"form": form, "mensalidade": mensalidade})


def mensalidade_adicionar(request, pk):
    pescador = get_object_or_404(Pescador, pk=pk)
    if request.method == "POST":
        comp_str = (request.POST.get("competencia") or "").strip()
        # Aceita formatos: AAAA-MM (input type=month), AAAA/MM, MM/AAAA, MM-AAAA
        competencia = None
        for sep in ("-", "/"):
            if sep in comp_str:
                parts = comp_str.split(sep)
                if len(parts) == 2:
                    a, b = parts
                    a, b = a.strip(), b.strip()
                    # Detectar se começa com ano (4 dígitos)
                    if len(a) == 4 and a.isdigit() and b.isdigit():
                        ano, mes = int(a), int(b)
                    elif len(b) == 4 and a.isdigit() and b.isdigit():
                        ano, mes = int(b), int(a)
                    else:
                        continue
                    try:
                        competencia = date(ano, mes, 1)
                    except Exception:
                        competencia = None
                break
        if not competencia:
            messages.error(request, "Competência inválida.")
            return redirect("associados:pescador_detail", pk=pescador.pk)

        obj, created = Mensalidade.objects.get_or_create(
            pescador=pescador,
            competencia=competencia,
            defaults={"valor": AssociacaoConfig.get_solo().valor_mensalidade_padrao},
        )
        if created:
            messages.success(request, "Mensalidade adicionada.")
        else:
            messages.info(request, "Mensalidade já existia para esta competência.")
    return redirect("associados:pescador_detail", pk=pescador.pk)


def recibo_pdf(request, pk):
    mensalidade = get_object_or_404(Mensalidade, pk=pk)
    if mensalidade.status != "pago":
        raise Http404("Mensalidade não está paga")

    config = AssociacaoConfig.get_solo()
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"inline; filename=recibo_{mensalidade.id}.pdf"

    def brl(value):
        try:
            v = float(value)
        except Exception:
            return f"R$ {value}"
        s = f"{v:,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Área principal (caixa centralizada)
    box_w = 500
    box_h = 460
    box_x = (width - box_w) / 2
    box_y = height - 80 - box_h
    p.setLineWidth(1)
    p.roundRect(box_x, box_y, box_w, box_h, 8)

    # Cabeçalho da associação (centralizado)
    head_y = box_y + box_h - 30
    if config.logo:
        try:
            img = ImageReader(config.logo.path)
            img_w, img_h = img.getSize()
            max_w, max_h = 90, 50
            ratio = min(max_w / img_w, max_h / img_h)
            dw, dh = img_w * ratio, img_h * ratio
            p.drawImage(img, box_x + box_w - dw - 16, head_y - dh + 10, dw, dh, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    p.setFont("Helvetica-Bold", 14)
    assoc = (config.nome or "Associação").upper()
    tw = p.stringWidth(assoc, "Helvetica-Bold", 14)
    p.drawString(box_x + (box_w - tw) / 2, head_y, assoc)
    p.setFont("Helvetica", 9)
    info1 = f"CNPJ: {config.cnpj or '-'}  |  Tel: {config.telefone or '-'}  |  Email: {config.email or '-'}"
    tw1 = p.stringWidth(info1, "Helvetica", 9)
    p.drawString(box_x + (box_w - tw1) / 2, head_y - 14, info1)
    info2 = f"End.: {config.endereco or '-'} - {config.cidade or ''}/{config.estado or ''} {config.cep or ''}"
    tw2 = p.stringWidth(info2, "Helvetica", 9)
    p.drawString(box_x + (box_w - tw2) / 2, head_y - 28, info2)

    # Título do recibo
    p.setFont("Helvetica-Bold", 16)
    num_txt = f" Nº {mensalidade.recibo_numero}" if mensalidade.recibo_numero else ""
    title = f"RECIBO DE PAGAMENTO{num_txt}"
    twt = p.stringWidth(title, "Helvetica-Bold", 16)
    p.drawString(box_x + (box_w - twt) / 2, head_y - 56, title)

    # Conteúdo (labels e valores)
    left = box_x + 24
    right = box_x + box_w - 24
    y = head_y - 86
    label_font = ("Helvetica-Bold", 11)
    value_font = ("Helvetica", 11)

    def draw_row(label, value):
        nonlocal y
        p.setFont(*label_font)
        p.drawString(left, y, label)
        p.setFont(*value_font)
        p.drawString(left + 150, y, value)
        y -= 20

    comp = mensalidade.competencia.strftime("%m/%Y")
    draw_row("Recebemos de:", f"{mensalidade.pescador.nome}")
    draw_row("CPF:", f"{mensalidade.pescador.cpf}")
    draw_row("RGP:", f"{mensalidade.pescador.rgp}")
    draw_row("Competência:", comp)
    draw_row("Valor:", brl(mensalidade.valor))
    draw_row("Data do pagamento:", mensalidade.data_pagamento.strftime('%d/%m/%Y'))
    if mensalidade.forma_pagamento:
        draw_row("Forma de pagamento:", mensalidade.forma_pagamento)
    if mensalidade.observacao:
        draw_row("Observações:", mensalidade.observacao)

    # QR Code (canto inferior direito da caixa)
    verify_url = request.build_absolute_uri(reverse('associados:recibo_pdf', args=[mensalidade.pk]))
    if mensalidade.recibo_token:
        verify_url += ("&" if "?" in verify_url else "?") + f"t={mensalidade.recibo_token}"
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(verify_url)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO(); img_qr.save(buf, format='PNG'); buf.seek(0)
    p.drawImage(ImageReader(buf), right - 80, box_y + 24, 64, 64, mask='auto')

    # Assinatura (centralizada)
    sig_y = box_y + 120
    line_w = 220
    cx = box_x + box_w / 2
    p.line(cx - line_w / 2, sig_y, cx + line_w / 2, sig_y)
    p.setFont("Helvetica", 10)
    assinatura = "Assinatura do responsável"
    if config.presidente:
        assinatura = f"{config.presidente} - Presidente"
    tws = p.stringWidth(assinatura, "Helvetica", 10)
    p.drawString(cx - tws / 2, sig_y - 12, assinatura)
    if config.assinatura_presidente:
        try:
            img_ass = ImageReader(config.assinatura_presidente.path)
            p.drawImage(img_ass, cx - 60, sig_y + 6, 120, 36, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Linha de autenticidade e data (centralizadas)
    p.setFont("Helvetica", 9)
    auth = f"Recibo Nº {mensalidade.recibo_numero or '-'} • Token {mensalidade.recibo_token or '-'}"
    twa = p.stringWidth(auth, "Helvetica", 9)
    p.drawString(cx - twa / 2, box_y + 96, auth)
    emit = f"Emitido em {date.today().strftime('%d/%m/%Y')}"
    twe = p.stringWidth(emit, "Helvetica", 9)
    p.drawString(cx - twe / 2, box_y + 82, emit)

    p.showPage()
    p.save()
    return response


class PescadorFichaView(DetailView):
    model = Pescador
    template_name = "associados/pescador_ficha.html"
    context_object_name = "pescador"


def mensalidades_gerar_ano(request, pk):
    pescador = get_object_or_404(Pescador, pk=pk)
    if request.method == "POST":
        ano_str = (request.POST.get("ano") or "").strip()
        try:
            ano = int(ano_str)
            assert 1900 <= ano <= 2100
        except Exception:
            messages.error(request, "Ano inválido.")
            return redirect("associados:pescador_detail", pk=pescador.pk)
        cfg = AssociacaoConfig.get_solo()
        criadas = 0
        for mes in range(1, 13):
            comp = date(ano, mes, 1)
            _, created = Mensalidade.objects.get_or_create(
                pescador=pescador,
                competencia=comp,
                defaults={"valor": cfg.valor_mensalidade_padrao},
            )
            if created:
                criadas += 1
        if criadas:
            messages.success(request, f"{criadas} competências geradas para {ano}.")
        else:
            messages.info(request, f"Todas as competências de {ano} já existiam.")
    return redirect("associados:pescador_detail", pk=pescador.pk)


class RelatoriosView(View):
    template_name = "relatorios/index.html"

    def get(self, request):
        # Filtros por mês/ano
        mes = request.GET.get("mes")
        ano = request.GET.get("ano")
        m_qs = Mensalidade.objects.all()
        try:
            if ano:
                m_qs = m_qs.filter(competencia__year=int(ano))
            if mes:
                m_qs = m_qs.filter(competencia__month=int(mes))
        except Exception:
            pass

        total_associados = Pescador.objects.count()
        m_pagas_qs = m_qs.filter(status="pago")
        total_mensalidades_pagas = m_pagas_qs.count()
        total_mensalidades_pendentes = m_qs.filter(status="pendente").count()
        # Total recebido (R$) pela soma dos valores pagos no período
        total_recebido = m_pagas_qs.aggregate(total=models.Sum('valor'))['total'] or 0
        # Caixa: receitas/despesas/saldo
        caixa_qs = CaixaLancamento.objects.all()
        try:
            if ano:
                caixa_qs = caixa_qs.filter(data__year=int(ano))
            if mes:
                caixa_qs = caixa_qs.filter(data__month=int(mes))
        except Exception:
            pass
        receitas = caixa_qs.filter(tipo='receita').aggregate(total=models.Sum('valor'))['total'] or 0
        despesas = caixa_qs.filter(tipo='despesa').aggregate(total=models.Sum('valor'))['total'] or 0
        saldo = (receitas or 0) - (despesas or 0)
        # Devedores: pescadores com alguma mensalidade pendente no período filtrado
        devedores_ids = m_qs.filter(status="pendente").values_list("pescador_id", flat=True).distinct()
        devedores = Pescador.objects.filter(id__in=devedores_ids).order_by("nome")
        try:
            filtro_mes_int = int(mes) if mes else None
        except Exception:
            filtro_mes_int = None
        contexto = {
            "total_associados": total_associados,
            "total_mensalidades_pagas": total_mensalidades_pagas,
            "total_mensalidades_pendentes": total_mensalidades_pendentes,
            "devedores": devedores[:50],
            "filtro_mes": mes,
            "filtro_mes_int": filtro_mes_int,
            "filtro_ano": ano,
            "config": AssociacaoConfig.get_solo(),
            "months": list(range(1, 13)),
            "total_recebido": total_recebido,
            "receitas": receitas,
            "despesas": despesas,
            "saldo": saldo,
        }
        return render(request, self.template_name, contexto)


class CaixaView(View):
    template_name = "caixa/index.html"

    def get(self, request):
        mes = request.GET.get("mes")
        ano = request.GET.get("ano")
        lanc_qs = CaixaLancamento.objects.all()
        try:
            if ano:
                lanc_qs = lanc_qs.filter(data__year=int(ano))
            if mes:
                lanc_qs = lanc_qs.filter(data__month=int(mes))
        except Exception:
            pass
        receitas = lanc_qs.filter(tipo='receita').aggregate(total=models.Sum('valor'))['total'] or 0
        despesas = lanc_qs.filter(tipo='despesa').aggregate(total=models.Sum('valor'))['total'] or 0
        saldo = (receitas or 0) - (despesas or 0)
        form = CaixaLancamentoForm()
        ctx = {
            "lancamentos": lanc_qs[:200],
            "form": form,
            "months": list(range(1, 13)),
            "filtro_mes": mes,
            "filtro_ano": ano,
            "receitas": receitas,
            "despesas": despesas,
            "saldo": saldo,
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        form = CaixaLancamentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Lançamento de caixa cadastrado.")
        else:
            messages.error(request, "Não foi possível salvar. Verifique os campos.")
        return redirect("associados:caixa")


class CaixaEditView(UpdateView):
    model = CaixaLancamento
    form_class = CaixaLancamentoForm
    template_name = "caixa/edit.html"
    success_url = reverse_lazy("associados:caixa")


def caixa_excluir(request, pk):
    lanc = get_object_or_404(CaixaLancamento, pk=pk)
    if request.method == "POST":
        lanc.delete()
        messages.success(request, "Lançamento removido.")
    return redirect("associados:caixa")


def mensalidade_excluir(request, pk):
    mensalidade = get_object_or_404(Mensalidade, pk=pk)
    pescador_id = mensalidade.pescador.pk
    if request.method == "POST":
        if mensalidade.status == "pago":
            messages.error(request, "Não é possível excluir mensalidade já paga.")
        else:
            mensalidade.delete()
            messages.success(request, "Mensalidade excluída com sucesso.")
    return redirect("associados:pescador_detail", pk=pescador_id)


class AssociacaoConfigUpdateView(UpdateView):
    model = AssociacaoConfig
    form_class = AssociacaoConfigForm
    template_name = "associados/associacao_config.html"
    success_url = reverse_lazy("associados:associacao_config")

    def get_object(self, queryset=None):
        return AssociacaoConfig.get_solo()

    def form_valid(self, form):
        messages.success(self.request, "Dados da associação salvos com sucesso.")
        return super().form_valid(form)


# ----------------------
# Dossiê do Defeso (PDF)
# ----------------------

REQUIRED_DOCS = [
    ("RG", "RG"),
    ("CPF", "CPF"),
    ("RGP", "RGP"),
    ("COMPROVANTE_ENDERECO", "Comprovante de Endereço"),
]


def defeso_dossie_pdf(request, pk):
    pescador = get_object_or_404(Pescador, pk=pk)
    config = AssociacaoConfig.get_solo()

    # Checklist de mensalidades: ano corrente, 12 pagas
    ano = date.today().year
    pagas_ano = Mensalidade.objects.filter(pescador=pescador, competencia__year=ano, status="pago").count()
    mensalidades_ok = pagas_ano >= 12

    # Checklist de documentos obrigatórios
    docs = pescador.documentos.all()
    docs_por_tipo = {d.tipo: d for d in docs}
    docs_check = []
    for cod, nome in REQUIRED_DOCS:
        docs_check.append({
            "codigo": cod,
            "nome": nome,
            "ok": cod in docs_por_tipo,
            "doc": docs_por_tipo.get(cod),
        })
    docs_ok = all(item["ok"] for item in docs_check)

    # PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"inline; filename=dossie_defeso_{pescador.id}.pdf"

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Capa com logo e associação
    p.setLineWidth(1)
    p.rect(40, height - 140, width - 80, 90)
    if config.logo:
        try:
            img = ImageReader(config.logo.path)
            img_w, img_h = img.getSize()
            max_w, max_h = 110, 70
            ratio = min(max_w / img_w, max_h / img_h)
            dw, dh = img_w * ratio, img_h * ratio
            p.drawImage(img, width - 60 - dw, height - 60 - dh, dw, dh, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 70, config.nome or "Associação")
    p.setFont("Helvetica", 11)
    p.drawString(50, height - 90, f"Presidente: {config.presidente or '-'}")
    p.drawString(50, height - 105, f"CNPJ: {config.cnpj or '-'} | Tel: {config.telefone or '-'} | Email: {config.email or '-'}")

    # Título
    p.setFont("Helvetica-Bold", 18)
    title = "DOSSIÊ DO SEGURO DEFESO"
    tw = p.stringWidth(title, "Helvetica-Bold", 18)
    p.drawString((width - tw) / 2, height - 170, title)

    # Identificação do pescador
    p.setFont("Helvetica", 12)
    y = height - 200
    p.drawString(50, y, f"Pescador: {pescador.nome}")
    y -= 18
    p.drawString(50, y, f"CPF: {pescador.cpf}   RGP: {pescador.rgp}")
    y -= 18
    p.drawString(50, y, f"Data de Associação: {pescador.data_associacao.strftime('%d/%m/%Y')}")

    # Checklist resumo
    y -= 28
    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y, "Checklist")
    y -= 20
    p.setFont("Helvetica", 12)
    p.drawString(60, y, f"Mensalidades pagas em {ano}: {pagas_ano}/12 - {'OK' if mensalidades_ok else 'PENDENTE'}")
    y -= 18
    p.drawString(60, y, f"Documentos obrigatórios: {'OK' if docs_ok else 'PENDENTE'}")

    # Documentos
    y -= 28
    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y, "Documentos Obrigatórios")
    p.setFont("Helvetica", 12)
    y -= 18
    for item in docs_check:
        status = "OK" if item["ok"] else "FALTANDO"
        txt = f"- {item['nome']}: {status}"
        if item["ok"] and item["doc"]:
            txt += f" (enviado em {item['doc'].data_upload.strftime('%d/%m/%Y %H:%M')})"
        p.drawString(60, y, txt)
        y -= 16
        if y < 80:
            p.showPage(); y = height - 60

    # Mensalidades do ano (sumário)
    y -= 10
    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y, f"Mensalidades {ano}")
    y -= 18
    p.setFont("Helvetica", 12)
    mens_ano = Mensalidade.objects.filter(pescador=pescador, competencia__year=ano).order_by('competencia')
    for m in mens_ano:
        txt = f"- {m.competencia.strftime('%m/%Y')} | {m.get_status_display()} | Valor: R$ {m.valor}"
        if m.data_pagamento:
            txt += f" | Pago em {m.data_pagamento.strftime('%d/%m/%Y')}"
        p.drawString(60, y, txt)
        y -= 16
        if y < 80:
            p.showPage(); y = height - 60

    # Rodapé
    p.setFont("Helvetica", 9)
    p.drawRightString(width - 50, 50, f"Emitido em {date.today().strftime('%d/%m/%Y')}")

    p.showPage()
    p.save()
    return response

# Create your views here.
