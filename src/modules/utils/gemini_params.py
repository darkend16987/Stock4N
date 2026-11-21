"""
Tham số sinh nội dung cho Gemini, theo thế hệ mô hình.

Tài liệu Gemini 3.8 Flash (aistudio.google.com/docs/whats-new-gemini-3.8) dặn bỏ `temperature`, `top_p`, `top_k`
(không rõ gửi lên sẽ lỗi hay bị bỏ qua) → với Gemini >= 3 không gửi các tham số này; Gemini 2.x giữ nguyên.
"""
import re


def supports_sampling_params(model_name):
    """True nếu mô hình còn nhận temperature/top_p/top_k (Gemini 2.x trở xuống hoặc tên không nhận diện được)."""
    m = re.match(r'(?:models/)?gemini-(\d+)', str(model_name or ''))
    return not (m and int(m.group(1)) >= 3)


def generation_kwargs(model_name, max_output_tokens, temperature=None):
    kwargs = {'max_output_tokens': max_output_tokens}
    if temperature is not None and supports_sampling_params(model_name):
        kwargs['temperature'] = temperature
    return kwargs
