DO $$ BEGIN CREATE TYPE "ticket_topic" AS ENUM ('billing', 'domains', 'email', 'websites'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "articles" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "title" VARCHAR(160) NOT NULL,
    "summary" VARCHAR(300) NOT NULL,
    "body" TEXT NOT NULL,
    "topic" "ticket_topic" NOT NULL,
    "published" BOOLEAN NOT NULL DEFAULT (FALSE),
    "helpful" BIGINT NOT NULL DEFAULT (0),
    "not_helpful" BIGINT NOT NULL DEFAULT (0),
    PRIMARY KEY ("id")
);

ALTER TABLE "articles" ADD CONSTRAINT "chk_articles_summary_5589c545" CHECK ((char_length("summary") <= 300));

ALTER TABLE "articles" ADD CONSTRAINT "chk_articles_title_5cd37c82" CHECK ((char_length("title") <= 160));

CREATE INDEX "ix_articles_fulltext" ON "articles" USING GIN (to_tsvector('english', coalesce("title", '') || ' ' || coalesce("summary", '') || ' ' || coalesce("body", '')));
