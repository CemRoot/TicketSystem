from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ticket_system', '0002_update_aianalysis_fields'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL - Apply changes
            """
            -- First, check if confidence_score column exists
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'ticket_system_aianalysis' AND column_name = 'confidence_score'
                ) THEN
                    -- Add confidence_score column
                    ALTER TABLE ticket_system_aianalysis ADD COLUMN confidence_score double precision NULL;
                END IF;
            END
            $$;

            -- Check if suggested_staff column exists
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'ticket_system_aianalysis' AND column_name = 'suggested_staff'
                ) THEN
                    -- Add suggested_staff column
                    ALTER TABLE ticket_system_aianalysis ADD COLUMN suggested_staff varchar(100) NULL;
                END IF;
            END
            $$;

            -- Convert processing_time to double precision if it's not already
            DO $$
            DECLARE
                col_type text;
            BEGIN
                -- Get the current column type
                SELECT data_type INTO col_type 
                FROM information_schema.columns 
                WHERE table_name = 'ticket_system_aianalysis' AND column_name = 'processing_time';
                
                -- Only convert if it's not already double precision
                IF col_type != 'double precision' THEN
                    -- First set to NULL temporarily to avoid cast errors
                    UPDATE ticket_system_aianalysis SET processing_time = NULL;
                    
                    -- Change the column type
                    ALTER TABLE ticket_system_aianalysis 
                    ALTER COLUMN processing_time TYPE double precision USING NULL;
                END IF;
            END
            $$;
            """,
            
            # Reverse SQL - If migration is reversed
            """
            -- No reverse migration provided since we're fixing schema issues
            """
        ),
    ]
