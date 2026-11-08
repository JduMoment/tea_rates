"""Справочники в коде: виды чая, сезоны сбора, колесо вкусов.

Подписи, склонения и цвета живут здесь, а не в БД: в таблицах хранится только имя члена enum.
"""

from back.enums.flavor import Flavor, FlavorGroup, Taste
from back.enums.season import Season
from back.enums.tea_kind import TeaKind

__all__ = ["Flavor", "FlavorGroup", "Season", "Taste", "TeaKind"]
