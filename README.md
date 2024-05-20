# ott-or-not

## Overview
This project is a lighthearted playground for me to experiment with various 
technologies and techniques. The goal is to create a simple web application that allows 
users to upload images of cute animals and be told by a machine learning model whether 
the animal is an otter, or not an otter (hence the name of the website, "Ott-Or-Not"). 
If it is an otter, another model will determine what species of otter it is.

The web application is not yet up and running, but a link to it will be provided once 
the first deployment of a user interface is complete.

# Structure
This is a mono-repo project, where each directory contains the code for one specific 
part of the overall project. Each sub-directory is a Python module, using [Poetry]
(https://python-poetry.org/) as the package manager, and Python 3.12 as the base 
interpreter for the project.

Most of the machine learning material is organized in the `modeling_notebooks` Python 
module. Despite the name, this module also contains a number of python scripts that 
are imported into the notebooks. This helps keep the size of the notebooks down, and 
lets the author and reader focus on the actual purpose of the notebook, and not the 
details of the code.

The `oon_utilities` Python module contains both utility classes/functions that are 
useful across all the other projects, as well as utility scripts for accomplishing 
tasks such as assembling training/eval data from scraping internet images.

Database structure for all parts of the project can be found in the 
`database_migrations` Python module. This module uses [Alembic](https://alembic.
sqlalchemy.org/en/latest/) to manage migrations and structure, as well as Docker to 
provide convenient testing on a local instance of Postgres. This package has some 
tables already defined, though they are not yet being actively used by other projects.

In the near future there will also be a `oon_frontend` application written using the 
[Flet](https://flet.dev/) framework to define the user interface. The current plan is 
to host the machine learning API on GCP, though this plan may change as I go along.
