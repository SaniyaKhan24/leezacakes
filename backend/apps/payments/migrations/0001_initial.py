import apps.payments.models
import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orders', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('method', models.CharField(default='upi_qr', max_length=20)),
                ('status', models.CharField(choices=[('awaiting_payment', 'Awaiting payment'), ('pending_verification', 'Pending verification'), ('verified', 'Verified'), ('rejected', 'Rejected')], default='awaiting_payment', max_length=32)),
                ('amount_due', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('verified_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='payment', to='orders.order')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to=settings.AUTH_USER_MODEL)),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('verify_payment', 'Can verify payments'),),
            },
        ),
        migrations.CreateModel(
            name='PaymentSubmission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('evidence_file', models.FileField(storage=apps.payments.models.private_evidence_storage, upload_to=apps.payments.models.private_evidence_path)),
                ('original_filename', models.CharField(blank=True, max_length=255)),
                ('content_type', models.CharField(max_length=80)),
                ('file_size', models.PositiveBigIntegerField()),
                ('status', models.CharField(choices=[('pending_review', 'Pending review'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending_review', max_length=20)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.CharField(blank=True, max_length=500)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='submissions', to='payments.payment')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_payment_submissions', to=settings.AUTH_USER_MODEL)),
                ('submitted_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payment_submissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-submitted_at', 'id'),
            },
        ),
        migrations.CreateModel(
            name='PaymentStatusHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('from_status', models.CharField(blank=True, default='', max_length=32)),
                ('to_status', models.CharField(max_length=32)),
                ('reason', models.CharField(blank=True, max_length=500)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='status_history', to='payments.payment')),
                ('related_submission', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='payments.paymentsubmission')),
            ],
            options={
                'ordering': ('created_at', 'id'),
            },
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['status', 'created_at'], name='payments_pa_status_343680_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentsubmission',
            index=models.Index(fields=['payment', 'status', 'submitted_at'], name='payments_pa_payment_8b5b5b_idx'),
        ),
    ]
