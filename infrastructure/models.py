import random
import string
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Equipment(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва обладнання")
    ip_address = models.GenericIPAddressField(verbose_name="IP-адреса")
    mac_address = models.CharField(max_length=17, blank=True, null=True, verbose_name="MAC-адреса")
    location = models.CharField(max_length=255, verbose_name="Розташування")
    is_active = models.BooleanField(default=True, verbose_name="Online")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        verbose_name = "Обладнання"
        verbose_name_plural = "Обладнання"

    def __str__(self):
        return f"{self.name} ({self.ip_address})"


class Client(models.Model):
    full_name = models.CharField(max_length=150, verbose_name="ПІБ клієнта")
    contract_number = models.CharField(max_length=20, unique=True, verbose_name="Номер договору")
    onu_serial = models.CharField(max_length=20, unique=True, null=True, blank=True)
    address = models.CharField(max_length=255, verbose_name="Адреса")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    equipment = models.ForeignKey(Equipment, on_delete=models.SET_NULL, null=True, blank=True)
    is_online = models.BooleanField(default=False)
    tariff = models.ForeignKey('Tariff', on_delete=models.SET_NULL, null=True, blank=True)
    is_blocked = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Абонент"
        verbose_name_plural = "Абоненти"

    def __str__(self):
        return f"{self.full_name} - {self.contract_number}"


class WarehouseItem(models.Model):
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=20)
    quantity = models.IntegerField(default=0)
    unit = models.CharField(max_length=10, default='шт.')
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Складська позиція"
        verbose_name_plural = "Складські позиції"

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"


class MessageLog(models.Model):
    target_client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.CharField(max_length=200)
    text = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Повідомлення"
        verbose_name_plural = "Повідомлення"

    def __str__(self):
        to = self.target_client.full_name if self.target_client else "Усім абонентам"
        return f"{self.subject} → {to}"


class Tariff(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    speed = models.IntegerField()
    channels = models.CharField(max_length=50)
    is_promo = models.BooleanField(default=False)
    dynamic_ip = models.BooleanField(default=False)
    kinoman = models.BooleanField(default=False)
    support_24_7 = models.BooleanField(default=True)
    connection_fee = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифи"

    def __str__(self):
        return f"{self.name} — {self.price} грн/міс"


class Employee(models.Model):
    POSITION_CHOICES = [
        ('admin', 'Системний адміністратор'),
        ('installer', 'Монтажник'),
        ('operator', 'Оператор Колл-центру'),
        ('foreman', 'Бригадир'),
        ('director', 'Директор'),
    ]
    full_name = models.CharField(max_length=150)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, verbose_name="Посада")
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Співробітник"
        verbose_name_plural = "Співробітники"

    def __str__(self):
        return self.full_name


class ConnectionApplication(models.Model):
    full_name = models.CharField(max_length=150, verbose_name="ПІБ")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    city = models.CharField(max_length=50, verbose_name="Місто")
    task_type = models.CharField(max_length=20, default='connection', verbose_name="Тип завдання")
    object_type = models.CharField(max_length=20, verbose_name="Тип об'єкта")
    street = models.CharField(max_length=100, verbose_name="Вулиця")
    house_number = models.CharField(max_length=20, verbose_name="№ будинку")
    comment = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    planned_date = models.DateField(null=True, blank=True, verbose_name="Запланована дата")
    assignee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Виконавець")

    class Meta:
        verbose_name = "Заявка на підключення"
        verbose_name_plural = "Заявки на підключення"

    def __str__(self):
        return f"Заявка: {self.full_name} — {self.city}"


class EmergencyTask(models.Model):
    city = models.CharField(max_length=50, default="м. Васильків", verbose_name="Місто")
    street = models.CharField(max_length=100, verbose_name="Вулиця")
    address = models.CharField(max_length=255, verbose_name="Повна адреса")
    description = models.TextField(verbose_name="Опис проблеми")
    status = models.CharField(max_length=20, default='new')
    assignees = models.ManyToManyField(Employee, related_name="emergency_tasks")
    created_at = models.DateTimeField(auto_now_add=True)
    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Аварія"
        verbose_name_plural = "Аварії"

    def __str__(self):
        return f"Аварія: {self.address}"


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Назва")
    category = models.CharField(max_length=20, verbose_name="Категорія")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна")
    quantity = models.IntegerField(default=0, verbose_name="Кількість")
    is_available = models.BooleanField(default=True, verbose_name="Доступно")
    # ===== ОСЬ ПОЛЯ, ЯКИХ НЕ ВИСТАЧАЛО =====
    description = models.TextField(blank=True, null=True, verbose_name="Опис")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Зображення")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товари"

    def __str__(self):
        return self.name


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    sold_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Продаж"
        verbose_name_plural = "Продажі"

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


# ================= ФУНКЦІЇ ТА БІЛІНГОВІ МОДЕЛІ =================

def generate_login():
    """7 випадкових цифр, унікальний логін"""
    while True:
        login = ''.join(random.choices(string.digits, k=7))
        if not ClientCredentials.objects.filter(login=login).exists():
            return login


def generate_password():
    """Буква + 4 цифри, напр. q1234"""
    letter = random.choice(string.ascii_lowercase)
    digits = ''.join(random.choices(string.digits, k=4))
    return letter + digits


class Account(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='account')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Рахунок абонента"
        verbose_name_plural = "Рахунки абонентів"

    def __str__(self):
        return f"{self.client.full_name} — {self.balance} ₴"


class ClientCredentials(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='credentials')
    login = models.CharField(max_length=7, unique=True)
    password = models.CharField(max_length=10)

    def save(self, *args, **kwargs):
        if not self.login:
            self.login = generate_login()
        if not self.password:
            self.password = generate_password()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Обліковий запис абонента"
        verbose_name_plural = "Облікові записи абонентів"

    def __str__(self):
        return f"{self.client.full_name}: {self.login}"


class PromisedPayment(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='promised_payments')
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    comment = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Обіцяний платіж"
        verbose_name_plural = "Обіцяні платежі"

    def __str__(self):
        return f"{self.client.full_name} до {self.expires_at.strftime('%d.%m.%Y')}"


class Payment(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=20)  # topup / charge / promised
    comment = models.CharField(max_length=255, blank=True, default='')
    created_by = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Платіж"
        verbose_name_plural = "Платежі"

    def __str__(self):
        return f"{self.client.full_name}: {self.amount} ₴ ({self.payment_type})"


@receiver(post_save, sender=Client)
def create_client_credentials(sender, instance, created, **kwargs):
    if created:
        ClientCredentials.objects.get_or_create(client=instance)