from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q
from datetime import timedelta, datetime, time
from decimal import Decimal

from .models import (
    Client, Account, Tariff, Payment, PromisedPayment,
    ClientCredentials, generate_password
)


# ------------------------------------------------------------------
# УТИЛІТА: Генерація логінів та НУЛЬОВИХ БАЛАНСІВ для нових абонентів
# ------------------------------------------------------------------
def ensure_accounts_and_credentials():
    # 1. Створюємо доступи (логін/пароль), якщо їх немає
    clients_without_creds = Client.objects.filter(credentials__isnull=True)
    for client in clients_without_creds:
        ClientCredentials.objects.create(client=client)

    # 2. Створюємо фінансовий рахунок (баланс 0.00), якщо його немає
    clients_without_accs = Client.objects.filter(account__isnull=True)
    for client in clients_without_accs:
        Account.objects.create(client=client, balance=Decimal('0.00'))


# ------------------------------------------------------------------
# БІЛІНГ — Головна сторінка
# ------------------------------------------------------------------
@login_required
def billing_dashboard(request):
    # Гарантуємо, що у всіх 100% абонентів є баланс та логін
    ensure_accounts_and_credentials()

    clients = Client.objects.select_related(
        'account', 'tariff', 'credentials'
    ).all().order_by('full_name')

    # Фільтрація
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')

    if search:
        clients = clients.filter(
            Q(full_name__icontains=search) |
            Q(contract_number__icontains=search) |
            Q(phone__icontains=search) |
            Q(credentials__login__icontains=search)
        )
    if status_filter == 'blocked':
        clients = clients.filter(is_blocked=True)
    elif status_filter == 'active':
        clients = clients.filter(is_blocked=False)
    elif status_filter == 'negative':
        clients = clients.filter(account__balance__lt=0)

    # Пагінація — 100 на сторінку
    paginator = Paginator(clients, 100)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Статистика
    total_balance = Account.objects.aggregate(s=Sum('balance'))['s'] or 0
    blocked_count = Client.objects.filter(is_blocked=True).count()
    negative_count = Account.objects.filter(balance__lt=0).count()

    now = timezone.now()
    monthly_income = Payment.objects.filter(
        payment_type='topup',
        created_at__year=now.year,
        created_at__month=now.month
    ).aggregate(s=Sum('amount'))['s'] or 0

    context = {
        'clients': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status_filter': status_filter,
        'total_balance': total_balance,
        'blocked_count': blocked_count,
        'negative_count': negative_count,
        'monthly_income': monthly_income,
        'tariffs': Tariff.objects.all(),
    }
    return render(request, 'billing.html', context)


# ------------------------------------------------------------------
# КАРТКА АБОНЕНТА
# ------------------------------------------------------------------
@login_required
def billing_client(request, client_id):
    client = get_object_or_404(
        Client.objects.select_related('account', 'tariff', 'credentials', 'equipment'),
        pk=client_id
    )

    # Перестраховка: якщо заходимо в картку, а балансу/доступу немає
    if not hasattr(client, 'credentials'):
        ClientCredentials.objects.create(client=client)
    if not hasattr(client, 'account'):
        Account.objects.create(client=client, balance=Decimal('0.00'))

    client.refresh_from_db()

    payments = client.payments.all()[:50]
    promised = client.promised_payments.filter(
        is_active=True, expires_at__gt=timezone.now()
    ).first()

    context = {
        'client': client,
        'payments': payments,
        'promised': promised,
        'tariffs': Tariff.objects.all(),
    }
    return render(request, 'billing_client.html', context)


# ------------------------------------------------------------------
# ПОПОВНЕННЯ БАЛАНСУ
# ------------------------------------------------------------------
@login_required
def topup_balance(request, client_id):
    if request.method != 'POST':
        return redirect('billing_client', client_id=client_id)

    client = get_object_or_404(Client, pk=client_id)
    amount_str = request.POST.get('amount', '0').replace(',', '.')
    comment = request.POST.get('comment', '')

    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            raise ValueError
    except (ValueError, Exception):
        messages.error(request, 'Введіть коректну суму поповнення.')
        return redirect('billing_client', client_id=client_id)

    account, _ = Account.objects.get_or_create(client=client)
    account.balance += amount
    account.save()

    # Якщо баланс став >= 0, розблоковуємо
    if account.balance >= 0:
        client.is_blocked = False
        client.save()

    Payment.objects.create(
        client=client,
        amount=amount,
        payment_type='topup',
        comment=comment or f'Поповнення на {amount} грн',
        created_by=request.user.username,
    )

    messages.success(request, f'✅ Баланс поповнено на {amount} грн.')
    return redirect('billing_client', client_id=client_id)


# ------------------------------------------------------------------
# ОБІЦЯНИЙ ПЛАТІЖ
# ------------------------------------------------------------------
@login_required
def promised_payment(request, client_id):
    if request.method != 'POST':
        return redirect('billing_client', client_id=client_id)

    client = get_object_or_404(Client, pk=client_id)

    existing = client.promised_payments.filter(
        is_active=True, expires_at__gt=timezone.now()
    ).first()

    if existing:
        messages.warning(request, f'⚠️ Вже є активний обіцяний платіж до {existing.expires_at.strftime("%d.%m.%Y")}.')
        return redirect('billing_client', client_id=client_id)

    # Логіка для вибору днів (7 днів або кастомна дата)
    promised_type = request.POST.get('promised_type')

    if promised_type == 'custom':
        date_str = request.POST.get('expires_date')
        custom_date = None
        if date_str:
            try:
                custom_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                custom_date = None

        if custom_date and custom_date > timezone.localdate():
            expires_at = timezone.make_aware(datetime.combine(custom_date, time(23, 59)))
        else:
            messages.warning(request, '⚠️ Дата некоректна або вже минула — встановлено стандартні 7 днів.')
            expires_at = timezone.now() + timedelta(days=7)
    else:
        expires_at = timezone.now() + timedelta(days=7)

    comment = request.POST.get('comment', '').strip()

    PromisedPayment.objects.create(
        client=client,
        expires_at=expires_at,
        comment=comment or f'Обіцяний платіж до {expires_at.strftime("%d.%m.%Y")}',
    )

    client.is_blocked = False
    client.save()

    Payment.objects.create(
        client=client,
        amount=Decimal('0.00'),
        payment_type='promised',
        comment=f'Обіцяний платіж — доступ до {expires_at.strftime("%d.%m.%Y")}',
        created_by=request.user.username,
    )

    messages.success(request, f'✅ Обіцяний активовано до {expires_at.strftime("%d.%m.%Y")}.')
    return redirect('billing_client', client_id=client_id)


# ------------------------------------------------------------------
# СПИСАННЯ АБОНПЛАТИ З УСІХ
# ------------------------------------------------------------------
@login_required
def charge_all(request):
    if request.method != 'POST':
        return redirect('billing_dashboard')

    clients = Client.objects.select_related('account', 'tariff').all()
    charged, blocked_new, skipped = 0, 0, 0
    now = timezone.now()

    for client in clients:
        if not client.tariff:
            skipped += 1
            continue

        tariff_price = Decimal(str(client.tariff.price))
        account, _ = Account.objects.get_or_create(client=client)

        has_promised = client.promised_payments.filter(
            is_active=True, expires_at__gt=now
        ).exists()

        account.balance -= tariff_price
        account.save()

        Payment.objects.create(
            client=client,
            amount=-tariff_price,
            payment_type='charge',
            comment=f'Списання абонплати: {client.tariff.name}',
            created_by=request.user.username,
        )

        if account.balance < 0 and not has_promised:
            client.is_blocked = True
            client.save()
            blocked_new += 1

        charged += 1

    messages.success(
        request,
        f'✅ Списано у {charged} абонентів. Заблоковано: {blocked_new}. Пропущено: {skipped}.'
    )
    return redirect('billing_dashboard')


# ------------------------------------------------------------------
# ІНШІ ДІЇ З АБОНЕНТОМ
# ------------------------------------------------------------------
@login_required
def change_tariff(request, client_id):
    if request.method == 'POST':
        client = get_object_or_404(Client, pk=client_id)
        try:
            tariff = Tariff.objects.get(pk=request.POST.get('tariff_id'))
            client.tariff = tariff
            client.save()
            messages.success(request, f'✅ Тариф змінено на «{tariff.name}».')
        except Tariff.DoesNotExist:
            messages.error(request, 'Тариф не знайдено.')
    return redirect('billing_client', client_id=client_id)


@login_required
def regenerate_password(request, client_id):
    if request.method == 'POST':
        client = get_object_or_404(Client, pk=client_id)
        creds, _ = ClientCredentials.objects.get_or_create(client=client)
        creds.password = generate_password()
        creds.save()
        messages.success(request, f'✅ Пароль оновлено: {creds.password}')
    return redirect('billing_client', client_id=client_id)


@login_required
def toggle_block(request, client_id):
    if request.method == 'POST':
        client = get_object_or_404(Client, pk=client_id)
        client.is_blocked = not client.is_blocked
        client.save()
        action = 'заблокований' if client.is_blocked else 'розблокований'
        messages.success(request, f'✅ Абонента {action}.')
    return redirect('billing_client', client_id=client_id)