"""
Chuyển sang Gemini 3.8 Flash: tham số sinh nội dung theo thế hệ mô hình, nạp .env, client giả (không gọi API).
"""
import os
import types

import pytest

import config
from modules.utils.gemini_params import generation_kwargs, supports_sampling_params


class TestSamplingParams:
    @pytest.mark.parametrize('model,expected', [
        ('gemini-2.5-flash', True), ('gemini-2.0-flash', True), ('gemini-1.5-pro', True),
        ('gemini-3.8-flash', False), ('models/gemini-3.8-flash', False), ('gemini-3-pro', False),
        ('gemini-10-flash', False), ('something-else', True), ('', True), (None, True)])
    def test_supports_sampling_params(self, model, expected):
        assert supports_sampling_params(model) is expected

    def test_gemini_3_omits_temperature(self):
        assert generation_kwargs('gemini-3.8-flash', 8192, temperature=0.2) == {'max_output_tokens': 8192}

    def test_gemini_2_keeps_temperature(self):
        assert generation_kwargs('gemini-2.5-flash', 1000, temperature=0.2) == {
            'max_output_tokens': 1000, 'temperature': 0.2}

    def test_no_temperature_requested(self):
        assert 'temperature' not in generation_kwargs('gemini-2.5-flash', 1000)


class TestDotenv:
    def test_parses_common_forms_and_respects_existing_env(self, tmp_path, monkeypatch):
        env = tmp_path / '.env'
        env.write_bytes('﻿# comment\r\nT_PLAIN=abc\r\nexport T_EXPORT=xyz\r\nT_QUOTED="va lue"\r\n'
                        "T_SINGLE='s q'\r\nT_INLINE=keep # bỏ phần này\r\nT_EXISTING=from_file\r\n\r\nNOEQUALS\r\n"
                        'T_EMPTY=\r\n'.encode('utf-8'))
        for k in ('T_PLAIN', 'T_EXPORT', 'T_QUOTED', 'T_SINGLE', 'T_INLINE', 'T_EMPTY'):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv('T_EXISTING', 'from_shell')
        config._load_dotenv(str(env))
        assert os.environ['T_PLAIN'] == 'abc' and os.environ['T_EXPORT'] == 'xyz'
        assert os.environ['T_QUOTED'] == 'va lue' and os.environ['T_SINGLE'] == 's q'
        assert os.environ['T_INLINE'] == 'keep' and os.environ['T_EMPTY'] == ''
        assert os.environ['T_EXISTING'] == 'from_shell'            # biến môi trường được ưu tiên
        for k in ('T_PLAIN', 'T_EXPORT', 'T_QUOTED', 'T_SINGLE', 'T_INLINE', 'T_EMPTY'):
            os.environ.pop(k, None)

    def test_missing_file_is_ignored(self, tmp_path):
        config._load_dotenv(str(tmp_path / 'nope.env'))

    def test_model_defaults(self):
        assert config.AI_MODEL
        assert config.COMMITTEE_CONFIG['model'] == (os.environ.get('COMMITTEE_MODEL') or config.AI_MODEL)
        assert config.COMMITTEE_CONFIG['max_output_tokens'] >= 4096


class FakeGenai:
    """Thay module google.generativeai: ghi lại tham số GenerationConfig và model được dùng."""

    def __init__(self, reject_mime=False):
        self.reject_mime = reject_mime
        self.failures = []
        self.request_options = None
        self.config_kwargs = None
        self.model_name = None
        outer = self

        class GenerationConfig:
            def __init__(self, **kw):
                if outer.reject_mime and 'response_mime_type' in kw:
                    raise TypeError('unexpected keyword response_mime_type')
                outer.config_kwargs = kw

        class GenerativeModel:
            def __init__(self, model_name, system_instruction=None):
                outer.model_name = model_name

            def generate_content(self, prompt, generation_config=None, request_options=None):
                outer.request_options = request_options
                if outer.failures:
                    raise RuntimeError(outer.failures.pop(0))
                return types.SimpleNamespace(text='{"ok": true}')

        self.types = types.SimpleNamespace(GenerationConfig=GenerationConfig)
        self.GenerativeModel = GenerativeModel
        self.configure = lambda api_key=None: None


class TestGeminiClient:
    def _client(self, monkeypatch, model, reject_mime=False):
        from modules.committee import llm
        fake = FakeGenai(reject_mime)
        monkeypatch.setattr(llm, 'genai', fake)
        monkeypatch.setattr(llm, '_GENAI_AVAILABLE', True)
        return llm.GeminiClient(api_key='test-key', model=model), fake

    def test_gemini_3_8_request_has_no_sampling_params_and_asks_for_json(self, monkeypatch):
        client, fake = self._client(monkeypatch, 'gemini-3.8-flash')
        assert client.generate('sys', 'prompt') == '{"ok": true}'
        assert fake.model_name == 'gemini-3.8-flash'
        assert 'temperature' not in fake.config_kwargs
        assert fake.config_kwargs['response_mime_type'] == 'application/json'
        assert fake.config_kwargs['max_output_tokens'] == config.COMMITTEE_CONFIG['max_output_tokens']

    def test_gemini_2_5_still_gets_temperature(self, monkeypatch):
        client, fake = self._client(monkeypatch, 'gemini-2.5-flash')
        client.generate('sys', 'prompt')
        assert fake.config_kwargs['temperature'] == config.COMMITTEE_CONFIG['temperature']

    def test_old_library_without_mime_type_falls_back_without_temperature(self, monkeypatch):
        client, fake = self._client(monkeypatch, 'gemini-3.8-flash', reject_mime=True)
        client.generate('sys', 'prompt')
        assert 'response_mime_type' not in fake.config_kwargs and 'temperature' not in fake.config_kwargs

    def test_request_has_a_timeout(self, monkeypatch):
        client, fake = self._client(monkeypatch, 'gemini-3.8-flash')
        client.generate('s', 'p')
        assert fake.request_options == {'timeout': config.COMMITTEE_CONFIG['request_timeout']}

    def test_transient_overload_is_retried_with_backoff_then_succeeds(self, monkeypatch):
        from modules.committee import llm
        client, fake = self._client(monkeypatch, 'gemini-3.8-flash')
        fake.failures = ['503 This model is currently experiencing high demand', '504 Deadline expired']
        sleeps = []
        monkeypatch.setattr(llm.time, 'sleep', sleeps.append)
        assert client.generate('s', 'p') == '{"ok": true}'
        assert sleeps == list(config.COMMITTEE_CONFIG['retry_backoff'])[:2]

    def test_persistent_overload_gives_llm_unavailable_after_all_retries(self, monkeypatch):
        from modules.committee import llm
        client, fake = self._client(monkeypatch, 'gemini-3.8-flash')
        fake.failures = ['503 high demand'] * 10
        sleeps = []
        monkeypatch.setattr(llm.time, 'sleep', sleeps.append)
        with pytest.raises(llm.LLMUnavailable, match='503'):
            client.generate('s', 'p')
        assert len(sleeps) == config.COMMITTEE_CONFIG['api_retries']
        assert len(fake.failures) == 10 - (config.COMMITTEE_CONFIG['api_retries'] + 1)

    def test_non_transient_error_is_not_retried(self, monkeypatch):
        from modules.committee import llm
        client, fake = self._client(monkeypatch, 'gemini-3.8-flash')
        fake.failures = ['404 model not found']
        sleeps = []
        monkeypatch.setattr(llm.time, 'sleep', sleeps.append)
        with pytest.raises(llm.LLMUnavailable, match='404'):
            client.generate('s', 'p')
        assert sleeps == []

    def test_missing_key_is_reported_as_unavailable(self, monkeypatch):
        from modules.committee import llm
        monkeypatch.setattr(llm, '_GENAI_AVAILABLE', True)
        monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
        client = llm.GeminiClient(api_key=None, model='gemini-3.8-flash')
        client._key = None
        assert client.available is False
        with pytest.raises(llm.LLMUnavailable):
            client.generate('s', 'p')


class TestAIReasoner:
    def test_uses_configured_model_and_omits_temperature(self, monkeypatch):
        from modules.analysis import ai_reasoner
        fake = FakeGenai()
        monkeypatch.setattr(ai_reasoner, 'genai', fake)
        monkeypatch.setattr(ai_reasoner, '_GENAI_AVAILABLE', True)
        monkeypatch.setattr(ai_reasoner.AIReasoner, 'MODEL', 'gemini-3.8-flash')
        reasoner = ai_reasoner.AIReasoner(api_key='test-key')
        assert reasoner.available and fake.model_name == 'gemini-3.8-flash'
        assert reasoner._call_ai('hi') == '{"ok": true}'
        assert 'temperature' not in fake.config_kwargs
        assert fake.config_kwargs['max_output_tokens'] == ai_reasoner.AIReasoner.MAX_TOKENS >= 4096

    def test_default_model_comes_from_config(self):
        from modules.analysis.ai_reasoner import AIReasoner
        assert AIReasoner.MODEL == config.AI_MODEL
