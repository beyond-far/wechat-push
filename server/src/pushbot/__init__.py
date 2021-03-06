import logging
import os
import json
import logging.config
from urllib.parse import urlparse

import dotenv
from aiohttp import web
import redis

from wechat.core import TokenManager
from pushbot import models
from pushbot import views


def initLogger():
    configfile = os.environ.get('LOGGING_CONFIG', 'logging.json')
    if os.path.exists(configfile):
        with open(configfile) as f:
            config = json.load(f)
        logging.config.dictConfig(config)


logger = logging.getLogger(__name__)


def routes(urlRoot):
    return [
        # messages
        web.post(urlRoot + 'message', views.Message.post),
        web.get(urlRoot + 'message/{token}', views.Message.get),
        # scene (scan for receiver id)
        web.post(urlRoot + 'scene', views.Scene.post),
        web.get(urlRoot + 'scene/{scene_id}', views.Scene.get),
        # callback from wechat
        web.get(urlRoot + 'callback', views.Callback.get),
        web.post(urlRoot + 'callback', views.Callback.post),
    ]


def createApp():
    # load env
    dotenv.load_dotenv('.env')
    # init log
    initLogger()

    APP_ID = os.environ['APP_ID']
    APP_SECRET = os.environ['APP_SECRET']
    # load url root
    URL_ROOT = os.environ.get('SERVER_API_ROOT', '/')
    if not (URL_ROOT.startswith('/') and URL_ROOT.endswith('/')):
        raise ValueError(
            'SERVER_API_ROOT must starts and ends with a slash (/).')
    # load wechat message view url
    VUE_APP_ROOT_URL = os.environ.get('VUE_APP_ROOT_URL', None)
    if VUE_APP_ROOT_URL is None:
        raise ValueError(
            'VUE_APP_ROOT_URL must be set to enable detail page.')
    parseResult = urlparse(VUE_APP_ROOT_URL)
    ALLOWED_DOMAINS = '{}://{}'.format(
        parseResult.scheme, parseResult.netloc)
    # load wechat token
    WECHAT_TOKEN = os.environ.get('WECHAT_TOKEN', None)
    if WECHAT_TOKEN is None:
        raise ValueError('WECHAT_TOKEN must be set to verify wechat callback.')
    # load redis db
    r = redis.Redis.from_url(os.environ['REDIS_URL'], decode_responses=True)
    # load SQL db
    session = models.initDB(os.environ['SQL_DB_URL'])
    # initiate token manager
    manager = TokenManager(APP_ID, APP_SECRET)

    # create app
    app = web.Application()
    app.add_routes(routes(URL_ROOT))
    app['config'] = {
        'tokenManager': manager,
        'session': session,
        'redis': r,
        'APP_ID': APP_ID,
        'WECHAT_TOKEN': WECHAT_TOKEN,
        'VUE_APP_ROOT_URL': VUE_APP_ROOT_URL,
        'ALLOWED_DOMAINS': ALLOWED_DOMAINS
    }
    logger.debug('App init complete.')
    return app


async def asyncApp():
    return createApp()
