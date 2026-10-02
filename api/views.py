from django.shortcuts import render, redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone

from inventory.models import ScanAttempt
from .services import verify_scan



def login_page(request):
    return render(request, 'scan/login.html')


def scan_page(request):
    return render(request, 'scan/scan.html')




class ScanVerifyView(APIView):
    """
    POST /api/scan/verify/

    Body (JSON):
        {
            "tag":    "CT-001",
            "serial": "SN-001",
            "asset":  "AST-001",
            "staff_id": "john.doe",     # optional; falls back to request.user.username
            "gps_lat": -1.2921,          # optional
            "gps_lng": 36.8219,          # optional
            "site_name": "Nairobi CBD"   # optional
        }

    Response (JSON):
        {
            "result": "VERIFIED",
            "message": "✅ Verified: CT-001 | SN-001 | AST-001",
            "unit": { ... } | null,
            "attempt_id": 42
        }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data

        tag = str(data.get('tag', '')).strip()
        serial = str(data.get('serial', '')).strip()
        asset = str(data.get('asset', '')).strip()
        staff_id = str(data.get('staff_id') or request.user.username).strip()
        site_name = str(data.get('site_name', '')).strip()

        gps_lat = self._to_decimal(data.get('gps_lat'))
        gps_lng = self._to_decimal(data.get('gps_lng'))

        # --- Run the verification logic ---
        outcome = verify_scan(
            tag=tag,
            serial=serial,
            asset=asset,
            staff_id=staff_id,
        )

        # --- Record the attempt (audit trail) ---
        attempt = ScanAttempt.objects.create(
            unit=outcome.unit,
            scanned_tag=tag,
            scanned_serial=serial,
            scanned_asset=asset,
            staff_id=staff_id,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            site_name=site_name,
            result=outcome.result,
            message=outcome.message,
            mismatch_details=outcome.mismatch_details,
        )

        # --- On verified/duplicate, bump the unit's last_verified timestamp ---
        if outcome.unit and outcome.result in ('VERIFIED', 'DUPLICATE'):
            outcome.unit.last_verified = timezone.now()
            outcome.unit.save(update_fields=['last_verified'])

        # --- Build response ---
        unit_payload = None
        if outcome.unit:
            unit_payload = {
                'cooler_tag': outcome.unit.cooler_tag,
                'serial_number': outcome.unit.serial_number,
                'asset_number': outcome.unit.asset_number,
                'location': outcome.unit.location,
                'status': outcome.unit.status,
            }

        return Response(
            {
                'result': outcome.result,
                'message': outcome.message,
                'unit': unit_payload,
                'attempt_id': attempt.id,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _to_decimal(value):
        """Safely convert to float or return None."""
        if value in (None, '', 'null'):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None