"""expand siarp schema

Revision ID: 7f4d4c6f1a22
Revises: 2d3f62138b11
Create Date: 2026-07-13 23:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7f4d4c6f1a22"
down_revision: Union[str, Sequence[str], None] = "2d3f62138b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


recordstatusenum = postgresql.ENUM("ACTIVE", "INACTIVE", name="recordstatusenum")
authroleenum = postgresql.ENUM("ADMIN", "OPERATOR", name="authroleenum")
vehicletypeenum = postgresql.ENUM("CAR", "MOTORCYCLE", "VAN", "TRUCK", "OTHER", name="vehicletypeenum")
scanstatusenum = postgresql.ENUM("DETECTED", "LOW_CONFIDENCE", "ERROR", "MANUAL", name="scanstatusenum")
notificationtypeenum = postgresql.ENUM("INFO", "WARNING", "ALERT", name="notificationtypeenum")
recordstatusenum_existing = postgresql.ENUM("ACTIVE", "INACTIVE", name="recordstatusenum", create_type=False)
authroleenum_existing = postgresql.ENUM("ADMIN", "OPERATOR", name="authroleenum", create_type=False)
vehicletypeenum_existing = postgresql.ENUM("CAR", "MOTORCYCLE", "VAN", "TRUCK", "OTHER", name="vehicletypeenum", create_type=False)
scanstatusenum_existing = postgresql.ENUM("DETECTED", "LOW_CONFIDENCE", "ERROR", "MANUAL", name="scanstatusenum", create_type=False)
notificationtypeenum_existing = postgresql.ENUM("INFO", "WARNING", "ALERT", name="notificationtypeenum", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    recordstatusenum.create(bind, checkfirst=True)
    authroleenum.create(bind, checkfirst=True)
    vehicletypeenum.create(bind, checkfirst=True)
    scanstatusenum.create(bind, checkfirst=True)
    notificationtypeenum.create(bind, checkfirst=True)

    op.add_column("university_persons", sa.Column("document_id", sa.String(), nullable=True))
    op.add_column("university_persons", sa.Column("faculty", sa.String(), nullable=True))
    op.add_column("university_persons", sa.Column("contact_info", sa.String(), nullable=True))
    op.add_column("university_persons", sa.Column("status", recordstatusenum_existing, nullable=False, server_default="ACTIVE"))
    op.add_column("university_persons", sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.add_column("university_persons", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

    op.add_column("auth_users", sa.Column("role", authroleenum_existing, nullable=False, server_default="OPERATOR"))
    op.add_column("auth_users", sa.Column("status", recordstatusenum_existing, nullable=False, server_default="ACTIVE"))
    op.add_column("auth_users", sa.Column("university_person_id", sa.Uuid(), nullable=True))
    op.add_column("auth_users", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_foreign_key(
        "fk_auth_users_university_person_id",
        "auth_users",
        "university_persons",
        ["university_person_id"],
        ["id"],
    )

    op.add_column("vehicles", sa.Column("brand", sa.String(), nullable=True))
    op.add_column("vehicles", sa.Column("model", sa.String(), nullable=True))
    op.add_column("vehicles", sa.Column("color", sa.String(), nullable=True))
    op.add_column("vehicles", sa.Column("vehicle_photo_path", sa.String(), nullable=True))
    op.add_column("vehicles", sa.Column("vehicle_type", vehicletypeenum_existing, nullable=False, server_default="CAR"))
    op.add_column("vehicles", sa.Column("year", sa.String(), nullable=True))
    op.add_column("vehicles", sa.Column("observation", sa.Text(), nullable=True))
    op.add_column("vehicles", sa.Column("status", recordstatusenum_existing, nullable=False, server_default="ACTIVE"))
    op.add_column("vehicles", sa.Column("registered_by_user_id", sa.Uuid(), nullable=True))
    op.add_column("vehicles", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_foreign_key(
        "fk_vehicles_registered_by_user_id",
        "vehicles",
        "auth_users",
        ["registered_by_user_id"],
        ["id"],
    )

    op.execute("UPDATE vehicles SET brand = 'Sin especificar' WHERE brand IS NULL")
    op.execute("UPDATE vehicles SET model = 'Sin especificar' WHERE model IS NULL")
    op.execute("UPDATE vehicles SET color = 'Sin especificar' WHERE color IS NULL")
    op.alter_column("vehicles", "brand", nullable=False)
    op.alter_column("vehicles", "model", nullable=False)
    op.alter_column("vehicles", "color", nullable=False)

    op.create_table(
        "plate_scans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("image_path", sa.String(), nullable=True),
        sa.Column("detected_plate", sa.String(), nullable=True),
        sa.Column("normalized_plate", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("scan_status", scanstatusenum_existing, nullable=False),
        sa.Column("manual_correction", sa.String(), nullable=True),
        sa.Column("vehicle_id", sa.Uuid(), nullable=True),
        sa.Column("scanned_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["scanned_by_user_id"], ["auth_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title_message", sa.String(), nullable=False),
        sa.Column("notification_type", notificationtypeenum_existing, nullable=False, server_default="INFO"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("plate_scan_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"]),
        sa.ForeignKeyConstraint(["plate_scan_id"], ["plate_scans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("plate_scans")
    op.drop_constraint("fk_vehicles_registered_by_user_id", "vehicles", type_="foreignkey")
    op.drop_column("vehicles", "updated_at")
    op.drop_column("vehicles", "registered_by_user_id")
    op.drop_column("vehicles", "status")
    op.drop_column("vehicles", "observation")
    op.drop_column("vehicles", "year")
    op.drop_column("vehicles", "vehicle_type")
    op.drop_column("vehicles", "vehicle_photo_path")
    op.drop_column("vehicles", "color")
    op.drop_column("vehicles", "model")
    op.drop_column("vehicles", "brand")
    op.drop_constraint("fk_auth_users_university_person_id", "auth_users", type_="foreignkey")
    op.drop_column("auth_users", "updated_at")
    op.drop_column("auth_users", "university_person_id")
    op.drop_column("auth_users", "status")
    op.drop_column("auth_users", "role")
    op.drop_column("university_persons", "updated_at")
    op.drop_column("university_persons", "created_at")
    op.drop_column("university_persons", "status")
    op.drop_column("university_persons", "contact_info")
    op.drop_column("university_persons", "faculty")
    op.drop_column("university_persons", "document_id")

    bind = op.get_bind()
    notificationtypeenum.drop(bind, checkfirst=True)
    scanstatusenum.drop(bind, checkfirst=True)
    vehicletypeenum.drop(bind, checkfirst=True)
    authroleenum.drop(bind, checkfirst=True)
    recordstatusenum.drop(bind, checkfirst=True)
