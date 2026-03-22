from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0012_encode_existing_merchant_ids"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="merchant_id",
        ),
    ]

