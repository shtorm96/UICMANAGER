# Generated manually — видалення моделі Ticket (замінено на ConnectionApplication з task_type='repair')

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0030_alter_employee_position'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Ticket',
        ),
    ]
