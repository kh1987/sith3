# Generated by Django 2.2.13 on 2020-08-28 19:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("subscription", "0012_auto_20200615_1438"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscription",
            name="subscription_type",
            field=models.CharField(
                choices=[
                    ("amicale/doceo", "Amicale/DOCEO member"),
                    ("assidu", "Assidu member"),
                    ("benevoles-euroks", "Eurok's volunteer"),
                    ("crous", "CROUS member"),
                    ("cursus-alternant", "Alternating cursus"),
                    ("cursus-alternant-reduction", "Alternating cursus (-20%)"),
                    ("cursus-branche", "Branch cursus"),
                    ("cursus-branche-reduction", "Branch cursus (-20%)"),
                    ("cursus-tronc-commun", "Common core cursus"),
                    ("cursus-tronc-commun-reduction", "Common core cursus (-20%)"),
                    ("deux-mois-essai", "Two months for free"),
                    ("deux-semestres", "Two semesters"),
                    ("deux-semestres-reduction", "Two semesters (-20%)"),
                    ("membre-honoraire", "Honorary member"),
                    ("membre-staff-ga", "GA staff member"),
                    ("reseau-ut", "UT network member"),
                    ("sbarro/esta", "Sbarro/ESTA member"),
                    ("six-semaines-essai", "Six weeks for free"),
                    ("un-jour", "One day"),
                    ("un-mois-essai", "One month for free"),
                    ("un-semestre", "One semester"),
                    ("un-semestre-reduction", "One semester (-20%)"),
                    ("un-semestre-welcome", "One semester Welcome Week"),
                ],
                max_length=255,
                verbose_name="subscription type",
            ),
        ),
    ]
