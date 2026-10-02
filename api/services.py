from dataclasses import dataclass
from typing import Optional

from django.utils import timezone

from inventory.models import Unit, ScanAttempt


@dataclass
class VerificationResult:
    """The outcome of a scan verification."""
    result: str                              # VERIFIED / MISMATCH / NOT_FOUND / PARTIAL / DUPLICATE
    message: str                             # Human-readable, shown on the phone
    unit: Optional[Unit] = None              # The matched unit, if any
    mismatch_details: Optional[dict] = None  # What matched what, for the review queue


def verify_scan(
    tag: str = '',
    serial: str = '',
    asset: str = '',
    staff_id: str = '',
) -> VerificationResult:
    """
    Core validation logic.

    Rules:
      - All 3 provided + all resolve to the same unit → VERIFIED
      - All 3 provided + resolve to different units → MISMATCH
      - Some provided values not in DB → MISMATCH (logged for review)
      - Only 1 value provided + it exists → PARTIAL
      - Nothing in DB at all → NOT_FOUND
      - Same unit already scanned today by this staff → DUPLICATE (soft warning)
    """
    tag = (tag or '').strip()
    serial = (serial or '').strip()
    asset = (asset or '').strip()

    # --- Case 0: nothing scanned ---
    if not any([tag, serial, asset]):
        return VerificationResult(
            result='NOT_FOUND',
            message='No details provided. Please scan or enter at least one value.',
        )

    # --- Resolve each provided field ---
    tag_unit = Unit.objects.filter(cooler_tag=tag).first() if tag else None
    serial_unit = Unit.objects.filter(serial_number=serial).first() if serial else None
    asset_unit = Unit.objects.filter(asset_number=asset).first() if asset else None

    provided = []   # [(field_name, raw_value, unit_or_None), ...]
    if tag:
        provided.append(('tag', tag, tag_unit))
    if serial:
        provided.append(('serial', serial, serial_unit))
    if asset:
        provided.append(('asset', asset, asset_unit))

    found = [(n, v, u) for n, v, u in provided if u]
    not_found = [(n, v) for n, v, u in provided if not u]

    # --- Case 1: nothing in DB at all ---
    if not found:
        return VerificationResult(
            result='NOT_FOUND',
            message='Unit not in database. Contact admin to register it.',
            mismatch_details={
                'not_found_fields': [n for n, _ in not_found],
            },
        )

    # --- Case 2: only ONE field was provided ---
    if len(provided) == 1:
        name, value, unit = provided[0]
        if unit:
            return VerificationResult(
                result='PARTIAL',
                message=(
                    f'Partial match on {name}: {unit.cooler_tag}. '
                    f'Scan the remaining details to fully verify.'
                ),
                unit=unit,
            )
        else:
            return VerificationResult(
                result='NOT_FOUND',
                message=f'{name.title()} not in database. Contact admin.',
            )

    # --- Case 3: 2 or 3 fields provided, but some are not in DB ---
    if not_found:
        details = {
            'matched': {n: u.cooler_tag for n, _, u in found},
            'not_found_fields': [n for n, _ in not_found],
        }
        return VerificationResult(
            result='MISMATCH',
            message=(
                f'Mismatch: {", ".join(n for n, _ in not_found)} '
                f'not found in database. Rescan or contact admin.'
            ),
            mismatch_details=details,
        )

    # --- Case 4: all provided fields found — do they agree on the same unit? ---
    unique_units = {u for _, _, u in found}

    if len(unique_units) > 1:
        details = {n: u.cooler_tag for n, _, u in found}
        return VerificationResult(
            result='MISMATCH',
            message='These belong to different units. Please rescan.',
            mismatch_details=details,
        )

    unit = unique_units.pop()

    # --- Case 5: all match — check same-day duplicate ---
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    already_today = (
        ScanAttempt.objects
        .filter(unit=unit, staff_id=staff_id, scanned_at__gte=today_start)
        .filter(result__in=['VERIFIED', 'DUPLICATE'])
        .exists()
    )

    if already_today:
        return VerificationResult(
            result='DUPLICATE',
            message=f'⚠️ {unit.cooler_tag} was already scanned today by you.',
            unit=unit,
        )

    # --- All clear ---
    return VerificationResult(
        result='VERIFIED',
        message=(
            f'✅ Verified: {unit.cooler_tag} | '
            f'{unit.serial_number} | {unit.asset_number}'
        ),
        unit=unit,
    )

