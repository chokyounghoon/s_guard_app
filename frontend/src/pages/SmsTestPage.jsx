import React, { useState } from 'react';
import { Send, AlertTriangle, CheckCircle, Terminal } from 'lucide-react';

const SmsTestPage = () => {
    const [sender, setSender] = useState('010-9999-8888');
    const [message, setMessage] = useState('');
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(false);

    const predefinedMessages = [
        { label: 'DB Connection Error', text: 'payment API timeout 및 database connection pool error 발생' },
        { label: 'Network Timeout', text: 'gateway 504 timeout error in user service' },
        { label: 'CPU Overload', text: 'CRITICAL: batch server CPU utilization reached 99%' }
    ];

    const handleSend = async (e) => {
        e?.preventDefault();
        if (!message.trim()) return;

        setIsLoading(true);
        const newLog = {
            time: new Date().toLocaleTimeString(),
            type: 'request',
            text: `전송 중... (${message})`
        };
        setLogs(prev => [newLog, ...prev]);

        try {
            // Cloudflare Worker API
            const apiUrl = 'https://sguard-sms-api.khcho0421.workers.dev/sms/receive';

            const payload = {
                sender,
                message,
                received_at: new Date().toISOString()
            };

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                setLogs(prev => [{
                    time: new Date().toLocaleTimeString(),
                    type: 'success',
                    text: `전송 성공! (Status: ${data.status})`
                }, ...prev]);
                setMessage(''); // Clear input after success
            } else {
                throw new Error(data.error || 'API Request Failed');
            }
        } catch (error) {
            setLogs(prev => [{
                time: new Date().toLocaleTimeString(),
                type: 'error',
                text: `전송 실패: ${error.message}`
            }, ...prev]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#0f111a] text-white p-8">
            <div className="max-w-4xl mx-auto space-y-8">

                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold flex items-center mb-2">
                        <Terminal className="w-8 h-8 mr-3 text-blue-400" />
                        S-Guard SMS 통합 테스트
                    </h1>
                    <p className="text-slate-400">
                        대시보드 Live Incident Stream 및 AI War-Room 에 데이터를 공급하기 위한 테스트 송신 도구입니다.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

                    {/* Left Column: Form & Presets */}
                    <div className="space-y-6">

                        <div className="bg-[#1a1f2e] border border-white/5 rounded-2xl p-6">
                            <h2 className="text-xl font-bold mb-4 flex items-center">
                                <Send className="w-5 h-5 mr-2 text-blue-400" />
                                커스텀 메시지 전송
                            </h2>

                            <form onSubmit={handleSend} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-400 mb-1">발신번호 (Sender)</label>
                                    <input
                                        type="text"
                                        value={sender}
                                        onChange={(e) => setSender(e.target.value)}
                                        className="w-full bg-[#0a0c10] border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-400 mb-1">메시지 내용 (Payload)</label>
                                    <textarea
                                        value={message}
                                        onChange={(e) => setMessage(e.target.value)}
                                        rows="4"
                                        placeholder="예: database connection pool error"
                                        className="w-full bg-[#0a0c10] border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500 resize-none"
                                        required
                                    />
                                </div>

                                <button
                                    type="submit"
                                    disabled={isLoading || !message.trim()}
                                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center transition-colors shadow-lg shadow-blue-500/20"
                                >
                                    {isLoading ? '전송 중...' : '대시보드로 전송하기'}
                                    {!isLoading && <Send className="w-4 h-4 ml-2" />}
                                </button>
                            </form>
                        </div>

                        <div className="bg-[#1a1f2e] border border-white/5 rounded-2xl p-6">
                            <h2 className="text-xl font-bold mb-4 flex items-center">
                                <AlertTriangle className="w-5 h-5 mr-2 text-orange-400" />
                                빠른 테스트 (Preset)
                            </h2>
                            <div className="space-y-3">
                                {predefinedMessages.map((preset, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => setMessage(preset.text)}
                                        className="w-full text-left bg-[#0a0c10] hover:bg-white/5 border border-white/10 rounded-lg p-3 transition-colors"
                                    >
                                        <div className="text-sm font-medium text-blue-400 mb-1">{preset.label}</div>
                                        <div className="text-sm text-slate-300 truncate">{preset.text}</div>
                                    </button>
                                ))}
                            </div>
                        </div>

                    </div>

                    {/* Right Column: Execution Logs */}
                    <div className="bg-[#1a1f2e] border border-white/5 rounded-2xl p-6 flex flex-col h-[600px]">
                        <h2 className="text-xl font-bold mb-4 flex items-center">
                            <CheckCircle className="w-5 h-5 mr-2 text-green-400" />
                            실시간 전송 로그
                        </h2>

                        <div className="flex-1 bg-[#0a0c10] border border-white/5 rounded-xl p-4 overflow-y-auto font-mono text-sm space-y-2">
                            {logs.length === 0 ? (
                                <div className="text-slate-500 text-center mt-10">
                                    전송 로그가 여기에 표시됩니다.
                                </div>
                            ) : (
                                logs.map((log, idx) => (
                                    <div key={idx} className="flex flex-col border-b border-white/5 pb-2 last:border-0">
                                        <span className="text-slate-500 text-xs mb-1">[{log.time}]</span>
                                        <span className={`
                      ${log.type === 'error' ? 'text-red-400' : ''}
                      ${log.type === 'success' ? 'text-green-400' : ''}
                      ${log.type === 'request' ? 'text-blue-400' : ''}
                    `}>
                                            {log.text}
                                        </span>
                                    </div>
                                ))
                            )}
                        </div>

                        <div className="mt-4 pt-4 border-t border-white/10">
                            <a
                                href="/#/dashboard"
                                target="_blank"
                                rel="noreferrer"
                                className="text-blue-400 hover:text-blue-300 text-sm font-medium flex items-center justify-center transition-colors"
                            >
                                내 대시보드 바로가기 →
                            </a>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default SmsTestPage;
