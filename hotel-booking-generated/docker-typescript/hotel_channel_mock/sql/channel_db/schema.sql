CREATE TABLE "published_nights" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "room_type" VARCHAR(80) NOT NULL,
    "night" DATE NOT NULL,
    "left" BIGINT NOT NULL,
    "nightly_rate" DECIMAL(19,4) NOT NULL,
    "received_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE "api_keys" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "key_hash" VARCHAR(64) NOT NULL,
    "owner_id" UUID NOT NULL,
    "scopes" JSONB NOT NULL DEFAULT '[]',
    "is_active" BOOLEAN NOT NULL DEFAULT (TRUE),
    "expires_at" TIMESTAMPTZ,
    "last_used_at" TIMESTAMPTZ,
    PRIMARY KEY ("id")
);

ALTER TABLE "published_nights" ADD CONSTRAINT "chk_published_nights_room_type_64d3c952" CHECK ((char_length("room_type") <= 80));

ALTER TABLE "api_keys" ADD CONSTRAINT "chk_api_keys_key_hash_455a30f8" CHECK ((char_length("key_hash") <= 64));

ALTER TABLE "published_nights" ADD CONSTRAINT "uq_published_nights_room_type_night" UNIQUE ("room_type", "night");

CREATE INDEX "ix_api_keys_owner_id" ON "api_keys" ("owner_id");

ALTER TABLE "api_keys" ADD CONSTRAINT "uq_api_keys_key_hash" UNIQUE ("key_hash");

COMMENT ON TABLE "published_nights" IS 'What the travel sites currently believe about one room type on one night.';

COMMENT ON TABLE "api_keys" IS 'API keys the vendor issued. Only the SHA-256 hash of a key is stored.';
