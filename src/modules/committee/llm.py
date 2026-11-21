"""
Client LLM cho hội đồng. Giao diện tối giản `generate(system, prompt) -> str` để dễ thay bằng bản giả khi test.

LƯU Ý: GeminiClient CHƯA được kiểm thử với API thật trong phiên phát triển (không có GOOGLE_API_KEY và gói
google-generativeai trên máy dev). Lần chạy đầu tiên cần xem log; phần parse JSON đã chịu được output có ```fence.
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None
    _GENAI_AVAILABLE = False


class LLMUnavailable(RuntimeError):
    """Không gọi được LLM (thiếu gói/khoá, hoặc lỗi API)."""


class GeminiClient:
    def __init__(self, api_key=None, model=None, temperature=None, max_output_tokens=None):
        cfg = config.COMMITTEE_CONFIG
        self.model_name = model or cfg['model']
        self.temperature = cfg['temperature'] if temperature is None else temperature
        self.max_output_tokens = max_output_tokens or cfg['max_output_tokens']
        self._key = api_key or os.environ.get('GOOGLE_API_KEY')
        self._configured = False

    @property
    def available(self):
        return _GENAI_AVAILABLE and bool(self._key)

    def _model_for(self, system):
        if not self._configured:
            genai.configure(api_key=self._key)
            self._configured = True
        return genai.GenerativeModel(model_name=self.model_name, system_instruction=system)

    def generate(self, system, prompt):
        if not self.available:
            raise LLMUnavailable("Thiếu gói google-generativeai hoặc GOOGLE_API_KEY")
        try:
            model = self._model_for(system)
            kwargs = dict(max_output_tokens=self.max_output_tokens, temperature=self.temperature)
            try:
                gen_cfg = genai.types.GenerationConfig(response_mime_type='application/json', **kwargs)
            except TypeError:                      # phiên bản thư viện cũ không có response_mime_type
                gen_cfg = genai.types.GenerationConfig(**kwargs)
            response = model.generate_content(prompt, generation_config=gen_cfg)
            return response.text
        except LLMUnavailable:
            raise
        except Exception as e:                     # lỗi mạng/quota/an toàn nội dung...
            raise LLMUnavailable(f"Gemini API lỗi: {e}") from e
