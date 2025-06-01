from invoke import task


@task()
def down(ctx):
    ctx.run("docker compose down -v")


@task(down)
def build(ctx):
    ctx.run("docker compose build")


@task(build)
def up(ctx):
    ctx.run("docker compose up -d")
