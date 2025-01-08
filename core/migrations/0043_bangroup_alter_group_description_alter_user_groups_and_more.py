# Generated by Django 4.2.17 on 2024-12-31 13:30

import django.contrib.auth.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.migrations.state import StateApps


def migrate_ban_groups(apps: StateApps, schema_editor):
    Group = apps.get_model("core", "Group")
    BanGroup = apps.get_model("core", "BanGroup")
    ban_group_ids = [
        settings.SITH_GROUP_BANNED_ALCOHOL_ID,
        settings.SITH_GROUP_BANNED_COUNTER_ID,
        settings.SITH_GROUP_BANNED_SUBSCRIPTION_ID,
    ]
    # this is a N+1 Queries, but the prod database has a grand total of 3 ban groups
    for group in Group.objects.filter(id__in=ban_group_ids):
        # auth_group, which both Group and BanGroup inherit,
        # is unique by name.
        # If we tried give the exact same name to the migrated BanGroup
        # before deleting the corresponding Group,
        # we would have an IntegrityError.
        # So we append a space to the name, in order to create a name
        # that will look the same, but that isn't really the same.
        ban_group = BanGroup.objects.create(
            name=f"{group.name} ",
            description=group.description,
        )
        perms = list(group.permissions.values_list("id", flat=True))
        if perms:
            ban_group.permissions.add(*perms)
        ban_group.users.add(
            *group.users.values_list("id", flat=True), through_defaults={"reason": ""}
        )
        group.delete()
        # now that the original group is no longer there,
        # we can remove the appended space
        ban_group.name = ban_group.name.strip()
        ban_group.save()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0042_invert_is_manually_manageable_20250104_1742"),
    ]

    operations = [
        migrations.CreateModel(
            name="BanGroup",
            fields=[
                (
                    "group_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="auth.group",
                    ),
                ),
                ("description", models.TextField(verbose_name="description")),
            ],
            bases=("auth.group",),
            managers=[
                ("objects", django.contrib.auth.models.GroupManager()),
            ],
            options={
                "verbose_name": "ban group",
                "verbose_name_plural": "ban groups",
            },
        ),
        migrations.AlterField(
            model_name="group",
            name="description",
            field=models.TextField(verbose_name="description"),
        ),
        migrations.AlterField(
            model_name="user",
            name="groups",
            field=models.ManyToManyField(
                help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                related_name="users",
                to="core.group",
                verbose_name="groups",
            ),
        ),
        migrations.CreateModel(
            name="UserBan",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="created at"),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the ban should be removed. Currently, there is no automatic removal, so this is purely indicative. Automatic ban removal may be implemented later on.",
                        null=True,
                        verbose_name="expires at",
                    ),
                ),
                ("reason", models.TextField(verbose_name="reason")),
                (
                    "ban_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_bans",
                        to="core.bangroup",
                        verbose_name="ban type",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bans",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="user",
            name="ban_groups",
            field=models.ManyToManyField(
                help_text="The bans this user has received.",
                related_name="users",
                through="core.UserBan",
                to="core.bangroup",
                verbose_name="ban groups",
            ),
        ),
        migrations.AddConstraint(
            model_name="userban",
            constraint=models.UniqueConstraint(
                fields=("ban_group", "user"), name="unique_ban_type_per_user"
            ),
        ),
        migrations.AddConstraint(
            model_name="userban",
            constraint=models.CheckConstraint(
                check=models.Q(("expires_at__gte", models.F("created_at"))),
                name="user_ban_end_after_start",
            ),
        ),
        migrations.RunPython(
            migrate_ban_groups, reverse_code=migrations.RunPython.noop, elidable=True
        ),
    ]