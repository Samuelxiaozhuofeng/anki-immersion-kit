# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from .subsearch_ajt.addon_config import AddonConfigManager


class SubSearchConfig(AddonConfigManager):
    pass


config = SubSearchConfig()
