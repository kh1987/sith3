# Generated by Django 4.2.16 on 2024-09-26 10:28

import phonenumber_field.modelfields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("counter", "0022_alter_product_icon"),
    ]

    operations = [
        migrations.AddField(
            model_name="billinginfo",
            name="phone_number",
            field=phonenumber_field.modelfields.PhoneNumberField(
                max_length=128, null=True, region=None, verbose_name="Phone number"
            ),
        ),
    ]