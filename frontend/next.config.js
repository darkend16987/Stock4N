import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"; // Giả lập component
// Trong thực tế bạn cần setup shadcn/ui hoặc dùng HTML thường. 
// Dưới đây tôi viết code thuần Tailwind cho đơn giản, không phụ thuộc thư viện UI phức tạp.

// IMPORT DỮ LIỆU
// Lưu ý: Khi deploy, đảm bảo file db.json nằm đúng chỗ
import db from '../data/db.json';

export default function Dashboard() {
    const { last_updated, analysis, portfolio, charts } = db;

    return (
        <div className="min-h-screen bg-slate-50 p-8 font-sans">
            {/* HEADER */}
            <header className="mb-8">
                <h1 className="text-3xl font-bold text-slate-900">📈 VN-Stock Intelligent Advisor</h1>
                <p className="text-slate-500">Cập nhật lần cuối: {last_updated}</p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                {/* COL 1: PORTFOLIO RECOMENDATION */}
                <div className="md:col-span-2 space-y-6">
                    <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                        <h2 className="text-xl font-semibold mb-4 text-emerald-700">💰 Danh Mục Khuyến Nghị</h2>
                        {portfolio.length > 0 ? (
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead className="bg-slate-100 text-slate-700 uppercase font-semibold">
                                        <tr>
                                            <th className="p-3">Mã</th>
                                            <th className="p-3">Hành động</th>
                                            <th className="p-3">Tỷ trọng</th>
                                            <th className="p-3">Giá Mua</th>
                                            <th className="p-3">Cắt lỗ</th>
                                            <th className="p-3">Chốt lời</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {portfolio.map((item, idx) => (
                                            <tr key={idx} className="border-b hover:bg-slate-50">
                                                <td className="p-3 font-bold">{item.Symbol}</td>
                                                <td className="p-3 text-emerald-600 font-bold">{item.Action}</td>
                                                <td className="p-3">{item['Weight_%']}</td>
                                                <td className="p-3">{item.Entry_Price}</td>
                                                <td className="p-3 text-red-500">{item.Stop_Loss}</td>
                                                <td className="p-3 text-green-500">{item.Target}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <div className="p-4 bg-yellow-50 text-yellow-800 rounded-lg">
                                ⚠️ Hiện tại thị trường rủi ro, hệ thống khuyến nghị giữ tiền mặt.
                            </div>
                        )}
                    </section>

                    {/* ANALYSIS TABLE */}
                    <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                        <h2 className="text-xl font-semibold mb-4">🏆 Bảng Xếp Hạng Thị Trường</h2>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm">
                                <thead className="bg-slate-100 text-slate-700 uppercase font-semibold">
                                    <tr>
                                        <th className="p-3">Mã</th>
                                        <th className="p-3">Tổng Điểm</th>
                                        <th className="p-3">Cơ Bản</th>
                                        <th className="p-3">Kỹ Thuật</th>
                                        <th className="p-3">Khuyến Nghị</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {analysis.slice(0, 10).map((item, idx) => (
                                        <tr key={idx} className="border-b hover:bg-slate-50">
                                            <td className="p-3 font-bold">{item.Symbol}</td>
                                            <td className="p-3">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-bold">{item.Total_Score}</span>
                                                    <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                                                        <div
                                                            className={`h-full ${item.Total_Score >= 7 ? 'bg-green-500' : item.Total_Score >= 5 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                                            style={{ width: `${item.Total_Score * 10}%` }}
                                                        ></div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="p-3">{item.Fund_Score}</td>
                                            <td className="p-3">{item.Tech_Score}</td>
                                            <td className={`p-3 font-semibold ${item.Recommendation.includes('MUA') ? 'text-green-600' : 'text-slate-500'}`}>
                                                {item.Recommendation}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>
                </div>

                {/* COL 2: SIDEBAR INFO */}
                <div className="space-y-6">
                    <div className="bg-blue-50 p-6 rounded-xl border border-blue-100">
                        <h3 className="font-bold text-blue-800 mb-2">🎯 Chiến lược</h3>
                        <p className="text-sm text-blue-700">
                            Hệ thống sử dụng chiến lược <strong>Defensive Swing Trading</strong>.
                            Ưu tiên bảo toàn vốn, chỉ giải ngân khi có sự đồng thuận giữa Cơ bản và Kỹ thuật.
                        </p>
                    </div>

                    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                        <h3 className="font-bold mb-4">📊 Top Cơ Hội</h3>
                        {analysis.slice(0, 3).map((stock) => (
                            <div key={stock.Symbol} className="mb-4 p-3 border rounded-lg">
                                <div className="flex justify-between items-center mb-1">
                                    <span className="font-bold text-lg">{stock.Symbol}</span>
                                    <span className="bg-slate-100 px-2 py-1 rounded text-xs font-mono">{stock.Total_Score}/10</span>
                                </div>
                                <p className="text-xs text-slate-500 line-clamp-2">{stock.Fund_Reason}</p>
                                <p className="text-xs text-slate-500 mt-1 italic">{stock.Tech_Reason}</p>
                            </div>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    );
}