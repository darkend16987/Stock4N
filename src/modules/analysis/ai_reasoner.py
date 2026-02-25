"""
AI Reasoner - Phân tích sâu bằng LLM (Gemini)
Dùng Google Gemini API để lập luận, tổng hợp và đề xuất từ dữ liệu đã thu thập.

Tại sao cần:
  - Rule-based scoring chỉ "đếm điểm" theo ngưỡng cố định.
  - LLM có thể xử lý ngữ cảnh phức tạp: macro, tin tức, mối liên hệ chéo.
  - Cung cấp lý giải bằng ngôn ngữ tự nhiên → trader dễ ra quyết định.
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from modules.utils.logger import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────
# Optional: import google-generativeai only if available
# ──────────────────────────────────────
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

# Import StockOptionSkill for strategy context
try:
    from modules.analysis.stock_option_skill import StockOptionSkill
    _skill = StockOptionSkill()
except Exception:
    _skill = None


class AIReasoner:
    """
    Sử dụng Google Gemini API để phân tích sâu cổ phiếu.

    Cần thiết lập GOOGLE_API_KEY trong .env hoặc environment variable.

    Modes:
        'stock_analysis'   – phân tích 1 mã cụ thể
        'market_outlook'   – nhận định tổng quan thị trường
        'portfolio_review' – đánh giá danh mục hiện tại
        'risk_alert'       – cảnh báo rủi ro từ context
    """

    MODEL = os.environ.get("AI_MODEL", "gemini-2.0-flash")
    MAX_TOKENS = 1500

    SYSTEM_PROMPT = """Bạn là chuyên gia phân tích cổ phiếu Việt Nam với 15 năm kinh nghiệm.
Bạn phân tích dữ liệu định lượng kết hợp với tư duy định tính.
Luôn trả lời bằng tiếng Việt, ngắn gọn, dứt khoát, có căn cứ.
Không đưa ra lời khuyên đầu tư tuyệt đối — chỉ phân tích.
Cấu trúc output: Tóm tắt → Điểm mạnh → Rủi ro → Khuyến nghị."""

    def __init__(self, api_key: str | None = None):
        if not _GENAI_AVAILABLE:
            logger.warning("google-generativeai package not installed. AI reasoning disabled.")
            self._model = None
            return

        key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not key:
            logger.warning("GOOGLE_API_KEY not set. AI reasoning disabled.")
            self._model = None
            return

        try:
            genai.configure(api_key=key)
            self._model = genai.GenerativeModel(
                model_name=self.MODEL,
                system_instruction=self.SYSTEM_PROMPT,
            )
            logger.info(f"AI Reasoner initialized with model: {self.MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self._model = None

    @property
    def available(self) -> bool:
        return self._model is not None

    # ──────────────────────────────────────
    # Public API
    # ──────────────────────────────────────

    def analyze_stock(self, symbol: str, stock_data: dict) -> str:
        """
        Phân tích 1 mã cổ phiếu từ dict data đã có.

        Args:
            symbol: Mã CK, VD 'VCB'
            stock_data: dict gồm các keys tuỳ có:
                - score, recommendation
                - roe, pe_ratio, profit_growth, revenue_growth
                - rsi, sma50_signal, volume_signal
                - ml_prediction, ml_confidence
                - seasonality_signal, momentum_signal
                - market_sentiment (breadth)
                - price, 52w_high, 52w_low
        """
        if not self.available:
            return self._fallback_analysis(symbol, stock_data)

        prompt = self._build_stock_prompt(symbol, stock_data)
        return self._call_ai(prompt)

    def market_outlook(self, breadth_data: dict, top_stocks: list) -> str:
        """
        Nhận định tổng quan thị trường.

        Args:
            breadth_data: Output từ MarketBreadthAnalyzer
            top_stocks: List of {symbol, score, recommendation}
        """
        if not self.available:
            return self._fallback_market(breadth_data)

        prompt = self._build_market_prompt(breadth_data, top_stocks)
        return self._call_ai(prompt)

    def portfolio_review(self, portfolio: list, market_filter: dict) -> str:
        """
        Đánh giá danh mục hiện tại trong bối cảnh thị trường.

        Args:
            portfolio: List of {symbol, action, capital, score}
            market_filter: Output từ MarketBreadthAnalyzer.get_market_filter()
        """
        if not self.available:
            return self._fallback_portfolio(portfolio)

        prompt = self._build_portfolio_prompt(portfolio, market_filter)
        return self._call_ai(prompt)

    # ──────────────────────────────────────
    # Prompt builders
    # ──────────────────────────────────────

    def _get_skill_context(self) -> str:
        """Get strategy context from StockOptionSkill if available."""
        if _skill:
            return _skill.get_ai_context() + "\n\n"
        return ""

    def _build_stock_prompt(self, symbol: str, d: dict) -> str:
        lines = [self._get_skill_context()]
        lines.append(f"## Phân Tích Cổ Phiếu: {symbol}\n")

        # Scoring
        if "score" in d:
            lines.append(f"Điểm tổng: {d['score']:.1f}/10  |  {d.get('recommendation', '')}")

        # Fundamentals
        fund_items = [
            ("ROE", d.get("roe"), "%"),
            ("P/E", d.get("pe_ratio"), "x"),
            ("Lợi nhuận tăng trưởng", d.get("profit_growth"), "%"),
            ("Doanh thu tăng trưởng", d.get("revenue_growth"), "%"),
        ]
        fund_lines = [f"{k}: {v}{u}" for k, v, u in fund_items if v is not None]
        if fund_lines:
            lines.append("\n**Cơ bản:** " + " | ".join(fund_lines))

        # Technical
        tech_items = [
            ("RSI", d.get("rsi")),
            ("MA50", d.get("sma50_signal")),
            ("Volume signal", d.get("volume_signal")),
        ]
        tech_lines = [f"{k}: {v}" for k, v in tech_items if v is not None]
        if tech_lines:
            lines.append("**Kỹ thuật:** " + " | ".join(tech_lines))

        # ML
        if d.get("ml_prediction"):
            lines.append(f"**ML:** {d['ml_prediction']} (confidence: {d.get('ml_confidence', '?')})")

        # Adaptive params
        if d.get("adaptive_rsi"):
            lines.append(f"**Adaptive params:** RSI={d['adaptive_rsi']}, "
                         f"MA=({d.get('adaptive_ma_fast')},{d.get('adaptive_ma_slow')})")

        # Patterns
        if d.get("seasonality_signal") is not None:
            lines.append(f"**Patterns:** seasonality={d['seasonality_signal']}, "
                         f"momentum={d.get('momentum_signal')}, "
                         f"S/R signal={d.get('sr_signal')}")

        # Market context
        if d.get("market_sentiment"):
            pct = d.get('pct_above_both', 0)
            pct_str = f"{pct:.0%}" if isinstance(pct, (int, float)) else str(pct)
            lines.append(f"**Market breadth:** {d['market_sentiment']} "
                         f"({pct_str} mã trên SMA10&20)")

        # Price
        if d.get("price"):
            lines.append(f"**Giá:** {d['price']:,.0f} | 52w high: {d.get('52w_high', '?'):,} "
                         f"| 52w low: {d.get('52w_low', '?'):,}")

        lines.append("\nHãy phân tích toàn diện và đưa ra khuyến nghị ngắn gọn.")
        return "\n".join(lines)

    def _build_market_prompt(self, breadth: dict, top_stocks: list) -> str:
        lines = [
            self._get_skill_context(),
            "## Nhận Định Thị Trường VN\n",
            f"**Market Breadth:** {breadth.get('pct_above_both', 0):.1%} mã trên SMA10 & SMA20",
            f"**Sentiment:** {breadth.get('sentiment', '?')}",
            f"**Signal:** {breadth.get('signal', 0):+d} (strength {breadth.get('signal_strength', 0):.2f})",
            "\n**Top mã được đề xuất:**",
        ]
        for s in top_stocks[:10]:
            lines.append(f"  - {s.get('Symbol', '?')}: điểm {s.get('Total_Score', '?')} | {s.get('Recommendation', '?')}")

        lines.append("\nNhận định ngắn gọn về thị trường và chiến lược phù hợp nhất lúc này.")
        return "\n".join(lines)

    def _build_portfolio_prompt(self, portfolio: list, market_filter: dict) -> str:
        lines = [
            self._get_skill_context(),
            "## Review Danh Mục Đầu Tư\n",
            f"**Market filter:** {market_filter.get('sentiment')} | "
            f"allow_buys={market_filter.get('allow_new_buys')} | "
            f"risk_mult={market_filter.get('risk_multiplier')}",
            "\n**Danh mục đề xuất:**",
        ]
        for p in portfolio[:10]:
            lines.append(f"  - {p.get('Symbol','?')}: {p.get('Action','?')} | "
                         f"vốn {p.get('Capital_VND','?')}")

        lines.append("\nĐánh giá danh mục này có phù hợp với sentiment thị trường hiện tại? "
                     "Gợi ý điều chỉnh nếu cần.")
        return "\n".join(lines)

    # ──────────────────────────────────────
    # API call (Gemini)
    # ──────────────────────────────────────

    def _call_ai(self, user_prompt: str) -> str:
        try:
            response = self._model.generate_content(
                user_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.MAX_TOKENS,
                    temperature=0.7,
                ),
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"[AI analysis unavailable: {e}]"

    # ──────────────────────────────────────
    # Fallback (no API key)
    # ──────────────────────────────────────

    def _fallback_analysis(self, symbol: str, d: dict) -> str:
        score = d.get("score", 0)
        rec   = d.get("recommendation", "N/A")
        return (
            f"[Rule-based] {symbol}: Điểm={score:.1f} | {rec}\n"
            f"(AI analysis yêu cầu GOOGLE_API_KEY)"
        )

    def _fallback_market(self, breadth: dict) -> str:
        s = breadth.get("sentiment", "NEUTRAL")
        p = breadth.get("pct_above_both", 0)
        return f"[Rule-based] Market Breadth: {p:.1%} → {s}"

    def _fallback_portfolio(self, portfolio: list) -> str:
        return f"[Rule-based] Danh mục gồm {len(portfolio)} mã. (AI analysis yêu cầu GOOGLE_API_KEY)"
