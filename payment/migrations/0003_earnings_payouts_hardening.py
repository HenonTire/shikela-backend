# Generated for earnings and payouts hardening.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.query_utils


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0002_webhooklog_idempotency"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="payoutrequest",
            name="idempotency_key",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name="earning",
            name="status",
            field=models.CharField(
                choices=[
                    ("AVAILABLE", "Available"),
                    ("PENDING_PAYOUT", "Pending Payout"),
                    ("PAID_OUT", "Paid Out"),
                ],
                default="AVAILABLE",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="earning",
            index=models.Index(fields=["user", "status"], name="payment_ear_user_id_c4f24a_idx"),
        ),
        migrations.AddIndex(
            model_name="payoutrequest",
            index=models.Index(fields=["user", "status"], name="payment_pay_user_id_e1993b_idx"),
        ),
        migrations.AddConstraint(
            model_name="payoutrequest",
            constraint=models.UniqueConstraint(
                condition=django.db.models.query_utils.Q(("idempotency_key__isnull", False)),
                fields=("user", "idempotency_key"),
                name="uniq_payout_user_idempotency_key",
            ),
        ),
    ]
