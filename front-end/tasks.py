from invoke import task, Collection, Context
import io
import tomllib


@task()
def down(ctx):
    ctx.run("docker compose down -v")


@task(down)
def build(ctx):
    ctx.run("docker compose build")


@task(build)
def up(ctx):
    ctx.run("docker compose up -d")


# ===== Overhead =====

# Look up other config defaults from pyproject.toml
with open("pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

other_config = pyproject["tool"].get("invoke")
ns = Collection()

if other_config:
    ns.configure(other_config)
