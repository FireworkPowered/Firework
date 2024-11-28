import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Union

from jsonschema import Draft202012Validator

from firework.util.importlib import pkg_resources


@dataclass
class Hook:
    endpoint: str
    target: str


@dataclass
class Deployment:
    root: str = field(default_factory=lambda: str(Path.cwd()))


@dataclass
class Config:
    sources: dict[str, str] = field(default_factory=lambda: {"{**}": "config/{**}"})


@dataclass
class ServiceEntrypoint:
    entrypoint: str
    type: Literal["entrypoint"] = "entrypoint"
    group: list[str] = field(default_factory=lambda: ["default"])


@dataclass
class ServiceCustom:
    type: Literal["custom"]
    module: str
    group: list[str] = field(default_factory=lambda: ["default"])


@dataclass
class LumaConfig:
    deployment: Deployment = field(default_factory=Deployment)
    profiles: dict[str, list[str]] = field(default_factory=dict)
    config: Config = field(default_factory=Config)
    services: list[Union[ServiceEntrypoint, ServiceCustom]] = field(default_factory=list)
    hooks: list[Hook] = field(default_factory=list)

    def __post_init__(self):
        self.service_groups: dict[str, list[ServiceCustom | ServiceEntrypoint]] = {}

        for service in self.services:
            if not service.group:
                raise ValueError("service group cannot be empty")

            for group in service.group:
                if group not in self.service_groups:
                    self.service_groups[group] = []

                self.service_groups[group].append(service)

        self.profile_services: dict[str, list[ServiceCustom | ServiceEntrypoint]] = {}

        if "default" in self.profiles:
            raise ValueError("profile `default` is reserved for internal use")

        for profile, groups in self.profiles.items():
            profile_services = []

            for group in groups:
                if group not in self.service_groups:
                    raise ValueError(f"service group {group} not found in services")

                profile_services.extend(self.service_groups[group])

            self.profile_services[profile] = profile_services

        self.profile_services["default"] = self.service_groups.get("default", [])


content_validator = Draft202012Validator(json.loads(pkg_resources.read_text(__name__, "schema.json", "utf-8")))


def into_config(config_file: Path) -> LumaConfig:
    import tomlkit
    from dacite.config import Config
    from dacite.core import from_dict

    with open(config_file, "r", encoding="utf-8") as fp:
        doc = tomlkit.load(fp)
        doc.pop("$schema", None)

    data = doc.unwrap()
    errs = list(content_validator.iter_errors(data))
    if errs:
        raise ValueError(f"Invalid {config_file.name}", errs)

    return from_dict(LumaConfig, data, Config(strict=True))
