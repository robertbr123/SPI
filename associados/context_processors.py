from .models import AssociacaoConfig

def app_config(request):
    return {
        'app_config': AssociacaoConfig.get_solo()
    }
