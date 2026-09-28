from django.conf import settings
from django.utils import timezone


def is_live_observation_fresh(observation) -> bool:
    observed_at = observation.last_live_discovery_at
    return bool(
        observed_at
        and (timezone.now() - observed_at).total_seconds()
        <= settings.DISCOVERY_OBSERVATION_MAX_AGE_SECONDS
    )
