from dotenv import load_dotenv
import os

if os.getenv('ENV') == 'dev':
    load_dotenv('.env.dev')
    from .dev import *
elif os.getenv('ENV') == 'prod':
    load_dotenv('.env.prod')
    from .prod import *
else:
    # from .old import *
    raise ValueError('Invalid environment specified. Use "dev" or "prod"')
