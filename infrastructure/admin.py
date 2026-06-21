from django.contrib import admin
from .models import (
    Equipment, Client, WarehouseItem, Tariff, Employee,
    ConnectionApplication, Product, Sale, ClientCredentials, EmergencyTask, MessageLog,
    Account, PromisedPayment, Payment
)

admin.site.register(ClientCredentials)
admin.site.register(MessageLog)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('client', 'balance', 'updated_at')
    search_fields = ('client__full_name', 'client__contract_number')
    list_filter = ('updated_at',)


@admin.register(PromisedPayment)
class PromisedPaymentAdmin(admin.ModelAdmin):
    list_display = ('client', 'expires_at', 'is_active', 'created_at')
    list_filter = ('is_active', 'expires_at')
    search_fields = ('client__full_name', 'client__contract_number')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('client', 'amount', 'payment_type', 'created_by', 'created_at')
    list_filter = ('payment_type', 'created_at')
    search_fields = ('client__full_name', 'client__contract_number', 'comment')

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'location', 'is_active')
    search_fields = ('name', 'ip_address')
    list_filter = ('is_active',)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'onu_serial', 'contract_number', 'is_online', 'equipment')
    search_fields = ('full_name', 'onu_serial', 'contract_number')
    list_filter = ('is_online', 'equipment')
    list_editable = ('is_online',)

@admin.register(WarehouseItem)
class WarehouseItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'unit', 'last_updated')
    list_filter = ('category',)
    search_fields = ('name',)
    list_editable = ('quantity',)

@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'speed', 'is_promo')
    list_editable = ('price', 'speed', 'is_promo')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'phone', 'is_active')
    list_filter = ('position', 'is_active')
    search_fields = ('full_name', 'phone')

@admin.register(ConnectionApplication)
class ConnectionApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'city', 'phone', 'status', 'created_at')
    list_filter = ('status', 'city', 'object_type')
    list_editable = ('status',)

@admin.register(EmergencyTask)
class EmergencyTaskAdmin(admin.ModelAdmin):
    list_display = ('address', 'city', 'status', 'created_at')
    list_filter = ('status', 'city', 'created_at')
    search_fields = ('address', 'description')
    list_editable = ('status',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'quantity', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name',)

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'total_price', 'sold_at')
    list_filter = ('sold_at',)
    search_fields = ('product__name',)