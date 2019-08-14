import json
from enum import (
    Enum,
    auto,
)


class UserRole(Enum):
    guest = auto()
    normal = auto()

    def translate(self, _escape_table):
        return self.name


class JerryEncoder(json.JSONEncoder):
    prefix = "__enum__"

    def default(self, o):
        if isinstance(o, UserRole):
            return {self.prefix: o.name}
        else:
            return super().default(o)


def jerry_decode(d):
    if JerryEncoder.prefix in d:
        name = d[JerryEncoder.prefix]
        return UserRole[name]
    else:
        return d
