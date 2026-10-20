import apps.catalog.models
import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(max_length=140, unique=True)),
                ('description', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='catalog/categories/')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='catalog.category')),
            ],
            options={
                'ordering': ('sort_order', 'name', 'id'),
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=180)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('description', models.TextField()),
                ('short_description', models.CharField(blank=True, max_length=320)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published'), ('archived', 'Archived')], default='draft', max_length=16)),
                ('is_available', models.BooleanField(default=True)),
                ('is_featured', models.BooleanField(default=False)),
                ('base_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('weight_description', models.CharField(blank=True, max_length=80)),
                ('preparation_time', models.PositiveIntegerField(blank=True, help_text='Preparation time in minutes', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='catalog.category')),
            ],
            options={
                'ordering': ('-created_at', 'id'),
            },
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('image', models.ImageField(upload_to='catalog/products/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), apps.catalog.models.validate_image_size])),
                ('alt_text', models.CharField(max_length=240)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_primary', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='images', to='catalog.product')),
            ],
            options={
                'ordering': ('sort_order', 'created_at', 'id'),
            },
        ),
        migrations.CreateModel(
            name='ProductVariant',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120)),
                ('sku', models.CharField(blank=True, max_length=80, null=True, unique=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='variants', to='catalog.product')),
            ],
            options={
                'ordering': ('sort_order', 'price', 'id'),
            },
        ),
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['is_active', 'sort_order'], name='catalog_cat_is_acti_100145_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['status', 'is_available'], name='catalog_pro_status_10550e_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', 'status'], name='catalog_pro_categor_da0f0a_idx'),
        ),
        migrations.AddConstraint(
            model_name='productimage',
            constraint=models.UniqueConstraint(condition=models.Q(('is_primary', True)), fields=('product',), name='one_primary_image_per_product'),
        ),
        migrations.AddConstraint(
            model_name='productvariant',
            constraint=models.UniqueConstraint(fields=('product', 'name'), name='unique_variant_name_per_product'),
        ),
    ]
