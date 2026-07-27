from slowapi import Limiter
from slowapi.util import get_remote_address

# Limite padrão para os GETs; os endpoints de escrita usam 10/minute (spec 8.2).
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

LIMITE_ESCRITA = "10/minute"
