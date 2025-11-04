from django.conf import settings
from django.db import models
from django.utils import timezone


class Pescador(models.Model):
    nome = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True, help_text="Formato: 000.000.000-00")
    data_nascimento = models.DateField()
    rg = models.CharField(max_length=20, blank=True)
    rg_orgao_emissor = models.CharField(max_length=50, blank=True)
    rgp = models.CharField(max_length=30, unique=True)
    telefone = models.CharField(max_length=20, blank=True)
    seguro_defeso_pedido = models.BooleanField(default=False)
    data_associacao = models.DateField(default=timezone.now)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.cpf})"


class Endereco(models.Model):
    pescador = models.OneToOneField(Pescador, on_delete=models.CASCADE, related_name="endereco")
    logradouro = models.CharField(max_length=200)
    numero = models.CharField(max_length=20)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    cep = models.CharField(max_length=9, help_text="Formato: 00000-000")

    def __str__(self):
        return f"{self.logradouro}, {self.numero} - {self.bairro} - {self.cidade}/{self.estado}"


class Documento(models.Model):
    TIPO_CHOICES = [
        ("RG", "RG"),
        ("CPF", "CPF"),
        ("RGP", "RGP"),
        ("COMPROVANTE_ENDERECO", "Comprovante de Endereço"),
        ("FOTO", "Foto 3x4"),
        ("OUTRO", "Outro"),
    ]
    pescador = models.ForeignKey(Pescador, on_delete=models.CASCADE, related_name="documentos")
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    arquivo = models.FileField(upload_to="documentos/")
    observacao = models.CharField(max_length=255, blank=True)
    data_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_upload"]

    def __str__(self):
        return f"{self.pescador.nome} - {self.tipo}"


class Mensalidade(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("pago", "Pago"),
        ("isento", "Isento"),
    ]
    pescador = models.ForeignKey(Pescador, on_delete=models.CASCADE, related_name="mensalidades")
    competencia = models.DateField(help_text="Use o primeiro dia do mês (AAAA-MM-01)")
    valor = models.DecimalField(max_digits=8, decimal_places=2, default=getattr(settings, "DEFAULT_MENSALIDADE", 25.00))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    data_pagamento = models.DateField(blank=True, null=True)
    forma_pagamento = models.CharField(max_length=50, blank=True)
    observacao = models.CharField(max_length=255, blank=True)
    recibo_numero = models.PositiveIntegerField(blank=True, null=True, unique=True)
    recibo_token = models.CharField(max_length=40, blank=True)

    class Meta:
        unique_together = ("pescador", "competencia")
        ordering = ["-competencia"]

    def __str__(self):
        comp = self.competencia.strftime("%m/%Y") if self.competencia else ""
        return f"{self.pescador.nome} - {comp} - {self.status}"


class AssociacaoConfig(models.Model):
    nome = models.CharField(max_length=200, default="Sistema do Pescador de Ipixuna")
    presidente = models.CharField(max_length=150, blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    assinatura_presidente = models.ImageField(upload_to="assinaturas/", blank=True, null=True)
    cnpj = models.CharField(max_length=18, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    cep = models.CharField(max_length=9, blank=True)
    valor_mensalidade_padrao = models.DecimalField(max_digits=8, decimal_places=2, default=getattr(settings, "DEFAULT_MENSALIDADE", 25.00))

    class Meta:
        verbose_name = "Configuração da Associação"
        verbose_name_plural = "Configurações da Associação"

    def __str__(self):
        return self.nome

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CaixaLancamento(models.Model):
    TIPO_CHOICES = (
        ("receita", "Receita"),
        ("despesa", "Despesa"),
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    categoria = models.CharField(max_length=100, help_text="Ex.: Mensalidade, Salário, Aluguel, Material")
    descricao = models.CharField(max_length=200, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-criado_em']

    def __str__(self):
        return f"{self.get_tipo_display()} {self.categoria} - R$ {self.valor} em {self.data}"
