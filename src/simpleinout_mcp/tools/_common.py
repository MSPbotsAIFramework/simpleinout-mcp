from .._json import error_envelope

NO_TOKEN = error_envelope(
    "not_configured",
    "No Simple In/Out credentials. Send the X-SimpleInOut-Client-Id, "
    "X-SimpleInOut-Client-Secret, and X-SimpleInOut-Refresh-Token headers.",
    False,
)
