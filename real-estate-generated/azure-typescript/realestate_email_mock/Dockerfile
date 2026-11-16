# ---- Builder stage ----
FROM node:22-alpine@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914 AS builder

WORKDIR /app

# Enable pnpm via corepack (built into Node.js)
RUN corepack enable

# Install dependencies first (layer caching).
# No lockfile is emitted by codegen; copying a workspace lockfile can drift from
# per-service package.json. Install from the manifest only.
COPY package.json ./
RUN pnpm install --shamefully-hoist

# Copy application source and build. nest-cli.json is what tells `nest build`
# to carry the emitted JSON sidecars under src/ into dist/; without it the
# runtime image, which copies dist/ alone, is missing files the service reads
# from its own compiled directory at startup.
COPY src/ ./src/
COPY tsconfig.json* ./
COPY nest-cli.json ./
RUN pnpm run build

# ---- Runtime stage: thin layer on the shared per-system base ----
# The base image already holds the union of every service's production
# dependencies in /app/node_modules; this image adds only the compiled code.
FROM realestate-system-typescript-base:95f641c519f4 AS runtime

WORKDIR /app

COPY --from=builder /app/dist/ ./dist/

# Set environment variables
ENV PORT=8092
ENV SERVICE_NAME=realestate-email-mock

# Expose service port
EXPOSE 8092

# Health check: the language's own command against the readiness route the
# language declares it mounts (supplied by TypeScriptRuntimeSpec.render_dockerfile).
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8092/ready || exit 1

# Switch to the non-root node user every Node.js image creates, by its uid:gid
USER 1000:1000

# Run the application
CMD ["node", "dist/main.js"]
