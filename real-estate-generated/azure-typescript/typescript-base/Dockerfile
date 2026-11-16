# Shared per-system base image.
# Installs the UNION of every service's production dependencies ONCE;
# per-service Dockerfiles copy only their own compiled dist/ onto this
# image's node_modules.
FROM node:22-alpine@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914 AS runtime

WORKDIR /app

# Enable pnpm via corepack (built into Node.js); the manifest's packageManager
# pins the pnpm version.
RUN corepack enable

# Install the union of all services' production dependencies (cached until the
# union manifest or this Dockerfile changes -- the base image tag is their
# content hash). The node_modules tree stays owned by root: the service images
# run as the unprivileged `node` user, which can read it but not modify it.
COPY package.json ./
RUN pnpm install --prod --shamefully-hoist
