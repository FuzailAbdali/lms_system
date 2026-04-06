from .base import *

DEBUG = False
ALLOWED_HOSTS = get_env_list("ALLOWED_HOSTS", "yourdomain.com") or ['yourdomain.com']
