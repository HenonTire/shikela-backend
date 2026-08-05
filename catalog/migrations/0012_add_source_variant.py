# Generated migration to add source_variant FK to ProductVariant
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0011_rename_catalog_pro_product_cccc4c_idx_catalog_pro_product_adc547_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariant',
            name='source_variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='imported_variants', to='catalog.productvariant'),
        ),
    ]
