-- Migration: Add height column to patients table
-- Date: 2026-02-06
-- Description: Adds height field (in cm) to store patient height measurements

ALTER TABLE patients ADD COLUMN IF NOT EXISTS height FLOAT;

-- Optional: Add a comment to document the column
COMMENT ON COLUMN patients.height IS 'Patient height in centimeters';
