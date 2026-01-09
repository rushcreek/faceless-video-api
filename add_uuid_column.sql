ALTER TABLE images ADD COLUMN IF NOT EXISTS runware_image_uuid VARCHAR(255);
CREATE INDEX IF NOT EXISTS idx_images_runware_image_uuid ON images (runware_image_uuid);
