# ============================================================
# infrastructure/management/commands/monthly_charge.py
# Запуск: python manage.py monthly_charge
# Автозапуск 1-го числа о 10:00 через cron:
#   0 10 1 * * /path/to/venv/bin/python /path/to/manage.py monthly_charge
# ============================================================
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from infrastructure.models import Client, Account, Payment, PromisedPayment


class Command(BaseCommand):
    help = 'Щомісячне списання абонплати (запускати 1-го числа о 10:00)'

    def handle(self, *args, **options):
        clients = Client.objects.select_related('account', 'tariff').all()
        charged = blocked = skipped = 0
        now = timezone.now()

        for client in clients:
            if not client.tariff:
                skipped += 1
                continue

            price = Decimal(str(client.tariff.price))
            account, _ = Account.objects.get_or_create(client=client)

            has_promised = client.promised_payments.filter(
                is_active=True, expires_at__gt=now
            ).exists()

            account.balance -= price
            account.save()

            Payment.objects.create(
                client=client,
                amount=-price,
                payment_type='charge',
                comment=f'Автосписання 1-го числа: {client.tariff.name}',
                created_by='system',
            )

            if account.balance < 0 and not has_promised:
                client.is_blocked = True
                client.save()
                blocked += 1

            charged += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Списання завершено: {charged} абонентів, '
                f'заблоковано: {blocked}, без тарифу: {skipped}'
            )
        )