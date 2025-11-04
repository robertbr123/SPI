from django import forms
from stdnum.br import cpf as br_cpf
from stdnum.br import cnpj as br_cnpj
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from .models import Pescador, Endereco, Documento, Mensalidade, AssociacaoConfig, CaixaLancamento


class PescadorForm(forms.ModelForm):
    class Meta:
        model = Pescador
        fields = ["nome", "cpf", "data_nascimento", "rg", "rg_orgao_emissor", "rgp", "telefone", "data_associacao"]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
            "data_associacao": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Salvar", css_class="btn btn-primary"))

    def clean_cpf(self):
        value = self.cleaned_data.get("cpf", "")
        try:
            br_cpf.validate(value)
        except Exception:
            raise forms.ValidationError("CPF inválido.")
        return value


class EnderecoForm(forms.ModelForm):
    class Meta:
        model = Endereco
        fields = ["logradouro", "numero", "complemento", "bairro", "cidade", "estado", "cep"]

    UF_CHOICES = [
        ("", "Selecione"),
        ("AC", "AC"), ("AL", "AL"), ("AM", "AM"), ("AP", "AP"), ("BA", "BA"), ("CE", "CE"), ("DF", "DF"),
        ("ES", "ES"), ("GO", "GO"), ("MA", "MA"), ("MG", "MG"), ("MS", "MS"), ("MT", "MT"), ("PA", "PA"),
        ("PB", "PB"), ("PE", "PE"), ("PI", "PI"), ("PR", "PR"), ("RJ", "RJ"), ("RN", "RN"), ("RO", "RO"),
        ("RR", "RR"), ("RS", "RS"), ("SC", "SC"), ("SE", "SE"), ("SP", "SP"), ("TO", "TO"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estado"].widget = forms.Select(choices=self.UF_CHOICES)


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["tipo", "arquivo", "observacao"]


class AssociacaoConfigForm(forms.ModelForm):
    class Meta:
        model = AssociacaoConfig
        fields = [
            "nome",
            "presidente",
            "logo",
            "assinatura_presidente",
            "cnpj",
            "telefone",
            "email",
            "endereco",
            "cidade",
            "estado",
            "cep",
            "valor_mensalidade_padrao",
        ]

    def clean_cnpj(self):
        value = self.cleaned_data.get("cnpj", "")
        if value:
            try:
                br_cnpj.validate(value)
            except Exception:
                raise forms.ValidationError("CNPJ inválido.")
        return value


class MensalidadePagarForm(forms.ModelForm):
    class Meta:
        model = Mensalidade
        fields = ["valor", "data_pagamento", "forma_pagamento", "observacao"]
        widgets = {
            "data_pagamento": forms.DateInput(attrs={"type": "date"}),
        }


class CaixaLancamentoForm(forms.ModelForm):
    class Meta:
        model = CaixaLancamento
        fields = ["tipo", "categoria", "descricao", "valor", "data"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
        }
