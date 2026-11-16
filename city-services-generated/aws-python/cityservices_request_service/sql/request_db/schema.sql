DO $$ BEGIN CREATE TYPE "request_category" AS ENUM ('pothole', 'streetlight', 'graffiti', 'flooding', 'fallen_tree', 'other'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

DO $$ BEGIN CREATE TYPE "request_priority" AS ENUM ('low', 'medium', 'high', 'critical'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

DO $$ BEGIN CREATE TYPE "request_status" AS ENUM ('open', 'assigned', 'in_progress', 'resolved', 'closed'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "service_requests" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "request_number" VARCHAR(30) NOT NULL,
    "title" VARCHAR(200) NOT NULL,
    "description" TEXT NOT NULL,
    "category" "request_category" NOT NULL,
    "priority" "request_priority" NOT NULL DEFAULT ('medium'),
    "status" "request_status" NOT NULL DEFAULT ('open'),
    "address" VARCHAR(300) NOT NULL,
    "latitude" DOUBLE PRECISION,
    "longitude" DOUBLE PRECISION,
    "location" geometry(Geometry,4326),
    "district_id" UUID,
    "district_name" VARCHAR(200),
    "reporter_phone" VARCHAR(20),
    PRIMARY KEY ("id")
);

CREATE TABLE "request_updates" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "request_id" UUID NOT NULL,
    "status" "request_status" NOT NULL,
    "note" VARCHAR(500) NOT NULL,
    PRIMARY KEY ("id")
);

ALTER TABLE "service_requests" ADD CONSTRAINT "chk_service_requests_address_c06df1d3" CHECK ((char_length("address") <= 300));

ALTER TABLE "service_requests" ADD CONSTRAINT "chk_service_requests_district_name_028cf7ec" CHECK ((char_length("district_name") <= 200));

ALTER TABLE "service_requests" ADD CONSTRAINT "chk_service_requests_request_number_3f671ce1" CHECK ((char_length("request_number") <= 30));

ALTER TABLE "service_requests" ADD CONSTRAINT "chk_service_requests_title_fa0e1671" CHECK ((char_length("title") <= 200));

ALTER TABLE "request_updates" ADD CONSTRAINT "chk_request_updates_note_db49f8ea" CHECK ((char_length("note") <= 500));

CREATE INDEX "ix_service_requests_status_priority" ON "service_requests" ("status", "priority");

CREATE INDEX "ix_service_requests_fulltext" ON "service_requests" USING GIN (to_tsvector('english', coalesce("title", '') || ' ' || coalesce("description", '')));

CREATE INDEX "ix_service_requests_district_id" ON "service_requests" ("district_id");

CREATE INDEX "gist_service_requests_location" ON "service_requests" USING GIST ("location");

ALTER TABLE "service_requests" ADD CONSTRAINT "uq_service_requests_request_number" UNIQUE ("request_number");

CREATE INDEX "ix_request_updates_request_id" ON "request_updates" ("request_id");

COMMENT ON COLUMN "service_requests"."reporter_phone" IS 'For status texts only; never in an answer.';

COMMENT ON TABLE "request_updates" IS 'What happened to a request, in order. The table refuses every change and delete.';

CREATE FUNCTION "trg_request_updates_append_only_7f0f83c3"() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP = 'UPDATE' THEN IF (to_jsonb(NEW) - CAST(ARRAY['updated_at'] AS text[])) = (to_jsonb(OLD) - CAST(ARRAY['updated_at'] AS text[])) THEN RETURN NEW; END IF; END IF; RAISE EXCEPTION USING MESSAGE = 'table ' || TG_TABLE_NAME || ' is append-only: ' || TG_OP || ' is refused', ERRCODE = 'restrict_violation'; END $$;

CREATE TRIGGER "trg_request_updates_append_only_7f0f83c3" BEFORE UPDATE OR DELETE ON "request_updates" FOR EACH ROW EXECUTE FUNCTION "trg_request_updates_append_only_7f0f83c3"();

CREATE TRIGGER "trg_request_updates_append_only_7f0f83c3_truncate" BEFORE TRUNCATE ON "request_updates" FOR EACH STATEMENT EXECUTE FUNCTION "trg_request_updates_append_only_7f0f83c3"();
