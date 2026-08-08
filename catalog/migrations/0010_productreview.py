from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0009_product_minimum_wholesale_quantity"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []

