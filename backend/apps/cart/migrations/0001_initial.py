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
            name='Cart',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('session_key', models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('converted', 'Converted')], default='active', max_length=16)),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='carts', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CartItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('quantity', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)])),
                ('acknowledged_unit_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='cart.cart')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cart_items', to='catalog.product')),
                ('variant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='cart_items', to='catalog.productvariant')),
            ],
        ),
        migrations.CreateModel(
            name='CartItemCustomization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('text_value', models.CharField(blank=True, max_length=80)),
                ('price_adjustment', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cart_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='customizations', to='cart.cartitem')),
                ('choice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='customization.customizationchoice')),
                ('option', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='customization.customizationoption')),
            ],
        ),
        migrations.AddIndex(
            model_name='cart',
            index=models.Index(fields=['status', 'updated_at'], name='cart_cart_status_39ba2f_idx'),
        ),
        migrations.AddConstraint(
            model_name='cart',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'active'), ('user__isnull', False)), fields=('user',), name='one_active_cart_per_user'),
        ),
        migrations.AddIndex(
            model_name='cartitem',
            index=models.Index(fields=['cart', 'product', 'variant'], name='cart_cartit_cart_id_bddf3b_idx'),
        ),
        migrations.AddConstraint(
            model_name='cartitemcustomization',
            constraint=models.UniqueConstraint(fields=('cart_item', 'option', 'choice', 'text_value'), name='unique_cart_selection'),
        ),
    ]
