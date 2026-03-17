# Generated data migration for default admin user

from django.db import migrations


def create_default_admin(apps, schema_editor):
    """
    创建默认管理员账户
    用户名: admin
    密码: admin123
    """
    User = apps.get_model('auth', 'User')
    
    # 检查 admin 用户是否已存在
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@forum.local',
            password='admin123'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_admin),
    ]
