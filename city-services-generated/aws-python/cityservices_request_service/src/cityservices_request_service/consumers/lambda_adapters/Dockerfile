# AWS Lambda container image.
# The AWS base image bundles the Python runtime and the Lambda Runtime
# Interface Client (RIC) -- no separate RIC install is needed
# (docs.aws.amazon.com/lambda/latest/dg/python-image.html).
FROM public.ecr.aws/lambda/python:3.12@sha256:51e4011d1e89ed5ad219607b6308ca80be46ee30099dae0afc1bb9948ba9b43f

COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy this Lambda's adapter/handler modules (cruftfree-codegen-python's
# platform-agnostic handler modules + thin AWS Lambda adapters) onto the
# Lambda task root.
COPY . ${LAMBDA_TASK_ROOT}

# No CMD: every Lambda function built from this image is invoked with an
# explicit command override, its function's ``ImageConfig.Command``
# (``iac/graph_builders/serverless.py``) -- one image, many
# functions, each naming its own handler at deploy time rather than a single
# baked-in default (AWS's own docs note the CMD instruction is optional
# when the handler is always supplied "as a parameter override outside of
# the Dockerfile").
