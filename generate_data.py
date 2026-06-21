import os
import django
import random
import string

# Налаштовуємо зв'язок нашого скрипта з твоїм сайтом
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Імпортуємо наші таблиці та бібліотеку Faker
from infrastructure.models import Equipment, Client
from faker import Faker


def generate_onu_serial():
    vendor = random.choice(['ZTEG', 'HWTC', 'ALCL', 'GPON'])
    random_hex = ''.join(random.choices(string.hexdigits.upper(), k=8))
    return f"{vendor}{random_hex}"


def generate_fake_clients(count=100):
    fake = Faker('uk_UA')
    equipments = list(Equipment.objects.all())

    if not equipments:
        print("Помилка: Додайте спочатку обладнання в адмінці!")
        return

    print(f"⏳ Генеруємо {count} абонентів у форматі ПІБ...")

    for _ in range(count):
        serial = generate_onu_serial()
        while Client.objects.filter(onu_serial=serial).exists():
            serial = generate_onu_serial()

        # Збираємо ПІБ вручну: Прізвище + Ім'я + По-батькові
        full_name_pib = f"{fake.last_name()} {fake.first_name()} {fake.middle_name()}"

        Client.objects.create(
            full_name=full_name_pib,
            contract_number=fake.unique.bothify(text='UIC-##########'),
            onu_serial=serial,
            address=fake.address().replace('\n', ', '),  # Робимо адресу в один рядок
            phone=fake.phone_number(),
            equipment=random.choice(equipments),
            is_online=random.choice([True, False])
        )
    print(f"✅ Успішно додано {count} абонентів у форматі ПІБ!")


if __name__ == '__main__':
    generate_fake_clients(100)

