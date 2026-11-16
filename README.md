# cruftfree-examples

Showcase examples for CruftFree, a generator that turns `.cfree` application specs into complete, runnable projects: backend services, web and mobile clients, database schemas, tests and deployment for Docker, AWS and Azure.

## Layout

| Folder | Holds |
|---|---|
| `<domain>/` | The specification: `.cfree` files and their `.ccfg` configuration profiles. |
| `<domain>-generated/docker-<language>/` | Generated from the `test` profile: a local docker-compose stack. |
| `<domain>-generated/aws-<language>/` or `azure-<language>/` | Generated from the `development` profile (alias `dev`): cloud infrastructure and services. |
| `scripts/git/` | Commit-and-push and pull scripts for this repository, see [scripts/git/README.md](scripts/git/README.md). |

`<language>` is `python` or `typescript`. The fifteen domains are blog-cms, city-services, ecommerce, finance, food-delivery, healthcare, helpdesk and learning-management (Python), and hotel-booking, hr-platform, iot-platform, logistics, real-estate, social-platform and task-management (TypeScript).

Secrets, environment files, dependency folders and machine-local build files are not part of the repository.
