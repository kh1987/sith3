"""
Django settings for sith project.

Generated by 'django-admin startproject' using Django 1.8.6.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '(4sjxvhz@m5$0a$j0_pqicnc$s!vbve)z+&++m%g%bjhlz4+g2'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'club',
    'subscription',
    'accounting',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'sith.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sith.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Medias
MEDIA_ROOT = './data/'
MEDIA_URL = '/data/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

# Auth configuration

AUTH_USER_MODEL = 'core.User'
AUTH_ANONYMOUS_MODEL = 'core.models.AnonymousUser'
LOGIN_URL = '/login'
LOGOUT_URL = '/logout'
LOGIN_REDIRECT_URL = '/'
DEFAULT_FROM_EMAIL="bibou@git.an"

# Email
EMAIL_HOST="localhost"
EMAIL_PORT=25

# AE configuration
AE_MAIN_CLUB = {
        'name': "AE",
        'unix_name': "ae",
        'address': "6 Boulevard Anatole France, 90000 Belfort"
        }
# Define the date in the year serving as reference for the subscriptions calendar
# (month, day)
AE_START_DATE = (8, 15) # 15th August
AE_GROUPS = {
    'root': {
        'id': 1,
        'name': "root",
    },
    'board': {
        'id': 2,
        'name': "ae_bureau",
    },
    'members': {
        'id': 3,
        'name': "ae_membres",
    },
    'public': {
        'id': 4,
        'name': "not_registered_users",
    },
}

AE_PAYMENT_METHOD = [('cheque', 'Chèque'),
                     ('cash', 'Espèce'),
                     ('other', 'Autre'),
                    ]

# Subscription durations are in semestres (should be settingized)
AE_SUBSCRIPTIONS = {
    'un-semestre': {
        'name': 'Un semestre',
        'price': 15,
        'duration': 1,
    },
    'deux-semestres': {
        'name': 'Deux semestres',
        'price': 28,
        'duration': 2,
    },
    'cursus-tronc-commun': {
        'name': 'Cursus Tronc Commun',
        'price': 45,
        'duration': 4,
    },
    'cursus-branche': {
        'name': 'Cursus Branche',
        'price': 45,
        'duration': 6,
    },
# To be completed....
}

CLUB_ROLES = {
        10: 'Président',
        9: 'Vice-Président',
        8: 'Vice-Président',
        7: 'Trésorier',
        5: 'Responsable com',
        4: 'Secrétaire',
        3: 'Responsable info',
        2: 'Membre du bureau',
        1: 'Membre actif',
        0: 'Membre',
        }
