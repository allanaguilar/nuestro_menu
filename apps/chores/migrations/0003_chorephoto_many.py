from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("chores", "0002_chorephoto"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="ChorePhoto"),
                migrations.CreateModel(
                    name="ChorePhoto",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        ("content", models.BinaryField()),
                        (
                            "content_type",
                            models.CharField(default="image/jpeg", max_length=40),
                        ),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "chore",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="photos",
                                to="chores.chore",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "foto de la tarea",
                        "verbose_name_plural": "fotos de las tareas",
                        "ordering": ["created_at"],
                    },
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE chores_chorephoto_many (
                            id uuid PRIMARY KEY,
                            content bytea NOT NULL,
                            content_type varchar(40) NOT NULL,
                            created_at timestamp with time zone NOT NULL,
                            chore_id uuid NOT NULL REFERENCES chores_chore(id) ON DELETE CASCADE
                        );
                        INSERT INTO chores_chorephoto_many (id, content, content_type, created_at, chore_id)
                        SELECT gen_random_uuid(), content, content_type, updated_at, chore_id
                        FROM chores_chorephoto;
                        DROP TABLE chores_chorephoto;
                        ALTER TABLE chores_chorephoto_many RENAME TO chores_chorephoto;
                        CREATE INDEX chores_chorephoto_chore_id_idx ON chores_chorephoto (chore_id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
