"""Configuration management for Narrio API settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


@dataclass
class APIConfig:
    """API configuration for a specific service."""

    provider: str
    api_key: str
    base_url: str
    model: str
    format: str = "chat/completions"  # "chat/completions" or "images/generations"

    def __post_init__(self):
        """Validate required fields."""
        if not self.api_key:
            raise ValueError(f"{self.provider} API key is required")
        if not self.base_url:
            raise ValueError(f"{self.provider} base URL is required")
        if not self.model:
            raise ValueError(f"{self.provider} model is required")
        if self.format not in ("chat/completions", "images/generations"):
            raise ValueError(f"Invalid format: {self.format}. Must be 'chat/completions' or 'images/generations'")


@dataclass
class ASRConfig:
    """ASR (Volcengine) configuration."""

    provider: str = "volcengine"
    app_id: str = ""
    api_key: str = ""  # 新版 API Key
    app_key: str = ""  # 旧版 App Key
    access_token: str = ""  # 旧版 Access Token
    secret_key: str = ""  # Secret Key (optional)
    resource_id: str = "auto"  # auto, volc.seedasr.auc, volc.bigasr.auc
    language: str = ""  # zh-CN, en-US, etc. (empty = auto detect)

    def __post_init__(self):
        """Validate that at least one authentication method is provided."""
        has_new_auth = bool(self.api_key)
        has_old_auth = bool(self.app_key and self.access_token)
        if not has_new_auth and not has_old_auth:
            raise ValueError(
                "ASR authentication required: provide either 'api_key' (new) or both 'app_key' and 'access_token' (old)"
            )


@dataclass
class NarrioConfig:
    """Complete Narrio configuration."""

    text_api: APIConfig
    image_api: APIConfig
    asr_api: ASRConfig | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NarrioConfig:
        """Create config from dictionary."""
        text_data = data.get("text_api", {})
        image_data = data.get("image_api", {})
        asr_data = data.get("asr_api", {})

        # ASR config is optional
        asr_config = None
        if asr_data and (asr_data.get("api_key") or (asr_data.get("app_key") and asr_data.get("access_token"))):
            try:
                asr_config = ASRConfig(
                    provider=asr_data.get("provider", "volcengine"),
                    app_id=asr_data.get("app_id", ""),
                    api_key=asr_data.get("api_key", ""),
                    app_key=asr_data.get("app_key", ""),
                    access_token=asr_data.get("access_token", ""),
                    secret_key=asr_data.get("secret_key", ""),
                    resource_id=asr_data.get("resource_id", "auto"),
                    language=asr_data.get("language", ""),
                )
            except ValueError:
                # If ASR config is invalid, leave it as None
                pass

        return cls(
            text_api=APIConfig(
                provider=text_data.get("provider", "unknown"),
                api_key=text_data.get("api_key", ""),
                base_url=text_data.get("base_url", ""),
                model=text_data.get("model", ""),
                format=text_data.get("format", "chat/completions"),
            ),
            image_api=APIConfig(
                provider=image_data.get("provider", "unknown"),
                api_key=image_data.get("api_key", ""),
                base_url=image_data.get("base_url", ""),
                model=image_data.get("model", ""),
                format=image_data.get("format", "images/generations"),  # 默认图片用images/generations
            ),
            asr_api=asr_config,
        )

    @classmethod
    def from_yaml_file(cls, path: Path) -> NarrioConfig:
        """Load configuration from YAML file."""
        if not yaml:
            raise RuntimeError("PyYAML is not installed. Install it with: pip install pyyaml")

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_env_or_yaml(cls, yaml_path: Path | None = None) -> NarrioConfig:
        """
        Load configuration from YAML file only.

        Priority:
        1. YAML file (if provided and exists)
        2. Default YAML location (.narrio.yaml in current directory)
        3. Raise error if no YAML file found
        """
        # Try provided YAML path first
        if yaml_path:
            if not yaml_path.exists():
                raise FileNotFoundError(
                    f"Config file not found: {yaml_path}\n"
                    "Please create a .narrio.yaml file (see .narrio.yaml.example)"
                )
            return cls.from_yaml_file(yaml_path)

        # Try default YAML location
        default_yaml = Path.cwd() / ".narrio.yaml"
        if default_yaml.exists():
            return cls.from_yaml_file(default_yaml)

        # No config found
        raise FileNotFoundError(
            "No .narrio.yaml configuration file found.\n"
            "Please create a .narrio.yaml file in the current directory.\n"
            "See .narrio.yaml.example for reference."
        )


def load_config(yaml_path: Path | None = None) -> NarrioConfig:
    """
    Load Narrio configuration.

    This is the main entry point for loading configuration.
    It will try YAML first, then fall back to environment variables.
    """
    return NarrioConfig.from_env_or_yaml(yaml_path)
