from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from .models import (
    Client, MessageLog,
    Tariff, Employee, ConnectionApplication, Product, Sale, EmergencyTask
)


@login_required
def dashboard_view(request):
    # 1. Беремо тільки АКТИВНІ заявки (Нові або Погоджені/В роботі)
    active_apps = ConnectionApplication.objects.filter(
        status__in=['new', 'agreed']
    ).order_by('-created_at')

    # 2. Беремо тільки АКТИВНІ аварії (Нові або В процесі усунення)
    active_emergencies = EmergencyTask.objects.filter(
        status__in=['new', 'in_progress']
    ).order_by('-created_at')

    return render(request, 'dashboard.html', {
        'total_clients': Client.objects.count(),
        'online_clients': Client.objects.filter(is_online=True).count(),
        'offline_clients': Client.objects.filter(is_online=False).count(),
        'new_tickets': active_apps.count(),  # Лічильник нових заявок на дашборді
        'active_applications': active_apps,
        'active_emergencies': active_emergencies,
        'installers': Employee.objects.filter(position__in=['installer', 'foreman']),
    })


@login_required
def create_emergency_view(request):
    if request.method == 'POST':
        city = request.POST.get('city', 'м. Васильків')
        street = request.POST.get('street', '')
        full_address = f"{city}, {street}"

        task = EmergencyTask.objects.create(
            city=city,
            street=street,
            address=full_address,
            description=request.POST.get('description', ''),
            status='new',
            latitude=request.POST.get('latitude'),
            longitude=request.POST.get('longitude')
        )
        installer_ids = request.POST.getlist('installers')
        if installer_ids:
            task.assignees.set(installer_ids)
    return redirect('dashboard')


@login_required
def create_application_view(request):
    if request.method == 'POST':
        status = request.POST.get('status', 'new')
        ConnectionApplication.objects.create(
            full_name=request.POST.get('full_name'),
            phone=request.POST.get('phone'),
            city=request.POST.get('city'),
            task_type=request.POST.get('task_type', 'connection'),
            object_type=request.POST.get('object_type'),
            street=request.POST.get('street'),
            house_number=request.POST.get('house_number'),
            comment=request.POST.get('comment'),
            status=status
        )
    return redirect('tasks')


@login_required
def tasks_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'assign':
            task_type = request.POST.get('task_type')
            task_id = request.POST.get('task_id')
            assignee_id = request.POST.get('assignee')
            planned_date = request.POST.get('planned_date')
            comment = request.POST.get('comment')

            if task_type == 'application':
                app = get_object_or_404(ConnectionApplication, id=task_id)
                if assignee_id: app.assignee_id = assignee_id
                if planned_date: app.planned_date = planned_date
                if comment: app.comment = f"{app.comment}\nЗапис оператора: {comment}" if app.comment else comment
                app.status = 'agreed'
                app.save()
            elif task_type == 'emergency':
                em = get_object_or_404(EmergencyTask, id=task_id)
                if assignee_id: em.assignees.set([assignee_id])
                if comment: em.description = f"{em.description}\nКоментар: {comment}"
                em.status = 'in_progress'
                em.save()

        elif action == 'complete':
            task_type = request.POST.get('task_type')
            task_id = request.POST.get('task_id')
            if task_type == 'application':
                app = get_object_or_404(ConnectionApplication, id=task_id)
                app.status = 'connected'
                app.save()
            elif task_type == 'emergency':
                em = get_object_or_404(EmergencyTask, id=task_id)
                em.status = 'done'
                em.save()

        elif action == 'cancel':
            task_type = request.POST.get('task_type')
            task_id = request.POST.get('task_id')
            if task_type == 'application':
                app = get_object_or_404(ConnectionApplication, id=task_id)
                app.status = 'refusal'
                app.save()
            elif task_type == 'emergency':
                em = get_object_or_404(EmergencyTask, id=task_id)
                em.status = 'done'
                em.description += "\n[СКАСОВАНО]"
                em.save()

        return redirect('tasks')

    pending_apps = ConnectionApplication.objects.filter(status='new').order_by('-created_at')
    pending_emergencies = EmergencyTask.objects.filter(status='new').order_by('-created_at')
    planned_apps = ConnectionApplication.objects.filter(status='agreed').order_by('planned_date')
    planned_emergencies = EmergencyTask.objects.filter(status='in_progress').order_by('-created_at')
    completed_apps = ConnectionApplication.objects.filter(status__in=['connected', 'refusal']).order_by('-created_at')[
        :50]
    completed_emergencies = EmergencyTask.objects.filter(status='done').order_by('-created_at')[:50]

    pending_count = pending_apps.count() + pending_emergencies.count()
    planned_count = planned_apps.count() + planned_emergencies.count()
    installers = Employee.objects.filter(is_active=True, position__in=['installer', 'foreman'])

    return render(request, 'tasks.html', {
        'pending_apps': pending_apps, 'pending_emergencies': pending_emergencies,
        'planned_apps': planned_apps, 'planned_emergencies': planned_emergencies,
        'completed_apps': completed_apps, 'completed_emergencies': completed_emergencies,
        'pending_count': pending_count, 'planned_count': planned_count,
        'installers': installers,
    })


@login_required
def client_list_view(request):
    search_query = request.GET.get('search', '')
    clients = Client.objects.all()
    if search_query:
        clients = clients.filter(Q(full_name__icontains=search_query) | Q(contract_number__icontains=search_query))
    return render(request, 'clients.html', {'clients': clients, 'search_query': search_query})


@login_required
def client_detail_view(request, pk):
    client = get_object_or_404(Client, pk=pk)

    # Найкращий розбір адреси клієнта для підстановки у формі заявки на ремонт
    address_parts = [p.strip() for p in client.address.split(',')] if client.address else []
    prefill_city = address_parts[0] if len(address_parts) > 0 else ''
    prefill_street = address_parts[1] if len(address_parts) > 1 else ''
    if prefill_street.lower().startswith('вул.'):
        prefill_street = prefill_street[4:].strip()
    prefill_house = ', '.join(address_parts[2:]) if len(address_parts) > 2 else ''

    return render(request, 'client_detail.html', {
        'client': client,
        'prefill_city': prefill_city,
        'prefill_street': prefill_street,
        'prefill_house': prefill_house,
    })


@login_required
def global_search_view(request):
    query = request.GET.get('q', '')
    results = Client.objects.filter(
        Q(full_name__icontains=query) | Q(contract_number__icontains=query)) if query else []
    return render(request, 'search_results.html', {'query': query, 'results': results})


@login_required
def network_map_view(request):
    return render(request, 'network_map.html')


@login_required
def warehouse_view(request):
    return render(request, 'warehouse.html', {
        'products': Product.objects.filter(is_available=True),
        'recent_sales': Sale.objects.all().order_by('-sold_at')[:5]
    })


@login_required
def sell_product_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if product.quantity > 0:
        product.quantity -= 1
        product.save()
        Sale.objects.create(product=product, quantity=1, total_price=product.price)
    return redirect('warehouse')


@login_required
def tariffs_view(request):
    return render(request, 'tariffs.html', {'tariffs': Tariff.objects.all().order_by('price')})


@login_required
def personnel_view(request):
    role_filter = request.GET.get('role', 'all')
    employees = Employee.objects.all().order_by('position')
    if role_filter and role_filter != 'all':
        employees = employees.filter(position=role_filter)
    return render(request, 'personnel.html', {
        'employees': employees,
        'positions': Employee.POSITION_CHOICES,
        'current_filter': role_filter,
    })


@login_required
def messages_view(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'send')

        if action == 'delete':
            message_id = request.POST.get('message_id')
            MessageLog.objects.filter(id=message_id).delete()
            messages.success(request, "Запис видалено.")
            return redirect('messages')

        client_id = request.POST.get('client_id')
        subject = request.POST.get('subject', '')
        msg_text = request.POST.get('text')

        if client_id and msg_text:
            if client_id == 'all':
                MessageLog.objects.create(target_client=None, subject=subject, text=msg_text)
                messages.success(request, "Повідомлення надіслано всім абонентам!")
            else:
                client = get_object_or_404(Client, id=client_id)
                MessageLog.objects.create(target_client=client, subject=subject, text=msg_text)
                messages.success(request, f"Повідомлення для {client.full_name} успішно відправлено!")

        return redirect('messages')

    return render(request, 'messages.html', {
        'clients': Client.objects.all().order_by('full_name'),
        'history': MessageLog.objects.all().order_by('-sent_at')
    })