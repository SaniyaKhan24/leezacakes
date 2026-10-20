import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('catalog', '0001_initial'),
        ('customization', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('order_number', models.CharField(editable=False, max_length=32, unique=True)),
                ('status', models.CharField(choices=[('pending_payment_verification', 'Pending payment verification'), ('confirmed', 'Confirmed'), ('preparing', 'Preparing'), ('ready_for_pickup', 'Ready for pickup'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending_payment_verification', max_length=32)),
                ('payment_status', models.CharField(choices=[('pending_verification', 'Pending verification'), ('verified', 'Verified')], default='pending_verification', max_length=24)),
                ('customer_name', models.CharField(max_length=160)),
                ('customer_phone', models.CharField(max_length=32)),
                ('customer_email', models.EmailField(blank=True, default='', max_length=254)),
                ('pickup_slot_start', models.DateTimeField()),
                ('pickup_slot_end', models.DateTimeField()),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('discount_total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('tax_total', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('grand_total', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('customer_note', models.TextField(blank=True)),
                ('idempotency_key', models.CharField(max_length=128)),
                ('request_fingerprint', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at', 'id'),
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('product_name_snapshot', models.CharField(max_length=180)),
                ('variant_name_snapshot', models.CharField(blank=True, max_length=120)),
                ('sku_snapshot', models.CharField(blank=True, max_length=80)),
                ('quantity', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('unit_base_price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('unit_customization_total', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('line_total', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='catalog.product')),
                ('variant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='catalog.productvariant')),
            ],
        ),
        migrations.CreateModel(
            name='OrderItemCustomization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('option_name_snapshot', models.CharField(max_length=120)),
                ('choice_name_snapshot', models.CharField(blank=True, max_length=120)),
                ('value_snapshot', models.CharField(blank=True, max_length=80)),
                ('price_adjustment', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('choice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='customization.customizationchoice')),
                ('option', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='customization.customizationoption')),
                ('order_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='customizations', to='orders.orderitem')),
            ],
        ),
        migrations.CreateModel(
            name='OrderStatusHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('from_status', models.CharField(blank=True, default='', max_length=32)),
                ('to_status', models.CharField(max_length=32)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='orders.order')),
            ],
            options={
                'ordering': ('created_at', 'id'),
            },
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user', 'created_at'], name='orders_orde_user_id_37fed6_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status', 'pickup_slot_start'], name='orders_orde_status_d9b95f_idx'),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.UniqueConstraint(fields=('user', 'idempotency_key'), name='unique_order_idempotency_per_user'),
        ),
    ]
