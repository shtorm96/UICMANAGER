import os
import django
import random
import string

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from infrastructure.models import Equipment, Client, Ticket
from faker import Faker


def generate_onu_serial():
    vendor = random.choice(['ZTEG', 'HWTC', 'ALCL', 'GPON'])
    random_hex = ''.join(random.choices(string.hexdigits.upper(), k=8))
    return f"{vendor}{random_hex}"


def generate_fake_data(count=50):
    fake = Faker('uk_UA')
    equipments = list(Equipment.objects.all())

    if not equipments:
        print("Спочатку додай обладнання в адмінці!")
        return

    print(f"⏳ Наповнюємо базу...")

    problems = [
        "Немає інтернету", "Низька швидкість", "Червоний вогник на ONU",
        "Кабель перебито", "Налаштування роутера", "Поганий сигнал Wi-Fi"
    ]

    for _ in range(count):
        serial = generate_onu_serial()
        while Client.objects.filter(onu_serial=serial).exists():
            serial = generate_onu_serial()

        # Генеруємо ПІБ
        if random.choice([True, False]):
            pib = f"{fake.last_name_male()} {fake.first_name_male()} {fake.middle_name_male()}"
        else:
            pib = f"{fake.last_name_female()} {fake.first_name_female()} {fake.middle_name_female()}"

        client = Client.objects.create(
            full_name=pib,
            contract_number=fake.unique.bothify(text='UIC-##########'),
            onu_serial=serial,
            address=fake.address().replace('\n', ', '),
            phone=fake.phone_number(),
            equipment=random.choice(equipments),
            is_online=random.choice([True, False])
        )

        # Кожному 4-му клієнту створюємо заявку
        if random.random() < 0.25:
            Ticket.objects.create(
                client=client,
                description=random.choice(problems),
                status=random.choice(['new', 'process', 'closed']),
                priority=random.choice(['low', 'medium', 'high'])
            )

    print(f"✅ База готова: {count} абонентів та пачка заявок.")


if __name__ == '__main__':
    generate_fake_data(500
                       )