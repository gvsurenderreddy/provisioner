# Django-style settings file
import os

REDIS_SERVER = os.getenv('REDIS_PORT_6379_TCP_ADDR', 'redis')
REDIS_PORT = os.getenv('REDIS_PORT_6379_TCP_PORT', 6379)
REDIS_DB = os.getenv('REDIS_DB', 0)
REDIS_LIST = 'prov'
