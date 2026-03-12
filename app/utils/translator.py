#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
翻译工具模块
支持百度翻译和Google翻译两种服务
"""

import requests
import hashlib
import random
import json
import urllib.parse
from config.api_config import (
    TRANSLATE_SERVICE,
    BAIDU_TRANSLATE_CONFIG,
    GOOGLE_TRANSLATE_CONFIG,
    BAIDU_LANG_MAP,
    GOOGLE_LANG_MAP
)
from app.utils.logger import logger

class Translator:
    """多语言翻译工具（支持百度翻译和Google翻译）"""
    
    def __init__(self):
        self.service = TRANSLATE_SERVICE
        self.lang_map = GOOGLE_LANG_MAP if self.service == "google" else BAIDU_LANG_MAP
        
        # 检查翻译服务是否可用
        self.service_enabled = self._check_service_enabled()
        
        if self.service_enabled:
            logger.info(f"使用 {self.service} 翻译服务")
        else:
            logger.warning(f"{self.service} 翻译服务未配置，将返回原文")
    
    def _check_service_enabled(self):
        """检查翻译服务是否可用"""
        if self.service == "google":
            # Google翻译
            if GOOGLE_TRANSLATE_CONFIG.get("use_free_api"):
                return True  # 免费API无需配置
            else:
                # 检查API密钥
                api_key = GOOGLE_TRANSLATE_CONFIG.get("api_key", "")
                enabled = GOOGLE_TRANSLATE_CONFIG.get("enabled", False)
                return bool(api_key and enabled)
        else:
            # 百度翻译
            appid = BAIDU_TRANSLATE_CONFIG.get("appid", "")
            secret_key = BAIDU_TRANSLATE_CONFIG.get("secret_key", "")
            enabled = BAIDU_TRANSLATE_CONFIG.get("enabled", False)
            return bool(appid and secret_key and enabled)
    
    def translate(self, text: str, to_lang: str = "英文") -> str:
        """
        翻译文本
        :param text: 待翻译文本（中文）
        :param to_lang: 目标语言
        :return: 翻译结果（失败时返回原文）
        """
        # 跳过条件
        if not text or to_lang == "中文" or not self.service_enabled:
            return text
        
        # 获取语言代码
        to_lang_code = self.lang_map.get(to_lang)
        if not to_lang_code:
            logger.warning(f"不支持的目标语言: {to_lang}")
            return text
        
        try:
            if self.service == "google":
                return self._google_translate(text, to_lang_code)
            else:
                return self._baidu_translate(text, to_lang_code)
        except Exception as e:
            logger.warning(f"翻译失败: {str(e)}，返回原文")
            return text
    
    def _baidu_translate(self, text: str, to_lang_code: str) -> str:
        """百度翻译实现"""
        appid = BAIDU_TRANSLATE_CONFIG["appid"]
        secret_key = BAIDU_TRANSLATE_CONFIG["secret_key"]
        
        # 生成签名
        salt = random.randint(32768, 65536)
        sign_str = f"{appid}{text}{salt}{secret_key}"
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        
        # 构造请求
        url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        params = {
            "q": text,
            "from": "zh",
            "to": to_lang_code,
            "appid": appid,
            "salt": salt,
            "sign": sign
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            result = response.json()
            
            if "error_code" in result:
                logger.warning(f"百度翻译错误: {result.get('error_msg', '未知错误')}")
                return text
            
            if "trans_result" in result and result["trans_result"]:
                return result["trans_result"][0]["dst"]
        except Exception as e:
            logger.warning(f"百度翻译请求失败: {str(e)}")
        
        return text
    
    def _google_translate(self, text: str, to_lang_code: str) -> str:
        """Google翻译实现"""
        if GOOGLE_TRANSLATE_CONFIG.get("use_free_api"):
            # 使用免费API（非官方，但有使用限制）
            return self._google_free_translate(text, to_lang_code)
        else:
            # 使用官方API
            return self._google_cloud_translate(text, to_lang_code)
    
    def _google_free_translate(self, text: str, to_lang_code: str) -> str:
        """Google免费翻译API"""
        try:
            # 使用translate.google.com的免费接口
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "zh-CN",
                "tl": to_lang_code,
                "dt": "t",
                "q": text
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0 and len(result[0]) > 0:
                    return result[0][0][0]
        except Exception as e:
            logger.warning(f"Google免费翻译失败: {str(e)}")
        
        return text
    
    def _google_cloud_translate(self, text: str, to_lang_code: str) -> str:
        """Google Cloud Translation API"""
        api_key = GOOGLE_TRANSLATE_CONFIG.get("api_key", "")
        if not api_key:
            return text
        
        try:
            url = "https://translation.googleapis.com/language/translate/v2"
            params = {
                "q": text,
                "target": to_lang_code,
                "source": "zh-CN",
                "key": api_key,
                "format": "text"
            }
            
            response = requests.get(url, params=params, timeout=5)
            result = response.json()
            
            if "data" in result and "translations" in result["data"]:
                return result["data"]["translations"][0]["translatedText"]
        except Exception as e:
            logger.warning(f"Google Cloud翻译失败: {str(e)}")
        
        return text
    
    def translate_batch(self, texts: list, to_lang: str = "英文") -> list:
        """批量翻译"""
        if not self.service_enabled or to_lang == "中文":
            return texts
        
        results = []
        for text in texts:
            results.append(self.translate(text, to_lang))
        return results


# 测试代码
if __name__ == "__main__":
    translator = Translator()
    
    test_texts = [
        "今天的IT新闻有哪些？",
        "中国人工智能发展迅速",
        "华为发布新款芯片"
    ]
    
    print(f"\n当前翻译服务: {translator.service}")
    print(f"服务状态: {'已启用' if translator.service_enabled else '未配置'}\n")
    
    for text in test_texts:
        result = translator.translate(text, "英文")
        print(f"原文: {text}")
        print(f"译文: {result}\n")
