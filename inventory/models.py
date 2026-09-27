from django.db import models


class Unit(models.Model):
    """
    A single physical cooler / fridge / dispenser.
    Each row = one unit. The three identifiers must be unique across the table.
    """

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Retired', 'Retired'),
        ('Lost', 'Lost'),
    ]

    cooler_tag = models.CharField(
        max_length=50, unique=True, db_index=True,
        help_text="Barcode value on the cooler tag."
    )
    serial_number = models.CharField(
        max_length=50, unique=True, db_index=True,
        help_text="Barcode value on the serial number sticker."
    )
    asset_number = models.CharField(
        max_length=50, unique=True, db_index=True,
        help_text="Asset number (usually typed manually)."
    )
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    last_verified = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['cooler_tag']
        verbose_name = "Unit"
        verbose_name_plural = "Units"

    def __str__(self):
        return f"{self.cooler_tag} | {self.serial_number} | {self.asset_number}"


class ScanAttempt(models.Model):
    """
    Every scan the app performs — success, mismatch, not-found, partial, duplicate.
    This is your audit trail and the source for the review queue.
    """

    RESULT_CHOICES = [
        ('VERIFIED', 'Verified'),
        ('MISMATCH', 'Mismatch'),
        ('NOT_FOUND', 'Not Found'),
        ('PARTIAL', 'Partial Save'),
        ('DUPLICATE', 'Duplicate Same Day'),
    ]

    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='scans',
        help_text="Matched unit, if any."
    )

    # Raw values captured on the device
    scanned_tag = models.CharField(max_length=50, blank=True)
    scanned_serial = models.CharField(max_length=50, blank=True)
    scanned_asset = models.CharField(max_length=50, blank=True)

    # Who / where
    staff_id = models.CharField(max_length=100, db_index=True)
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    site_name = models.CharField(max_length=200, blank=True)

    # Outcome
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    message = models.CharField(max_length=300, blank=True)
    mismatch_details = models.JSONField(
        null=True, blank=True,
        help_text="Which scanned field matched which unit (for mismatch review)."
    )

    scanned_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-scanned_at']
        indexes = [
            models.Index(fields=['staff_id', 'scanned_at']),
            models.Index(fields=['result']),
        ]
        verbose_name = "Scan Attempt"
        verbose_name_plural = "Scan Attempts"

    def __str__(self):
        return f"{self.staff_id} | {self.result} | {self.scanned_at:%Y-%m-%d %H:%M}"