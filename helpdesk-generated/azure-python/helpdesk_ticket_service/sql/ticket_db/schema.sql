DO $$ BEGIN CREATE TYPE "priority" AS ENUM ('low', 'normal', 'high', 'urgent'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

DO $$ BEGIN CREATE TYPE "ticket_status" AS ENUM ('new', 'open', 'waiting', 'resolved', 'closed'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

DO $$ BEGIN CREATE TYPE "ticket_topic" AS ENUM ('billing', 'domains', 'email', 'websites'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "tickets" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "number" VARCHAR(20) NOT NULL,
    "subject" VARCHAR(200) NOT NULL,
    "topic" "ticket_topic" NOT NULL,
    "priority" "priority" NOT NULL DEFAULT ('normal'),
    "status" "ticket_status" NOT NULL DEFAULT ('new'),
    "customer_id" VARCHAR(64) NOT NULL,
    "customer_name" VARCHAR(200) NOT NULL,
    "customer_email" VARCHAR(320) NOT NULL,
    "assignee_id" VARCHAR(64),
    "assignee_name" VARCHAR(200),
    "respond_by" TIMESTAMPTZ NOT NULL,
    "first_replied_at" TIMESTAMPTZ,
    "resolved_at" TIMESTAMPTZ,
    "breached" BOOLEAN NOT NULL DEFAULT (FALSE),
    "satisfaction" BIGINT,
    PRIMARY KEY ("id")
);

CREATE TABLE "ticket_messages" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "ticket_id" UUID NOT NULL,
    "author_name" VARCHAR(200) NOT NULL,
    "from_customer" BOOLEAN NOT NULL DEFAULT (FALSE),
    "internal" BOOLEAN NOT NULL DEFAULT (FALSE),
    "body" TEXT NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE "response_policies" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "priority" "priority" NOT NULL,
    "minutes" BIGINT NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE "saved_replies" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "title" VARCHAR(120) NOT NULL,
    "body" TEXT NOT NULL,
    PRIMARY KEY ("id")
);

ALTER TABLE "tickets" ADD CONSTRAINT "chk_tickets_assignee_id_303a4d35" CHECK ((char_length("assignee_id") <= 64));

ALTER TABLE "tickets" ADD CONSTRAINT "chk_tickets_assignee_name_f25b5893" CHECK ((char_length("assignee_name") <= 200));

ALTER TABLE "tickets" ADD CONSTRAINT "chk_tickets_customer_id_5248d1ea" CHECK ((char_length("customer_id") <= 64));

ALTER TABLE "tickets" ADD CONSTRAINT "chk_tickets_customer_name_7108af70" CHECK ((char_length("customer_name") <= 200));

ALTER TABLE "tickets" ADD CONSTRAINT "chk_tickets_number_c3daa055" CHECK ((char_length("number") <= 20));

ALTER TABLE "tickets" ADD CONSTRAINT "chk_tickets_subject_6afca0bc" CHECK ((char_length("subject") <= 200));

ALTER TABLE "ticket_messages" ADD CONSTRAINT "chk_ticket_messages_author_name_9d7b5c6d" CHECK ((char_length("author_name") <= 200));

ALTER TABLE "saved_replies" ADD CONSTRAINT "chk_saved_replies_title_2a4d74da" CHECK ((char_length("title") <= 120));

CREATE INDEX "ix_tickets_status_respond_by" ON "tickets" ("status", "respond_by");

CREATE INDEX "ix_tickets_customer_id" ON "tickets" ("customer_id");

CREATE INDEX "ix_tickets_assignee_id" ON "tickets" ("assignee_id");

ALTER TABLE "tickets" ADD CONSTRAINT "uq_tickets_number" UNIQUE ("number");

CREATE INDEX "ix_ticket_messages_ticket_id" ON "ticket_messages" ("ticket_id");

ALTER TABLE "response_policies" ADD CONSTRAINT "uq_response_policies_priority" UNIQUE ("priority");

COMMENT ON COLUMN "tickets"."number" IS 'LP-402193. The number people say out loud.';

COMMENT ON COLUMN "tickets"."respond_by" IS 'When a first answer is due. The clock stops at the first reply.';

COMMENT ON COLUMN "tickets"."satisfaction" IS 'The customer''s score from 1 to 5, once it is resolved.';

COMMENT ON TABLE "ticket_messages" IS 'One thing said on a ticket. Never changed afterwards: what was said stays said.';

COMMENT ON COLUMN "ticket_messages"."internal" IS 'Seen by agents only.';

COMMENT ON TABLE "response_policies" IS 'How long each priority may wait for a first answer.';

COMMENT ON TABLE "saved_replies" IS 'An answer agents send often, editable in the Console.';

CREATE FUNCTION "trg_ticket_messages_append_only_7f0f83c3"() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP = 'UPDATE' THEN IF (to_jsonb(NEW) - CAST(ARRAY['updated_at'] AS text[])) = (to_jsonb(OLD) - CAST(ARRAY['updated_at'] AS text[])) THEN RETURN NEW; END IF; END IF; RAISE EXCEPTION USING MESSAGE = 'table ' || TG_TABLE_NAME || ' is append-only: ' || TG_OP || ' is refused', ERRCODE = 'restrict_violation'; END $$;

CREATE TRIGGER "trg_ticket_messages_append_only_7f0f83c3" BEFORE UPDATE OR DELETE ON "ticket_messages" FOR EACH ROW EXECUTE FUNCTION "trg_ticket_messages_append_only_7f0f83c3"();

CREATE TRIGGER "trg_ticket_messages_append_only_7f0f83c3_truncate" BEFORE TRUNCATE ON "ticket_messages" FOR EACH STATEMENT EXECUTE FUNCTION "trg_ticket_messages_append_only_7f0f83c3"();
