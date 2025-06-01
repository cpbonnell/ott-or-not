from invoke import task, Collection, Context
import io
import aws


@task()
def down(ctx):
    ctx.run("docker compose down -v")


@task(down)
def build(ctx):
    ctx.run("docker compose build")


@task(build)
def up(ctx):
    ctx.run("docker compose up -d")


@task(aws.profile, aws.region, aws.account_id)
def login(ctx: Context, aws_profile: str = None):

    if not aws_profile:
        aws_profile = ctx.aws.profile

    print("Logging into AWS ECR...")
    result = ctx.run(f"aws ecr get-login-password --profile {aws_profile}", hide=True)
    print("ECR key retrieved...")

    login_key = result.stdout.strip()
    print(f"Got a key of size {len(login_key)} starting in {login_key[:5]}")

    # Log Docker into the AWS ECR instance
    print("Logging docker into AWS ECR...")
    endpoint = f"{ctx.aws.account_id}.dkr.ecr.{ctx.aws.region}.amazonaws.com"
    result = ctx.run(
        command=f"docker login --username AWS --password-stdin {endpoint}",
        in_stream=io.StringIO(login_key),
    )
    print(f"Docker has been logged in: {result.stdout}")


# ===== Overhead =====
ns = Collection(down, build, up, login)
ns.add_collection(aws)
