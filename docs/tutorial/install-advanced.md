Si le projet marche chez vous après avoir suivi les étapes 
données dans la page précédente, alors vous pouvez développer.
Ce que nous nous vous avons présenté n'est absolument pas
la même configuration que celle du site, mais elle n'en
est pas moins fonctionnelle.

Cependant, vous pourriez avoir envie de faire en sorte
que votre environnement de développement soit encore plus
proche de celui en production.
Voici les étapes à suivre pour ça.

!!!tip

    Configurer les dépendances du projet
    peut demander beaucoup d'allers et retours entre
    votre répertoire projet et divers autres emplacements.

    Vous pouvez gagner du temps en déclarant un alias :

    === "bash/zsh"

        ```bash
        alias cdp="cd /repertoire/du/projet"
        ```

    === "nu"

        ```nu
        alias cdp = cd /repertoire/du/projet
        ```

    Chaque fois qu'on vous demandera de retourner au répertoire
    projet, vous aurez juste à faire :

    ```bash
    cdp
    ```

## Installer les dépendances manquantes

Pour installer complètement le projet, il va falloir
quelques dépendances en plus.
Commencez par installer les dépendances système :

=== "Linux"

    === "Debian/Ubuntu"

        ```bash
        sudo apt install postgresql redis libq-dev nginx
        ```

    === "Arch Linux"
    
        ```bash
        sudo pacman -S postgresql redis nginx
        ```

=== "macOS"

    ```bash
    brew install postgresql redis lipbq nginx
    export PATH="/usr/local/opt/libpq/bin:$PATH"
    source ~/.zshrc
    ```

Puis, installez les dépendances nécessaires en prod :

```bash
uv sync --group prod
```

!!! info

    Certaines dépendances peuvent être un peu longues à installer
    (notamment psycopg-c).
    C'est parce que ces dépendances compilent certains modules
    à l'installation.

## Configurer Redis

Redis est utilisé comme cache.
Assurez-vous qu'il tourne :

```bash
sudo systemctl redis status
```

Et s'il ne tourne pas, démarrez-le :

```bash
sudo systemctl start redis
sudo systemctl enable redis  # si vous voulez que redis démarre automatiquement au boot
```

Puis ajoutez le code suivant à la fin de votre fichier
`settings_custom.py` :

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379",
    }
}
```

## Configurer PostgreSQL

PostgreSQL est utilisé comme base de données.

Passez sur le compte de l'utilisateur postgres 
et lancez l'invite de commande sql :

```bash
sudo su - postgres
psql
```

Puis configurez la base de données :

```postgresql
CREATE DATABASE sith;
CREATE USER sith WITH PASSWORD 'password';

ALTER ROLE sith SET client_encoding TO 'utf8';
ALTER ROLE sith SET default_transaction_isolation TO 'read committed';
ALTER ROLE sith SET timezone TO 'UTC';

GRANT ALL PRIVILEGES ON DATABASE sith TO SITH;
\q
```

Si vous utilisez une version de PostgreSQL supérieure ou égale
à 15, vous devez exécuter une commande en plus,
en étant connecté en tant que postgres :

```bash
psql -d sith -c "GRANT ALL PRIVILEGES ON SCHEMA public to sith";
```

Puis ajoutez le code suivant à la fin de votre
`settings_custom.py` :

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "sith",
        "USER": "sith",
        "PASSWORD": "password",
        "HOST": "localhost",
        "PORT": "",  # laissez ce champ vide pour que le choix du port soit automatique
    }
}
```

Enfin, créez vos données :

```bash
uv run ./manage.py populate
```

!!! note

    N'oubliez de quitter la session de l'utilisateur
    postgres après avoir configuré la db.

## Configurer nginx

Nginx est utilisé comme reverse-proxy.

!!!warning

    Nginx ne sert pas les fichiers de la même manière que Django.
    Les fichiers statiques servis seront ceux du dossier `/static`,
    tels que générés par les commandes `collectstatic` et
    `compilestatic`.
    Si vous changez du css ou du js sans faire tourner
    ces commandes, ces changements ne seront pas reflétés.

    De manière générale, utiliser nginx en dev n'est pas très utile,
    voire est gênant si vous travaillez sur le front.
    Ne vous embêtez pas avec ça, sauf par curiosité intellectuelle,
    ou bien si vous voulez tester spécifiquement 
    des interactions avec le reverse proxy.


Placez-vous dans le répertoire `/etc/nginx`, 
et créez les dossiers et fichiers nécessaires :

```bash
cd /etc/nginx/
sudo mkdir sites-enabled sites-available
sudo touch sites-available/sith.conf
sudo ln -s /etc/nginx/sites-available/sith.conf sites-enabled/sith.conf
```

Puis ouvrez le fichier `sites-available/sith.conf` et mettez-y le contenu suivant :

```nginx
server {
    listen 8000;

    server_name _;

    location /static/;
        root /repertoire/du/projet;
    }
    location ~ ^/data/(products|com|club_logos)/ {
        root /repertoire/du/projet;
    }
    location ~ ^/data/(SAS|profiles|users|.compressed|.thumbnails)/ {
        # https://nginx.org/en/docs/http/ngx_http_core_module.html#internal
        internal;
        root /repertoire/du/projet;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        include uwsgi_params;
    }
}
```

Ouvrez le fichier `nginx.conf`, et ajoutez la configuration suivante :

```nginx
http {
    # Toute la configuration
    # éventuellement déjà là

    include /etc/nginx/sites-enabled/sith.conf;
}
```

Vérifiez que votre configuration est bonne :

```bash
sudo nginx -t
```

Si votre configuration n'est pas bonne, corrigez-la.
Puis lancez ou relancez nginx :

```bash
sudo systemctl restart nginx
```

Dans votre `settings_custom.py`, remplacez `DEBUG=True` par `DEBUG=False`.

Enfin, démarrez le serveur Django :

```bash
cd /repertoire/du/projet
uv run ./manage.py runserver 8001
```

Et c'est bon, votre reverse-proxy est prêt à tourner devant votre serveur.
Nginx écoutera sur le port 8000.
Toutes les requêtes vers des fichiers statiques et les medias publiques
seront seront servies directement par nginx.
Toutes les autres requêtes seront transmises au serveur django.


## Mettre à jour la base de données antispam

L'anti spam nécessite d'être à jour par rapport à des bases de données externes.
Il existe une commande pour ça qu'il faut lancer régulièrement.
Lors de la mise en production, il est judicieux de configurer
un cron pour la mettre à jour au moins une fois par jour.

```bash
python manage.py update_spam_database
```
