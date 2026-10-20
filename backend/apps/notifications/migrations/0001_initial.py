import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_key', models.CharField(max_length=40)),
                ('category', models.CharField(default='transactional', max_length=20)),
                ('deduplication_key', models.CharField(max_length=180, unique=True)),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='DeliveryAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.CharField(max_length=20)),
                ('status', models.CharField(default='pending', max_length=20)),
                ('provider_message_id', models.CharField(blank=True, max_length=180)),
                ('error_message', models.CharField(blank=True, max_length=500)),
                ('attempt_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='notifications.notification')),
            ],
        ),
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('marketing_whatsapp_enabled', models.BooleanField(default=False)),
                ('marketing_sms_enabled', models.BooleanField(default=False)),
                ('marketing_email_enabled', models.BooleanField(default=False)),
                ('marketing_consent_recorded_at', models.DateTimeField(blank=True, null=True)),
                ('marketing_consent_source', models.CharField(blank=True, max_length=80)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_preferences', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['event_key', 'created_at'], name='notificatio_event_k_0fb8ef_idx'),
        ),
    ]
