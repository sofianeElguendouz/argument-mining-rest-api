Argumentation Mining Tool
===============================

This repository has the code to run the [Argumentation Mining
REST API](https://orbis.i3s.unice.fr/).

The base application is written with [Django](https://www.djangoproject.com/)
and [Django Rest Framework](https://www.django-rest-framework.org/) for the REST
API.

The webserver is configured to run with [Gunicorn](https://gunicorn.org/) as
WSGI server, behind a [nginx](https://nginx.org/en/) HTTP proxy server via
[Docker Compose](https://docs.docker.com/compose/install/).

Setup for a Development (Local) Environment
-------------------------------------------

For development purposes, the easiest solution is to just use Django's
integrated server. This server is useful for debugging purposes, but it's not
good for deploying the application on a production environment.

### Webserver Base Requirements Installation

First step is to create virtual environment. The dependencies of the project are defined in the [`pyproject.toml`](./pyproject.toml) file:

```bash
$ python -m venv venv
$ source ./venv/bin/activate
(venv) $ pip install --upgrade pip setuptools wheel
(venv) $ pip install -e ".[dev]"  # Installs all the dependencies, including development dependencies.
```

With all the dependencies installed, we need to setup the database and run the
server:

```bash
(venv) $ cd ./orbis_am_module  # Move to the base directory of the Django app
(venv) $ ./manage.py migrate  # Creates the DB, defined in the Django settings
(venv) $ ./manage.py createsuperuser  # Creates the admin superuser
(venv) $ ./manage.py runserver  # Runs the development server
```

The first time it runs, the application will try and download the Hugging Face
models from the repository. The models configured by default are public, but if
you change them to private, you'll need to define your token before running any
of the commands above, otherwise they will fail.

Once the application is running you can access it at [`http://localhost:8000/`]
which should redirect you to the [API
Documentation](`http://localhost:8000/api/docs/`). You can also access the
[Django Admin Interface](http://localhost:8000/admin/).

By default, the application will create a database file using Sqlite (as defined
in the
[`./orbis_am_tool/orbis_am_tool/settings/__init__.py`](./orbis_am_tool/orbis_am_tool/settings/__init__.py)),
if you want to use another DB engine you'll need to [configure](#configuration)
it accordingly.

For more information on how the Django application works, you should read on
[Django's documentation](https://www.djangoproject.com/start/). In particular,
if this is your first experience with Django, before modifying anything, you
should finish the [Django
Tutorial](https://docs.djangoproject.com/en/5.0/intro/tutorial01/).

Configuration
-------------

The base configuration file is located in
[`./orbis_am_tool/orbis_am_tool/settings/__init__.py`](./orbis_am_tool/orbis_am_tool/settings/__init__.py),
it provides some basic configurations, particularly useful ones for setting up
the development server, however, if you need to change some configurations,
perhaps add extra stuff, etc., you shouldn't resort to changing that file, and
instead creating a new python file that imports the base settings file. All
configuration files stored in the settings directory will be ignored by git as
each configuraiton should be specific to each machine is running the server.
There is however an [example
file](./orbis_am_tool/orbis_am_tool/settings/prod.py.example) that shows a
typical production environment configuration file that we will discuss further
in the [deployment section](#deployment).

For example, if you'd like to change the path to the path to the Hugging Face
models, you can do it by creating a new configuration file `dev.py` inside
[`./orbis_am_tool/orbis_am_tool/settings/`](./orbis_am_tool/orbis_am_tool/settings/),
with the following structure:

```python
from orbis_am_tool.settings import *  # Import the base configuration

ARGUMENTS_COMPONENTS_MODEL = "new/model"
```

Then, in order for you to run the development server with the new configuration
file, you should set it up by exporting it first:

```bash
(venv) $ export DJANGO_SETTINGS_MODULE=orbis_am_tool.settings.dev
(venv) $ ./manage.py runserver  # Runs the development server
```

To read about the Django configuration, please to the [Django
documentation](https://docs.djangoproject.com/en/5.0/ref/settings/).

Configurations that are particular to the flow of the application are at the end
of the file, under the "ORBIS Argumentation Mining Tool Configurations" section
of the settings file. Most of these configurations have to do with the models to
use in the application as well as some parameters to better control the models
(e.g., the minimum threshold score for a classifier model to be taken into
account).

Deployment
----------

### Environment File

The deployment of the application is done via Docker and Docker Compose. Before running the corresponding commands to create the images, you first need to create the envionment file, the repository provides an example [`.env.example`](./.env.example) that you can copy:

```bash
$ cp .env.example .env
```

You need to fill the information of the file that is missing, which are
corresponding to secrets and passwords. **Don't upload this file to the
repository, it must be specific for the deployment server**. If there's already
a file `.env`, check it first, it might be already set up.

### Production Environment Settings

The file
[`./orbis_am_tool/orbis_am_tool/settings/prod.py.example`](./orbis_am_tool/orbis_am_tool/settings/prod.py.example)
shows you an example of a production ready file, that uses also the environment,
if it's not already in the server, you can copy it and modify it accordingly.

There's a [checklist from
Django](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/) on
what are the steps to follow in order to build a production ready environment
file if you'd like more information. Please check if there are already a
configuration file in place before copying anything.

#### SECRET_KEY

One important configuration on a production environment is the `SECRET_KEY`
configuration, if it hasn't been already set, you should generate it. Django
provides a way to do so, for more information please check [this blog
article](https://humberto.io/blog/tldr-generate-django-secret-key/)

### Building the Docker Images

Once you generated the configuration environment file, you can proceed to create
the docker images (there's no need for virtual environment here). This generally
need sudo access:

    $ sudo docker compose build

#### Installation of Requirements in Docker Image

The [`Dockerfile`](./Dockerfile) uses the
[`requirements.txt`](./requirements.txt) file to setup the application. This
file was generated with the help of the `uv pip compile` command. This is
because the original application was build using the highly recommended
[`uv`](https://astral.sh/blog/uv) package rather than `pip`, and we generated
the `requirements.txt` file with the following command:

```bash
$ uv pip compile pyproject.toml -o requirements.txt --no-strip-extras --extra-index-url https://download.pytorch.org/whl/cpu
```

Another way to generate the `requirements.txt` file is, with a fresh installation in a virtual environment, via `pip freeze`:

```bash
(venv) $ pip freeze > requirements.txt
```

Although this last might add also extra packages that might not be required. In
any case, if you add a new requirements to the `pyproject.toml` file, please
make sure that you are setting up the `requirements.txt` file accordingly to
avoid failing dependencies.

#### Database

The [`docker-compose.yml`](./docker-compose.yml) file also provides a service
for the database, named `pg`, that will create a docker volume. This is a
postgres image mounted as a docker container, with the volume to allow data
persistance. The database can be set by setting the corresponding environment
variables in the `.env` file.

#### Nginx and HTTPS

The configurations for the nginx reverse proxy in the docker compose file is
managed in the file [`./nginx/default.conf`](./nginx/default.conf) that is
mounted as a volume for the `app` service in the docker compose file. The
configuration file is expected to have mounted a couple of certification/key
files for the HTTPS certification, that should be inside the development server,
the same as the production configuration or the environment file, you **must not
upload these certification files to the GitHub repository** (that's why they are
ignored in the `.gitignore` file).

### Running the Docker Containers

Once the images finished building you can run the docker containers:

```bash
$ sudo docker compose up -d
```

And you can check on logging for the webserver application (which is the one
that takes the most time to load) with logging:

```bash
$ sudo docker compose logs -f orbis_am_tool
```

To see the current running containers you can check them like so:

```bash
$ sudo docker compose ps
```

Setup for SystemD Service
-------------------------

In order to have this running as a service for the OS, there are a couple of
service configuration files that are ready available for `systemd`. You can
check them in [`./systemd/`](./systemd/). There are 3 files, 2 service files and
a timer.

In order to setup the application, you should change the `WorkingDirectory` of
the `./config/systemd/orbis-am-tool.service` file to match the directory where
this repository is held. E.g. if you have your repository in
`/home/orbis/orbis-argument-mining-tool`, that should be your working directory
(that's the default value in the repository).

After that, create a couple of symlinks to `/etc/systemd/system` for each of the
systemd files (this requires root/sudo access, check the `#` instead of the `$`
prompt):

    # ln -s $PWD/systemd/orbis-am-tool.service /etc/systemd/system
    # ln -s $PWD/systemd/docker-cleanup.service /etc/systemd/system
    # ln -s $PWD/systemd/docker-cleanup.timer /etc/systemd/system

Reload the systemd daemon:

    # systemctl daemon-reload

And activate and enable the services:

    # systemctl start orbis-am-tool.service
    # systemctl enable orbis-am-tool.service
    # systemctl start docker-cleanup.timer
    # systemctl enable docker-cleanup.timer
    # systemctl start docker-cleanup.service
    # systemctl enable docker-cleanup.service

Finally, you can check the status of each service:

    # systemctl status orbis-am-tool.service
    # systemctl status docker-cleanup.timer
    # systemctl status docker-cleanup.service

The systemd files were based on this [GitHub Gist](https://gist.github.com/mosquito/b23e1c1e5723a7fd9e6568e5cf91180f).
