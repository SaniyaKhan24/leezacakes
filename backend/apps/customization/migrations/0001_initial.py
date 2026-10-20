import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomizationOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(max_length=140, unique=True)),
                ('description', models.TextField(blank=True)),
                ('input_type', models.CharField(choices=[('single_choice', 'Single choice'), ('multiple_choice', 'Multiple choice'), ('text', 'Free text')], max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ('sort_order', 'name', 'id'),
            },
        ),
        migrations.CreateModel(
            name='CustomizationChoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(max_length=140)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('option', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='choices', to='customization.customizationoption')),
            ],
            options={
                'ordering': ('sort_order', 'name', 'id'),
            },
        ),
        migrations.CreateModel(
            name='ProductCustomization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_required', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('min_selections', models.PositiveIntegerField(blank=True, null=True)),
                ('max_selections', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('option', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='product_customizations', to='customization.customizationoption')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='customizations', to='catalog.product')),
            ],
            options={
                'ordering': ('sort_order', 'id'),
            },
        ),
        migrations.CreateModel(
            name='ProductCustomizationChoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price_adjustment', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('choice', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='product_configurations', to='customization.customizationchoice')),
                ('product_customization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='choices', to='customization.productcustomization')),
            ],
            options={
                'ordering': ('sort_order', 'id'),
            },
        ),
        migrations.AddConstraint(
            model_name='customizationchoice',
            constraint=models.UniqueConstraint(fields=('option', 'slug'), name='unique_choice_slug_per_option'),
        ),
        migrations.AddConstraint(
            model_name='productcustomization',
            constraint=models.UniqueConstraint(fields=('product', 'option'), name='unique_product_customization'),
        ),
        migrations.AddConstraint(
            model_name='productcustomizationchoice',
            constraint=models.UniqueConstraint(fields=('product_customization', 'choice'), name='unique_product_customization_choice'),
        ),
    ]
