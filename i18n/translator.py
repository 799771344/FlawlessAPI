import json
from typing import Dict, Optional
from pathlib import Path
import logging

class I18nSupport:
    """国际化支持"""
    
    def __init__(self, locale_dir: str, default_locale: str = 'en'):
        self.locale_dir = Path(locale_dir)
        self.default_locale = default_locale
        self.translations: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)
        
        # 加载翻译文件
        self.load_translations()
        
    def load_translations(self):
        """加载所有翻译文件"""
        try:
            for file_path in self.locale_dir.glob('*.json'):
                locale = file_path.stem
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.translations[locale] = json.load(f)
                    
            self.logger.info(f"Loaded translations for: {list(self.translations.keys())}")
        except Exception as e:
            self.logger.error(f"Failed to load translations: {e}")
            
    def translate(self, key: str, locale: str = None, **kwargs) -> str:
        """翻译文本
        Args:
            key: 翻译键
            locale: 语言代码
            **kwargs: 用于格式化的参数
        Returns:
            str: 翻译后的文本
        """
        locale = locale or self.default_locale
        
        # 获取翻译
        translation = self.translations.get(locale, {}).get(key)
        if not translation:
            # 回退到默认语言
            translation = self.translations.get(self.default_locale, {}).get(key, key)
            
        # 应用格式化参数
        try:
            return translation.format(**kwargs)
        except Exception as e:
            self.logger.error(f"Translation format error: {e}")
            return key
            
    def add_translation(self, locale: str, translations: Dict):
        """添加新的翻译"""
        if locale in self.translations:
            self.translations[locale].update(translations)
        else:
            self.translations[locale] = translations
            
    def save_translations(self):
        """保存翻译到文件"""
        for locale, translations in self.translations.items():
            file_path = self.locale_dir / f"{locale}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)