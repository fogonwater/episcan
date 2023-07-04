import os

# Store api key on environmental variable
# so we can use it with Github secrets
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY')