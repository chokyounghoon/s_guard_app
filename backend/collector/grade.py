from ..core.models import IncidentLevel

def determine_severity(current_error_rate: float, threshold: float) -> IncidentLevel:
    """
    Determine incident severity based on error rate and threshold.
    """
    if current_error_rate >= threshold:
        return IncidentLevel.LEVEL_3 # Critical
    elif current_error_rate >= (threshold * 0.8):
        return IncidentLevel.LEVEL_2 # Warning
    else:
        return IncidentLevel.LEVEL_1 # Caution
