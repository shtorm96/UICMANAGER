from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from infrastructure.views import (
    dashboard_view,
    client_list_view,
    client_detail_view,
    network_map_view,
    warehouse_view,
    messages_view,
    tariffs_view,
    personnel_view,
    create_application_view,
    tasks_view,
    sell_product_view,
    create_emergency_view,
    global_search_view,
)

from infrastructure.views_billing import (
    billing_dashboard,
    billing_client,
    topup_balance,
    promised_payment,
    charge_all,
    change_tariff,
    regenerate_password,
    toggle_block,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('', dashboard_view, name='dashboard'),
    path('clients/', client_list_view, name='clients'),
    path('clients/<int:pk>/', client_detail_view, name='client_detail'),
    path('map/', network_map_view, name='network_map'),
    path('warehouse/', warehouse_view, name='warehouse'),
    path('messages/', messages_view, name='messages'),
    path('tariffs/', tariffs_view, name='tariffs'),
    path('personnel/', personnel_view, name='personnel'),
    path('create-application/', create_application_view, name='create_application'),
    path('tasks/', tasks_view, name='tasks'),
    path('sell/<int:product_id>/', sell_product_view, name='sell_product'),
    path('emergency/create/', create_emergency_view, name='create_emergency'),
    path('search/', global_search_view, name='global_search'),

    # Білінг
    path('billing/', billing_dashboard, name='billing_dashboard'),
    path('billing/client/<int:client_id>/', billing_client, name='billing_client'),
    path('billing/client/<int:client_id>/topup/', topup_balance, name='topup_balance'),
    path('billing/client/<int:client_id>/promised/', promised_payment, name='promised_payment'),
    path('billing/client/<int:client_id>/change-tariff/', change_tariff, name='change_tariff'),
    path('billing/client/<int:client_id>/regenerate-password/', regenerate_password, name='regenerate_password'),
    path('billing/client/<int:client_id>/toggle-block/', toggle_block, name='toggle_block'),
    path('billing/charge-all/', charge_all, name='charge_all'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)