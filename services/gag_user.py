"""Совместимость: старые импорты gag_* → Aqua."""

from services.aqua_network import AquaError as GAGError
from services.aqua_user import (
    AquaNotConfiguredError as GagNotConfiguredError,
    ad_id_from_url,
    generate_link_for_lead,
    generate_link_for_user,
    load_aqua_profile as load_gag_profile,
    profile_ready,
)

__all__ = [
    "GAGError",
    "GagNotConfiguredError",
    "ad_id_from_url",
    "generate_link_for_lead",
    "generate_link_for_user",
    "load_gag_profile",
    "profile_ready",
]
