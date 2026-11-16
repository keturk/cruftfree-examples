# AWS Lambda container image (Node.js/TypeScript).
# The AWS base image bundles the Node.js runtime and the Lambda Runtime
# Interface Client (RIC) -- no separate RIC install is needed
# (docs.aws.amazon.com/lambda/latest/dg/nodejs-image.html).
FROM public.ecr.aws/lambda/nodejs:22@sha256:f4f30ba3a882589f91824fc850626b7a13c6649131fc3351c252459eae605d94

COPY package.json ${LAMBDA_TASK_ROOT}
RUN npm install --omit=dev

# Copy this Lambda's adapter modules (cruftfree-codegen-typescript's
# platform-agnostic handler modules + thin AWS Lambda adapters) onto the
# Lambda task root, then compile them to CommonJS in place. ``typescript``
# is a dev-scoped dependency never present in the runtime catalog above, so
# it is pulled on demand rather than installed as a project dependency.
# ``--noResolve`` transpiles each file without following its own module
# imports: the adapter's sibling handler-module import lives outside this
# image's build context (this Dockerfile's own directory), exactly like
# every other file this image's Python counterpart also excludes -- Node's
# own module resolution finds the copied sibling at invocation time
# instead, never at this build step.
COPY *.ts ${LAMBDA_TASK_ROOT}/
RUN npx --yes typescript@5.5.0 tsc --noResolve --skipLibCheck \
    --module commonjs --target es2022 ${LAMBDA_TASK_ROOT}/*.ts

# No CMD: every Lambda function built from this image is invoked with an
# explicit command override, its function's ``ImageConfig.Command``
# (``iac/graph_builders/serverless.py``) -- one image, many
# functions, each naming its own handler at deploy time rather than a single
# baked-in default (AWS's own docs note the CMD instruction is optional
# when the handler is always supplied "as a parameter override outside of
# the Dockerfile").
