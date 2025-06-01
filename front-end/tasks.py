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


@task()
def login(ctx: Context, aws_profile: str = None):

    if not aws_profile:
        aws_profile = ctx.aws.profile
        # TODO: In the future we should handle AWS configuration more elegantly,
        #    rather than allowing only "profile" and always looking up defaults
        #    for other values

    print("Logging into AWS ECR...")
    result = ctx.run(f"aws ecr get-login-password --profile {aws_profile}", hide=True)
    print("ECR key retrieved...")

    login_key = result.stdout.strip()
    print(f"Got a key of size {len(login_key)} starting in {login_key[:5]}")

    # Look up the AWS Account ID
    result = ctx.run(
        f"aws sts get-caller-identity --profile {aws_profile} --query Account --output text"
    )
    aws_account_id = result.stdout.strip()
    print(f"Identified AWS Account ID {aws_account_id}")

    # Look up the AWS Region
    result = ctx.run(f"aws configure get region --profile {aws_profile}")
    aws_region = result.stdout.strip()
    print(f"Identified AWS Region {aws_region}")

    # Log Docker into the AWS ECR instance
    print("Logging docker into AWS ECR...")
    endpoint = f"{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com"
    result = ctx.run(
        command=f"docker login --username AWS --password-stdin {endpoint}",
        in_stream=io.StringIO(login_key),
    )
    print(f"Docker has been logged in: {result.stdout}")


# ===== Overhead =====

# Look up other config defaults from pyproject.toml
with open("pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

other_config = pyproject["tool"].get("invoke")
ns = Collection(login)

if other_config:
    ns.configure(other_config)
