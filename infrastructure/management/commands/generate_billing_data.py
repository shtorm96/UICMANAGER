# infrastructure/management/commands/generate_billing_data.py
# Запуск: python manage.py generate_billing_data

import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from infrastructure.models import (
    Client, Account, Tariff, Payment, PromisedPayment, ClientCredentials
)


STREETS = {
    'м. Васильків': [
        'вул. Грушевського', 'вул. Київська', 'вул. Незалежності',
        'вул. Шевченка', 'вул. Соборна', 'вул. Центральна',
        'вул. Садова', 'вул. Лесі Українки', 'вул. Франка',
        'пр. Перемоги', 'вул. Богдана Хмельницького', 'вул. Гагаріна',
    ],
    'с. Барахти':       ['вул. Центральна', 'вул. Шкільна', 'вул. Садова'],
    'с. Березанщина':   ['вул. Польова', 'вул. Зелена', 'вул. Молодіжна'],
    'с. Безп\'ятне':    ['вул. Центральна', 'вул. Лісова'],
    'с. Борисів':       ['вул. Садова', 'вул. Набережна'],
    'с. Залізне':       ['вул. Центральна', 'вул. Польова'],
    'с. Заріччя':       ['вул. Річкова', 'вул. Зелена'],
    'с. Застугна':      ['вул. Центральна', 'вул. Шкільна'],
    'с. Здорівка':      ['вул. Садова', 'вул. Молодіжна'],
    'с. Зелений Бір':   ['вул. Лісова', 'вул. Центральна'],
    'с. Кобці':         ['вул. Польова', 'вул. Садова'],
    'с. Крушинка':      ['вул. Центральна', 'вул. Шкільна'],
    'с. Путрівка':      ['вул. Центральна', 'вул. Набережна', 'вул. Садова'],
}

CITIES = list(STREETS.keys())
CITY_WEIGHTS = [40] + [5] * (len(CITIES) - 1)  # Васильків частіше


class Command(BaseCommand):
    help = 'Генерує реалістичні білінгові дані та скорочує до 200 абонентів'

    def handle(self, *args, **options):
        self.stdout.write('🔄 Починаю генерацію даних...')

        tariffs = list(Tariff.objects.all())
        if not tariffs:
            self.stdout.write(self.style.ERROR('❌ Немає тарифів! Спочатку створи тарифи.'))
            return

        # ── 1. Скорочуємо до 200 абонентів ──────────────────────────
        total = Client.objects.count()
        if total > 200:
            to_delete = Client.objects.order_by('id')[200:]
            ids = list(to_delete.values_list('id', flat=True))
            Client.objects.filter(id__in=ids).delete()
            self.stdout.write(f'🗑  Видалено {total - 200} зайвих абонентів')

        clients = list(Client.objects.all())
        self.stdout.write(f'👥 Абонентів після очистки: {len(clients)}')

        # ── 2. Оновлюємо адреси ──────────────────────────────────────
        self.stdout.write('📍 Оновлюю адреси...')
        for client in clients:
            city = random.choices(CITIES, weights=CITY_WEIGHTS)[0]
            street = random.choice(STREETS[city])
            house = random.randint(1, 120)
            suffix = random.choice(['', '', '', '/А', '/Б', '/В'])
            client.address = f'{city}, {street}, {house}{suffix}'
        Client.objects.bulk_update(clients, ['address'])

        # ── 3. Credentials для всіх ──────────────────────────────────
        self.stdout.write('🔑 Генерую credentials...')
        for client in clients:
            ClientCredentials.objects.get_or_create(client=client)

        # ── 4. Тарифи + баланси + платежі ────────────────────────────
        self.stdout.write('💳 Генерую білінгові дані...')
        now = timezone.now()

        for client in clients:
            # Тариф (10% без тарифу)
            if random.random() > 0.10:
                client.tariff = random.choice(tariffs)

            # Початковий баланс
            rand = random.random()
            if rand < 0.60:      # 60% — нормальний баланс
                balance = Decimal(random.randint(50, 800))
                client.is_blocked = False
            elif rand < 0.80:    # 20% — низький баланс
                balance = Decimal(random.randint(0, 49))
                client.is_blocked = False
            elif rand < 0.93:    # 13% — мінус, заблокований
                balance = Decimal(random.randint(-300, -1))
                client.is_blocked = True
            else:                # 7% — мінус але є обіцяний
                balance = Decimal(random.randint(-150, -1))
                client.is_blocked = False

            account, _ = Account.objects.get_or_create(client=client)
            account.balance = balance
            account.save()

            # Обіцяний платіж для деяких мінусових
            if balance < 0 and not client.is_blocked:
                expires = now + timedelta(days=random.randint(1, 6))
                PromisedPayment.objects.get_or_create(
                    client=client,
                    defaults={'expires_at': expires, 'is_active': True}
                )

            # Історія платежів (2-8 записів за останні 6 місяців)
            Payment.objects.filter(client=client).delete()
            num_payments = random.randint(2, 8)

            for i in range(num_payments):
                days_ago = random.randint(1, 180)
                pay_date = now - timedelta(days=days_ago)

                ptype = random.choices(
                    ['topup', 'charge', 'charge', 'manual'],
                    weights=[40, 40, 15, 5]
                )[0]

                if ptype == 'topup':
                    amount = Decimal(random.choice([100, 150, 200, 250, 300, 500]))
                    comment = random.choice([
                        'Готівка', 'Термінал ПриватБанк',
                        'Переказ на картку', 'Онлайн оплата'
                    ])
                elif ptype == 'charge':
                    amount = -Decimal(str(client.tariff.price)) if client.tariff else Decimal('-99')
                    comment = f'Списання абонплати: {client.tariff.name if client.tariff else "—"}'
                else:
                    amount = Decimal(random.choice([50, -50, 100, -100]))
                    comment = 'Ручне коригування'

                p = Payment(
                    client=client,
                    amount=amount,
                    payment_type=ptype,
                    comment=comment,
                    created_by='system',
                )
                p.save()
                # Зміщуємо дату вручну після збереження
                Payment.objects.filter(pk=p.pk).update(created_at=pay_date)

        Client.objects.bulk_update(clients, ['tariff', 'is_blocked'])

        # ── Підсумок ─────────────────────────────────────────────────
        blocked = Client.objects.filter(is_blocked=True).count()
        no_tariff = Client.objects.filter(tariff__isnull=True).count()
        neg_balance = Account.objects.filter(balance__lt=0).count()
        promised = PromisedPayment.objects.filter(is_active=True).count()

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Готово!\n'
            f'   Абонентів: {Client.objects.count()}\n'
            f'   Заблокованих: {blocked}\n'
            f'   Від\'ємний баланс: {neg_balance}\n'
            f'   Обіцяний платіж: {promised}\n'
            f'   Без тарифу: {no_tariff}\n'
        ))