"""
Tests for the config module.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestModelProvider:
    """Tests for ModelProvider enum."""
    
    def test_gemini_value(self):
        """Test Gemini provider value."""
        from config import ModelProvider
        assert ModelProvider.GEMINI.value == "gemini"
    
    def test_ollama_value(self):
        """Test Ollama provider value."""
        from config import ModelProvider
        assert ModelProvider.OLLAMA.value == "ollama"


class TestGeminiModel:
    """Tests for GeminiModel enum."""
    
    def test_model_values(self):
        """Test Gemini model values."""
        from config import GeminiModel
        assert GeminiModel.GEMINI_2_5_FLASH.value == "gemini-2.5-flash"
        assert GeminiModel.GEMINI_1_5_PRO.value == "gemini-1.5-pro"
        assert GeminiModel.GEMINI_1_5_FLASH.value == "gemini-1.5-flash"
        assert GeminiModel.GEMINI_2_0_FLASH.value == "gemini-2.0-flash-exp"


class TestOllamaModel:
    """Tests for OllamaModel enum."""
    
    def test_model_values(self):
        """Test Ollama model values."""
        from config import OllamaModel
        assert OllamaModel.DEEPSEEK_OCR.value == "deepseek-ocr:3b"
        assert OllamaModel.QWEN2_5_CODER.value == "qwen2.5-coder:3b"


class TestThemeConfig:
    """Tests for ThemeConfig dataclass."""
    
    def test_default_values(self):
        """Test ThemeConfig default values."""
        from config import ThemeConfig
        theme = ThemeConfig()
        
        assert theme.accent_color == "#FF8800"
        assert theme.accent_color_name == "orange1"
        assert theme.bg_color == "#0D1117"
        assert theme.text_color == "#E6EDF3"
        assert theme.success_color == "#3FB950"
        assert theme.warning_color == "#D29922"
        assert theme.error_color == "#F85149"
        assert theme.info_color == "#58A6FF"
    
    def test_custom_values(self):
        """Test ThemeConfig with custom values."""
        from config import ThemeConfig
        theme = ThemeConfig(accent_color="#00FF00", success_color="#FFFFFF")
        
        assert theme.accent_color == "#00FF00"
        assert theme.success_color == "#FFFFFF"
        # Other defaults unchanged
        assert theme.bg_color == "#0D1117"


class TestGeminiSafetySettings:
    """Tests for GeminiSafetySettings dataclass."""
    
    def test_default_values(self):
        """Test default safety settings are BLOCK_NONE."""
        from config import GeminiSafetySettings
        settings = GeminiSafetySettings()
        
        assert settings.harassment == "BLOCK_NONE"
        assert settings.hate_speech == "BLOCK_NONE"
        assert settings.sexually_explicit == "BLOCK_NONE"
        assert settings.dangerous_content == "BLOCK_NONE"
    
    def test_to_list(self):
        """Test to_list() method output format."""
        from config import GeminiSafetySettings
        settings = GeminiSafetySettings()
        result = settings.to_list()
        
        assert len(result) == 4
        assert all("category" in item and "threshold" in item for item in result)
        
        categories = [item["category"] for item in result]
        assert "HARM_CATEGORY_HARASSMENT" in categories
        assert "HARM_CATEGORY_HATE_SPEECH" in categories
        assert "HARM_CATEGORY_SEXUALLY_EXPLICIT" in categories
        assert "HARM_CATEGORY_DANGEROUS_CONTENT" in categories
    
    def test_custom_settings_to_list(self):
        """Test to_list() with custom threshold."""
        from config import GeminiSafetySettings
        settings = GeminiSafetySettings(harassment="BLOCK_MEDIUM_AND_ABOVE")
        result = settings.to_list()
        
        harassment_setting = next(
            item for item in result if item["category"] == "HARM_CATEGORY_HARASSMENT"
        )
        assert harassment_setting["threshold"] == "BLOCK_MEDIUM_AND_ABOVE"


class TestConfig:
    """Tests for the main Config class."""
    
    def test_default_initialization(self, clean_env):
        """Test Config with default values."""
        from config import Config, ModelProvider
        
        config = Config()
        
        assert config.google_api_key == ""
        assert config.ollama_host == "http://localhost:11434"
        assert config.max_context_messages == 50
        assert config.max_tokens_per_message == 8000
        assert config.sliding_window_size == 20
        assert isinstance(config.project_root, Path)
    
    def test_environment_variables(self):
        """Test Config reads from environment."""
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "test-api-key",
            "OLLAMA_HOST": "http://custom:11434",
            "USER_NAME": "TestUser",
            "ORG_NAME": "TestOrg",
        }, clear=False):
            from importlib import reload
            import config
            reload(config)
            
            cfg = config.Config()
            assert cfg.google_api_key == "test-api-key"
            assert cfg.ollama_host == "http://custom:11434"
            assert cfg.user_name == "TestUser"
            assert cfg.org_name == "TestOrg"
    
    def test_current_model_gemini(self, clean_env):
        """Test current_model property for Gemini."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.GEMINI
        config.gemini_model = "gemini-1.5-pro"
        
        assert config.current_model == "gemini-1.5-pro"
    
    def test_current_model_ollama(self, clean_env):
        """Test current_model property for Ollama."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.OLLAMA
        config.ollama_model = "qwen2.5-coder:3b"
        
        assert config.current_model == "qwen2.5-coder:3b"
    
    def test_model_display_name(self, clean_env):
        """Test model_display_name property."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.GEMINI
        config.gemini_model = "gemini-2.5-flash"
        
        assert "Gemini" in config.model_display_name
        assert "gemini-2.5-flash" in config.model_display_name
    
    def test_switch_provider_enum(self, clean_env):
        """Test switch_provider with enum."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.GEMINI
        config.switch_provider(ModelProvider.OLLAMA)
        
        assert config.default_provider == ModelProvider.OLLAMA
    
    def test_switch_provider_string(self, clean_env):
        """Test switch_provider with string."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.GEMINI
        config.switch_provider("ollama")
        
        assert config.default_provider == ModelProvider.OLLAMA
    
    def test_switch_model_gemini(self, clean_env):
        """Test switch_model for Gemini provider."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.GEMINI
        config.switch_model("gemini-1.5-pro")
        
        assert config.gemini_model == "gemini-1.5-pro"
    
    def test_switch_model_ollama(self, clean_env):
        """Test switch_model for Ollama provider."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.OLLAMA
        config.switch_model("deepseek-r1:8b")
        
        assert config.ollama_model == "deepseek-r1:8b"
    
    def test_validate_missing_api_key(self, clean_env):
        """Test validate() catches missing API key."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.GEMINI
        config.google_api_key = ""
        
        issues = config.validate()
        assert len(issues) == 1
        assert "GOOGLE_API_KEY" in issues[0]
    
    def test_validate_with_api_key(self, clean_env):
        """Test validate() passes with API key."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.GEMINI
        config.google_api_key = "valid-key"
        
        issues = config.validate()
        assert len(issues) == 0
    
    def test_validate_ollama_no_key_needed(self, clean_env):
        """Test validate() doesn't require key for Ollama."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.OLLAMA
        config.google_api_key = ""
        
        issues = config.validate()
        assert len(issues) == 0
    
    def test_to_dict(self, clean_env):
        """Test to_dict() method."""
        from config import Config, ModelProvider
        
        config = Config()
        config.default_provider = ModelProvider.GEMINI
        config.gemini_model = "gemini-2.5-flash"
        config.user_name = "TestUser"
        config.org_name = "TestOrg"
        config.project_root = Path("/test/path")
        
        result = config.to_dict()
        
        assert result["provider"] == "gemini"
        assert result["model"] == "gemini-2.5-flash"
        assert result["user"] == "TestUser"
        assert result["org"] == "TestOrg"
        assert result["project_root"] == str(Path("/test/path"))


class TestGlobalConfig:
    """Tests for global config functions."""
    
    def test_get_config(self, clean_env):
        """Test get_config returns Config instance."""
        from config import get_config, Config
        
        config = get_config()
        assert isinstance(config, Config)
    
    def test_reload_config(self, clean_env):
        """Test reload_config creates new instance."""
        from config import get_config, reload_config
        
        original = get_config()
        original.user_name = "Modified"
        
        # Reload should create fresh config
        reloaded = reload_config()
        
        # Should be different object
        assert reloaded is not original
