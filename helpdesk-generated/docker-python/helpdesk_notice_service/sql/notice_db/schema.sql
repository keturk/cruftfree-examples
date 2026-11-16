CREATE TABLE "notices" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "recipient" VARCHAR(200) NOT NULL,
    "subject" VARCHAR(200) NOT NULL,
    "body" VARCHAR(2000) NOT NULL,
    "delivered" BOOLEAN NOT NULL DEFAULT (FALSE),
    "attempts" BIGINT NOT NULL DEFAULT (0),
    "notice_key" VARCHAR(120) NOT NULL,
    PRIMARY KEY ("id")
);

ALTER TABLE "notices" ADD CONSTRAINT "chk_notices_body_5154484f" CHECK ((char_length("body") <= 2000));

ALTER TABLE "notices" ADD CONSTRAINT "chk_notices_notice_key_74b0648a" CHECK ((char_length("notice_key") <= 120));

ALTER TABLE "notices" ADD CONSTRAINT "chk_notices_recipient_118cdbab" CHECK ((char_length("recipient") <= 200));

ALTER TABLE "notices" ADD CONSTRAINT "chk_notices_subject_6afca0bc" CHECK ((char_length("subject") <= 200));

CREATE INDEX "ix_notices_delivered" ON "notices" ("delivered");

ALTER TABLE "notices" ADD CONSTRAINT "uq_notices_notice_key" UNIQUE ("notice_key");
