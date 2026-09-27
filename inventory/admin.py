from django.contrib import admin
from .models import Unit, ScanAttempt


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = (
        'cooler_tag', 'serial_number', 'asset_number',
        'location', 'status', 'last_verified',
    )
    search_fields = ('cooler_tag', 'serial_number', 'asset_number', 'location')
    list_filter = ('status',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('cooler_tag',)


@admin.register(ScanAttempt)
class ScanAttemptAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'result', 'unit', 'site_name', 'scanned_at')
    list_filter = ('result', 'scanned_at')
    search_fields = ('staff_id', 'scanned_tag', 'scanned_serial', 'scanned_asset')
    readonly_fields = ('scanned_at',)
    date_hierarchy = 'scanned_at'

    def has_add_permission(self, request):
        # Scans come from the app, not from the admin
        return False