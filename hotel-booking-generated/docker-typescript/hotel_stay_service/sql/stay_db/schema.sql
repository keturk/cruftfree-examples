DO $$ BEGIN CREATE TYPE "room_condition" AS ENUM ('ready', 'dirty', 'out_of_service'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

DO $$ BEGIN CREATE TYPE "stay_status" AS ENUM ('held', 'confirmed', 'checked_in', 'checked_out', 'cancelled', 'expired'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "room_types" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "name" VARCHAR(80) NOT NULL,
    "summary" VARCHAR(200) NOT NULL,
    "description" TEXT NOT NULL,
    "sleeps" BIGINT NOT NULL,
    "nightly_rate" DECIMAL(19,4) NOT NULL,
    "inventory" BIGINT NOT NULL,
    "listed" BOOLEAN NOT NULL DEFAULT (TRUE),
    PRIMARY KEY ("id")
);

CREATE TABLE "rooms" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "number" VARCHAR(8) NOT NULL,
    "room_type_id" UUID NOT NULL,
    "room_type_name" VARCHAR(80) NOT NULL,
    "floor" BIGINT NOT NULL,
    "condition" "room_condition" NOT NULL DEFAULT ('ready'),
    PRIMARY KEY ("id")
);

CREATE TABLE "stays" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "code" VARCHAR(20) NOT NULL,
    "room_type_id" UUID NOT NULL,
    "room_type_name" VARCHAR(80) NOT NULL,
    "room_number" VARCHAR(8),
    "guest_id" VARCHAR(64) NOT NULL,
    "guest_name" VARCHAR(200) NOT NULL,
    "guest_email" VARCHAR(320) NOT NULL,
    "arrival" DATE NOT NULL,
    "departure" DATE NOT NULL,
    "nights" BIGINT NOT NULL,
    "guests" BIGINT NOT NULL,
    "total" DECIMAL(19,4) NOT NULL,
    "status" "stay_status" NOT NULL DEFAULT ('held'),
    "hold_until" TIMESTAMPTZ,
    "charge_id" VARCHAR(40),
    "desk_note" TEXT,
    PRIMARY KEY ("id")
);

ALTER TABLE "room_types" ADD CONSTRAINT "chk_room_types_name_15bf5bf0" CHECK ((char_length("name") <= 80));

ALTER TABLE "room_types" ADD CONSTRAINT "chk_room_types_summary_054d5d14" CHECK ((char_length("summary") <= 200));

ALTER TABLE "rooms" ADD CONSTRAINT "chk_rooms_number_15755fbb" CHECK ((char_length("number") <= 8));

ALTER TABLE "rooms" ADD CONSTRAINT "chk_rooms_room_type_name_e991403b" CHECK ((char_length("room_type_name") <= 80));

ALTER TABLE "stays" ADD CONSTRAINT "chk_stays_charge_id_fb5588e1" CHECK ((char_length("charge_id") <= 40));

ALTER TABLE "stays" ADD CONSTRAINT "chk_stays_code_767438d9" CHECK ((char_length("code") <= 20));

ALTER TABLE "stays" ADD CONSTRAINT "chk_stays_guest_id_12910600" CHECK ((char_length("guest_id") <= 64));

ALTER TABLE "stays" ADD CONSTRAINT "chk_stays_guest_name_a7284549" CHECK ((char_length("guest_name") <= 200));

ALTER TABLE "stays" ADD CONSTRAINT "chk_stays_room_number_dac31153" CHECK ((char_length("room_number") <= 8));

ALTER TABLE "stays" ADD CONSTRAINT "chk_stays_room_type_name_e991403b" CHECK ((char_length("room_type_name") <= 80));

ALTER TABLE "room_types" ADD CONSTRAINT "uq_room_types_name" UNIQUE ("name");

CREATE INDEX "ix_rooms_room_type_id" ON "rooms" ("room_type_id");

ALTER TABLE "rooms" ADD CONSTRAINT "uq_rooms_number" UNIQUE ("number");

CREATE INDEX "ix_stays_room_type_id_arrival_departure" ON "stays" ("room_type_id", "arrival", "departure");

CREATE INDEX "ix_stays_status_hold_until" ON "stays" ("status", "hold_until");

CREATE INDEX "ix_stays_room_type_id" ON "stays" ("room_type_id");

CREATE INDEX "ix_stays_guest_id" ON "stays" ("guest_id");

ALTER TABLE "stays" ADD CONSTRAINT "uq_stays_code" UNIQUE ("code");

COMMENT ON TABLE "room_types" IS 'What a guest chooses.';

COMMENT ON COLUMN "room_types"."inventory" IS 'How many rooms of this type can be sold. Taking one out of service does not change it.';

COMMENT ON TABLE "rooms" IS 'A door with a number. Only the desk thinks about these.';

COMMENT ON COLUMN "stays"."code" IS 'MH-402193. The code a guest reads out at the desk.';

COMMENT ON COLUMN "stays"."hold_until" IS 'A held room goes back on sale at this moment.';
