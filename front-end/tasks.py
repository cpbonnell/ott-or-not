from invoke import task, Collection, Context
import io
import aws
import tomllib

with open("pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

package_version = pyproject["project"]["version"]
# service_name = pyproject["project"]["name"]
service_name = "oon/front-end"


@task()
def down(ctx):
    ctx.run("docker compose down -v")


@task(down)
def build(ctx, tag: str | None = None):
    new_env = {}
    if tag:
        new_env["TAG"] = tag
    ctx.run("docker compose build", env=new_env)


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


@task(aws.profile, aws.region, aws.account_id)
def register(ctx: Context):
    # NOTE: this only works if a repository with the expected name already exists

    print(f"Step 1 - Building the image and tagging with {package_version}")
    build(ctx, tag=package_version)

    print("Step 2 - Beginning login process...")
    login(ctx)

    print("Step 3 - Tag the image")
    endpoint = f"{ctx.aws.account_id}.dkr.ecr.{ctx.aws.region}.amazonaws.com"
    source_image = f"{service_name}:{package_version}"
    destination_image = f"{endpoint}/{source_image}"
    result = ctx.run(f"docker tag {source_image} {destination_image}")

    print("Step 4 - Push the image to AWS ECR")
    result = ctx.run(f"docker push {destination_image}")


# ===== Overhead =====
ns = Collection(down, build, up, login, register)
ns.add_collection(aws)
