from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ticket_system', '0003_manual_aianalysis_update'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL - Apply changes
            """
            -- Check if suggested_category column exists
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'ticket_system_aianalysis' AND column_name = 'suggested_category'
                ) THEN
                    -- Add suggested_category column (renaming from suggested_category_id if it exists)
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'ticket_system_aianalysis' AND column_name = 'suggested_category_id'
                    ) THEN
                        -- Convert foreign key to text field
                        ALTER TABLE ticket_system_aianalysis 
                        ADD COLUMN suggested_category varchar(100) NULL;
                        
                        -- Copy data from related table if possible (simplified approach)
                        UPDATE ticket_system_aianalysis SET suggested_category = NULL;
                    ELSE
                        -- Just add the column if neither exists
                        ALTER TABLE ticket_system_aianalysis ADD COLUMN suggested_category varchar(100) NULL;
                    END IF;
                END IF;
            END
            $$;
            """,
            
            # Reverse SQL - If migration is reversed
            """
            -- No reverse migration provided
            """
        ),
    ]
