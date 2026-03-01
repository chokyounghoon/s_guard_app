import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Phone, Menu, Plus, Send, Home, MessageSquare, BarChart2, Settings, Info, AlertTriangle, ChevronDown, ChevronUp, Users, LogOut, FileText, UserPlus, Bot, Sparkles, Zap, X } from 'lucide-react';
import AIChatBubble from '../components/AIChatBubble';
import AIThinkingIndicator from '../components/AIThinkingIndicator';
import ServerStatusChart from '../components/chat/ServerStatusChart';

export default function ChatPage() {
  const navigate = useNavigate();
  const [isLogExpanded, setIsLogExpanded] = useState(true);
  const [showPhoneList, setShowPhoneList] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [showAIAssistant, setShowAIAssistant] = useState(false);
  const [aiMessages, setAiMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [isAiThinking, setIsAiThinking] = useState(false);

  const participants = [
    { name: '정도현 팀장', role: 'Team Leader', phone: '010-1234-5678' },
    { name: '시스템 어드민', role: 'Admin', phone: '010-9876-5432' },
    { name: '최광훈 담당', role: 'Developer', phone: '010-5555-5555' },
    { name: '이수민 매니저', role: 'Manager', phone: '010-1111-2222' },
    { name: '김철수 사원', role: 'Staff', phone: '010-3333-4444' },
    { name: '박영희 대리', role: 'Assistant', phone: '010-7777-8888' },
  ];

  // Main Chat State
  const [mainMessages, setMainMessages] = useState([
    {
      id: 1,
      type: 'other',
      sender: '정도현 팀장',
      role: 'Team Leader',
      initials: 'JD',
      color: 'bg-slate-700',
      text: '현재 Server-02에서 포트 8080 타임아웃 오류가 발생했습니다. 확인 가능하신 분 있나요?',
      time: '13:42'
    },
    {
      id: 2,
      type: 'other',
      sender: '시스템 어드민',
      role: 'Admin',
      initials: 'SA',
      color: 'bg-blue-900/40 border border-blue-500/20 text-blue-400',
      text: '네, 로그 확인 결과 아래와 같은 오류가 발생하고 있습니다.',
      time: '13:45'
    },
    {
      id: 3,
      type: 'other',
      sender: '시스템 어드민',
      role: 'Admin',
      initials: 'SA',
      color: 'bg-blue-900/40 border border-blue-500/20 text-blue-400',
      text: '상단 로그 배너를 참고해주세요. DB Connection Pool 이슈로 보입니다.',
      time: '13:45'
    },
    {
      id: 4,
      type: 'me',
      text: '제가 지금 유휴 세션 초기화 작업 진행하겠습니다. 작업 완료 후 보고 드리겠습니다.',
      time: '13:46'
    },
    {
      id: 5,
      type: 'system',
      text: '사용자가 <span class="text-blue-400 font-semibold underline underline-offset-4 decoration-blue-500/40">임시 복구 작업</span>을 시작했습니다.',
      icon: Info
    }
  ]);
  const [mainInput, setMainInput] = useState('');

  const handleCall = (phoneNumber) => {
    window.location.href = `tel:${phoneNumber}`;
    setShowPhoneList(false);
  };

  // AI Assistant Logic
  const quickActions = [
    { id: 'status', label: '현재 서버 상태 알려줘', icon: BarChart2 },
    { id: 'error', label: '이 에러 원인 분석해줘', icon: AlertTriangle },
    { id: 'history', label: '유사 장애 이력 찾아줘', icon: FileText },
    { id: 'action', label: '조치 방법 추천해줘', icon: Zap }
  ];

  const detectIntent = (message) => {
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('상태') || lowerMessage.includes('어때') || lowerMessage.includes('괜찮')) return 'status';
    if (lowerMessage.includes('에러') || lowerMessage.includes('왜') || lowerMessage.includes('원인')) return 'error';
    if (lowerMessage.includes('전에') || lowerMessage.includes('과거') || lowerMessage.includes('이전') || lowerMessage.includes('이력')) return 'history';
    if (lowerMessage.includes('어떻게') || lowerMessage.includes('조치') || lowerMessage.includes('해결') || lowerMessage.includes('방법')) return 'action';
    if (lowerMessage.includes('cpu') || lowerMessage.includes('높')) return 'cpu_analysis';
    if (lowerMessage.includes('db') || lowerMessage.includes('데이터베이스') || lowerMessage.includes('connection')) return 'db_analysis';
    return 'general';
  };

  const getAIResponse = (intent, userMessage) => {
    const responses = {
      status: {
        text: "결제 서버 현재 상태를 확인했습니다.\n\n**✅ 정상 운영 중**\n- CPU: 68% (안정)\n- Memory: 72% (안정)\n- Response Time: 180ms (평균)\n- Error Rate: 0.02%\n\n지난 1시간 동안 특이사항 없습니다.",
        metrics: { cpu: 68, memory: 72, responseTime: 180 },
        confidence: 98
      },
      error: {
        text: "Timeout 에러의 원인을 분석했습니다.\n\n**에러 타입**: DB Connection Timeout\n**발생 빈도**: 지난 1시간 동안 47건\n\n**주요 원인**:\n- Connection Pool 고갈 (현재 95% 사용 중)\n- 장기 실행 쿼리 3건 감지 (평균 15초 소요)\n\n**유사 사례**: 3개월 전 [INC-2025-11-15] 사례와 95% 일치",
        confidence: 95
      },
      history: {
        text: "과거 유사 장애 이력을 검색했습니다.\n\n**🔍 검색 결과: 4건**\n\n**1. DB Connection Pool 고갈** (95% 유사)\n- 발생: 2025-11-15 14:32\n- 조치: Pool Size 200→500 증설\n- 해결 시간: 23분\n\n**2. 배치 프로세스 무한 루프** (88% 유사)\n- 발생: 2025-09-22 09:15\n- 조치: 루프 탈출 조건 추가\n- 해결 시간: 1시간 15분\n\nAI Report 페이지에서 전체 이력을 확인하실 수 있습니다.",
        confidence: 92
      },
      action: {
        text: "권장 조치 방법을 제시합니다.\n\n**🛠️ 단계별 조치 가이드**\n\n**1️⃣ 즉시 조치 (긴급)**\n```bash\n# Connection Pool 임시 증설\nvim /etc/app/database.conf\nmax_connections=500\nsudo systemctl restart app-server\n```\n\n**2️⃣ 근본 원인 해결**\n```bash\n# 느린 쿼리 확인\nmysql -e \"SHOW FULL PROCESSLIST;\"\n# 장기 실행 세션 종료\nmysql -e \"KILL <session_id>;\"\n```\n\n**3️⃣ 모니터링 강화**\n- Connection Pool 사용률 알림 설정 (>85%)\n- 쿼리 실행 시간 로깅 활성화\n\n**⏱️ 예상 소요 시간**: 15~20분",
        confidence: 94
      },
      cpu_analysis: {
        text: "CPU 사용률 급증 원인을 다각도로 분석했습니다.\n\n**🔍 분석 결과**:\n**1. 프로세스**: `batch_processor_v2`가 CPU 92% 점유\n**2. 패턴**: 무한 루프 의심 (메모리 증가 + CPU 고정)\n**3. 시작 시간**: 약 15분 전 (14:17경)\n\n**🛠️ 권장 조치 순서**:\n**1️⃣ 프로세스 상태 확인**\n```bash\nps aux | grep batch_processor\ntop -p $(pgrep batch_processor)\n```\n\n**2️⃣ 로그 확인**\n```bash\ntail -f /var/log/batch_errors.log\n```\n\n**3️⃣ 긴급 대응 (심각 시)**\n```bash\nsudo systemctl restart batch_processor_v2\n```\n\n**⏱️ 조치 안하면**: 5~10분 내 서비스 중단 가능성 85%",
        metrics: { cpu: 92, memory: 78, responseTime: 350 },
        confidence: 95
      },
      db_analysis: {
        text: "DB 서버 상태를 실시간 분석했습니다.\n\n**⚠️ 주의 필요**\n- Connection Pool: 85% (높음)\n- Active Connections: 170/200\n- Slow Query Count: 23건 (지난 10분)\n- Lock Wait Time: 평균 2.3초\n\n**권장 조치**: Connection Pool 크기 증설을 고려하세요.\n```bash\n# /etc/mysql/my.cnf\nmax_connections=400\nwait_timeout=300\n```\n\n**예상 효과**: 병목 현상 해소, 응답 시간 30% 개선",
        metrics: { cpu: 45, memory: 52, responseTime: 850 },
        confidence: 97
      },
      general: {
        text: `"${userMessage}"에 대한 정보를 찾고 있습니다.\n\n현재 War-Room에서 다루고 있는 **INC-8823 (CRITICAL)** 장애와 관련된 정보를 제공해 드릴 수 있습니다.\n\n다음과 같은 질문을 시도해 보세요:\n- "현재 서버 상태 어때?"\n- "이 에러 왜 나는 거야?"\n- "DB 연결 풀 어떻게 늘려?"\n- "CPU가 높은 이유가 뭐야?"`,
        confidence: 85
      }
    };

    return responses[intent] || responses.general;
  };

  const handleAIMessage = async (message) => {
    if (!message.trim()) return;

    // Add user message
    const userMessage = {
      type: 'user',
      text: message,
      timestamp: new Date()
    };
    
    setAiMessages(prev => [...prev, userMessage]);
    setUserInput('');
    setIsAiThinking(true);

    try {
      const apiResponse = await fetch('http://localhost:8000/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: message })
      });
      
      if (!apiResponse.ok) {
        throw new Error(`API Error: ${apiResponse.status}`);
      }
      
      const data = await apiResponse.json();
      
      const aiMessage = {
        type: 'ai',
        text: data.response,
        // We can structure the AI response and optionally add 'related_logs' logic if needed
        timestamp: new Date()
      };

      setAiMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error("Failed to connect to AI backend:", error);
      const errorMessage = {
        type: 'ai',
        text: "현재 AI 에이전트 서비스 응답이 지연되고 있거나 연결할 수 없습니다. 서버 상태를 확인해주세요.",
        timestamp: new Date()
      };
      setAiMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsAiThinking(false);
    }
  };

  const handleQuickAction = (action) => {
    handleAIMessage(action.label);
  };

  const handleCopyMessage = (text) => {
    navigator.clipboard.writeText(text);
    alert('메시지가 클립보드에 복사되었습니다.');
  };

  const handleShareToTeam = (text) => {
    const newMessage = {
      id: Date.now(),
      type: 'me',
      text: `[AI Analysis Shared]\n\n${text}`,
      time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
    };
    setMainMessages(prev => [...prev, newMessage]);
    setShowAIAssistant(false);
  };

  const handleMainSendMessage = () => {
    if (!mainInput.trim()) return;
    const newMessage = {
      id: Date.now(),
      type: 'me',
      text: mainInput,
      time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
    };
    setMainMessages(prev => [...prev, newMessage]);
    setMainInput('');
  };

  return (
    <div className="min-h-screen bg-[#0f1421] text-white font-sans flex flex-col pb-20 relative">
      {/* Header */}
      <header className="flex justify-between items-center p-4 sticky top-0 bg-[#0f1421]/90 backdrop-blur-md z-50 border-b border-white/5">
        <div className="flex items-center space-x-3">
          <button onClick={() => navigate(-1)} className="p-1 rounded-full hover:bg-white/10 transition-colors">
            <ArrowLeft className="w-6 h-6 text-white" />
          </button>
          <div className="flex flex-col">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg">INC-8823</span>
              <span className="bg-red-500/20 text-red-500 text-[10px] font-bold px-2 py-0.5 rounded border border-red-500/30 uppercase tracking-tighter">
                CRITICAL
              </span>
            </div>
            <span className="text-slate-400 text-xs">장애 협업 채팅방 ({participants.length}명)</span>
          </div>
        </div>
        <div className="flex items-center space-x-4 relative">
          <button 
            onClick={() => { setShowPhoneList(!showPhoneList); setShowMenu(false); }}
            className={`p-1.5 rounded-full transition-colors ${showPhoneList ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-white/10 text-slate-300'}`}
          >
            <Phone className="w-5 h-5" />
          </button>
          
          {/* Phone List Dropdown */}
          {showPhoneList && (
            <div className="absolute top-12 right-0 w-64 bg-[#1a1f2e] border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50">
                <div className="p-3 border-b border-white/5 bg-[#11141d]">
                    <span className="text-xs font-bold text-slate-300">통화 대상 선택</span>
                </div>
                <div className="max-h-60 overflow-y-auto">
                    {participants.map((person, index) => (
                        <div key={index} onClick={() => handleCall(person.phone)} className="flex items-center justify-between p-3 hover:bg-white/5 cursor-pointer transition-colors border-b border-white/5 last:border-0">
                            <div className="flex items-center space-x-3">
                                <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold">
                                    {person.name[0]}
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-sm text-white">{person.name}</span>
                                    <span className="text-[10px] text-slate-500">{person.role}</span>
                                </div>
                            </div>
                            <Phone className="w-4 h-4 text-green-500" />
                        </div>
                    ))}
                </div>
            </div>
          )}

          <button 
            onClick={() => { setShowMenu(!showMenu); setShowPhoneList(false); }}
            className={`p-1.5 rounded-full transition-colors ${showMenu ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-white/10 text-slate-300'}`}
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Menu Dropdown */}
          {showMenu && (
            <div className="absolute top-12 right-0 w-48 bg-[#1a1f2e] border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50">
                <div 
                    onClick={() => { alert('사용자 초대 기능이 실행됩니다.'); setShowMenu(false); }}
                    className="flex items-center space-x-3 p-3 hover:bg-white/5 cursor-pointer transition-colors border-b border-white/5"
                >
                    <UserPlus className="w-4 h-4 text-blue-400" />
                    <span className="text-sm text-slate-200">초대하기</span>
                </div>
                <div 
                    onClick={() => { if(confirm('대화방을 나가시겠습니까?')) navigate('/dashboard'); }}
                    className="flex items-center space-x-3 p-3 hover:bg-red-500/10 cursor-pointer transition-colors"
                >
                    <LogOut className="w-4 h-4 text-red-400" />
                    <span className="text-sm text-red-400">나가기</span>
                </div>
            </div>
          )}
        </div>
      </header>

      {/* Persistent Error Log Banner (Collapsible) */}
      <div className="bg-red-950/10 border-b border-red-500/10 backdrop-blur-sm z-30 sticky top-[73px]">
        <div className="px-4 py-2">
            <div 
                onClick={() => setIsLogExpanded(!isLogExpanded)}
                className="flex items-center justify-between cursor-pointer group"
            >
                <div className="flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 text-red-500 animate-pulse" />
                    <span className="text-xs font-bold text-red-400">🚨 현재 발생 중인 장애 (Ongoing Issue)</span>
                </div>
                <button className="p-1 rounded-full group-hover:bg-red-500/10 transition-colors">
                    {isLogExpanded ? <ChevronUp className="w-4 h-4 text-red-400" /> : <ChevronDown className="w-4 h-4 text-red-400" />}
                </button>
            </div>
            
            {isLogExpanded && (
                <div className="bg-[#0d0f14] rounded-lg border border-red-500/20 overflow-hidden mt-2 mb-1 animate-in slide-in-from-top-2 duration-200">
                    <div className="bg-red-900/10 px-3 py-1.5 border-b border-red-500/10 flex justify-between items-center">
                    <span className="text-[10px] text-red-300 font-mono">system_err.log</span>
                    <span className="text-[10px] text-red-400/70">Live Stream</span>
                    </div>
                    <div className="p-3 text-[11px] font-mono leading-relaxed">
                    <p className="text-red-400"><span className="font-bold">Error:</span> Connection timed out at port 8080.</p>
                    <p className="text-yellow-200/80 mt-1"><span className="font-bold text-yellow-500">Caused by:</span> java.net.ConnectException: Connection refused</p>
                    </div>
                </div>
            )}
        </div>
      </div>

      {/* Chat Area */}
      <main className="flex-1 p-4 space-y-6 overflow-y-auto pb-40">
        {/* Date Divider */}
        <div className="flex justify-center my-4">
          <div className="bg-slate-800/40 text-slate-400 text-[11px] px-4 py-1 rounded-full">
            2023년 10월 25일 수요일
          </div>
        </div>

        {mainMessages.map((msg) => (
          <div key={msg.id}>
            {msg.type === 'other' && (
              <div className="flex items-start space-x-3 mb-4">
                <div className={`w-10 h-10 rounded-xl ${msg.color} flex items-center justify-center font-bold text-sm shrink-0`}>
                  {msg.initials}
                </div>
                <div className="flex flex-col space-y-1">
                  <span className="text-xs text-slate-400 font-medium">{msg.sender}</span>
                  <div className="flex items-end space-x-2">
                    <div className="bg-slate-800/80 rounded-2xl rounded-tl-none px-4 py-2.5 max-w-[280px] text-[15px] leading-relaxed whitespace-pre-wrap">
                      {msg.text}
                    </div>
                    <span className="text-[10px] text-slate-500 pb-1">{msg.time}</span>
                  </div>
                </div>
              </div>
            )}

            {msg.type === 'me' && (
              <div className="flex flex-col items-end space-y-1 mb-4">
                <div className="flex items-end space-x-2">
                  <span className="text-[10px] text-slate-500 pb-1">{msg.time}</span>
                  <div className="bg-blue-600 rounded-2xl rounded-tr-none px-4 py-3 max-w-[280px] text-[15px] leading-relaxed shadow-lg shadow-blue-900/20 whitespace-pre-wrap">
                    {msg.text}
                  </div>
                </div>
              </div>
            )}

            {msg.type === 'system' && (
              <div className="flex justify-center mt-8 mb-8">
                <div className="bg-slate-800/30 border border-white/5 rounded-xl px-4 py-2.5 flex items-center space-x-3 max-w-[320px]">
                  <div className="p-1.5 bg-blue-500/20 rounded-full">
                     <msg.icon className="w-4 h-4 text-blue-400" />
                  </div>
                  <p className="text-[13px] text-slate-300" dangerouslySetInnerHTML={{ __html: msg.text }} />
                </div>
              </div>
            )}
          </div>
        ))}
      </main>
    
      {/* AI Assistant Panel */}
      {showAIAssistant && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" onClick={() => setShowAIAssistant(false)}>
          <div 
            className="absolute right-0 top-0 h-full w-full max-w-md bg-[#0f1421] border-l border-white/10 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* AI Panel Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10 bg-gradient-to-r from-purple-900/20 to-blue-900/20">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center shadow-lg">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-white">AI Assistant</h3>
                  <p className="text-[10px] text-slate-400">S-Autopilot 실시간 분석</p>
                </div>
              </div>
              <button
                onClick={() => setShowAIAssistant(false)}
                className="p-2 hover:bg-white/10 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            {/* Quick Actions */}
            {aiMessages.length === 0 && (
              <div className="p-4 space-y-3 border-b border-white/5">
                <p className="text-xs text-slate-400 mb-2">💡 빠른 질문</p>
                <div className="grid grid-cols-2 gap-2">
                  {quickActions.map((action) => (
                    <button
                      key={action.id}
                      onClick={() => handleQuickAction(action)}
                      className="flex items-center space-x-2 p-3 bg-gradient-to-br from-slate-800/60 to-slate-900/60 hover:from-purple-900/30 hover:to-blue-900/30 border border-white/5 hover:border-purple-500/30 rounded-xl text-left transition-all group"
                    >
                      <action.icon className="w-4 h-4 text-purple-400 group-hover:text-purple-300 flex-shrink-0" />
                      <span className="text-[11px] text-slate-300 leading-tight">{action.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* AI Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              {aiMessages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center space-y-3">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-600/20 to-blue-600/20 flex items-center justify-center border border-purple-500/20">
                    <Bot className="w-8 h-8 text-purple-400" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white mb-1">AI와 대화를 시작하세요</h4>
                    <p className="text-xs text-slate-400 leading-relaxed max-w-xs">
                      서버 상태, 에러 원인, 조치 방법 등<br/>무엇이든 물어보세요!
                    </p>
                  </div>
                </div>
              )}

              {aiMessages.map((msg, index) => (
                <div key={index}>
                  {msg.type === 'user' ? (
                    <div className="flex flex-col items-end space-y-1">
                      <div className="bg-blue-600 rounded-2xl rounded-tr-none px-4 py-3 max-w-[85%] text-sm leading-relaxed shadow-lg shadow-blue-900/20">
                        {msg.text}
                      </div>
                      <span className="text-[10px] text-slate-500">
                        {msg.timestamp.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  ) : (
                    <>
                      <AIChatBubble 
                        message={msg}
                        onCopy={handleCopyMessage}
                        onShare={handleShareToTeam}
                      />
                      {msg.metrics && (
                        <div className="ml-10 max-w-[85%] mt-2 animate-fade-in-up">
                            <ServerStatusChart />
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}

              {isAiThinking && <AIThinkingIndicator />}
            </div>

            {/* AI Input Area */}
            <div className="p-3 border-t border-white/10 bg-[#0a0d14]">
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAIMessage(userInput)}
                  placeholder="AI에게 질문하세요..."
                  className="flex-1 bg-slate-800/60 rounded-full py-2.5 px-4 text-sm border border-white/5 focus:outline-none focus:border-purple-500/50 transition-all placeholder:text-slate-500"
                />
                <button
                  onClick={() => handleAIMessage(userInput)}
                  disabled={!userInput.trim()}
                  className="p-2.5 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white shadow-lg shadow-purple-900/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* New Analysis Action Bar */}
      <div className="px-4 pb-2 bg-[#0f1421]">
        <button 
            onClick={() => navigate('/ai-process-report')}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-blue-900/30 flex items-center justify-center space-x-2 transition-all active:scale-[0.98]"
        >
            <Settings className="w-5 h-5 animate-spin-slow" />
            <span>AI 처리 분석 및 결과 보고서 생성</span>
        </button>
      </div>

      {/* Input Area */}
      <div className="p-3 bg-[#0f1421] border-t border-white/5 flex items-center space-x-3 mb-[70px]">
        <button className="p-2.5 rounded-full bg-slate-800/60 hover:bg-slate-700 transition-colors">
          <Plus className="w-6 h-6 text-slate-400" />
        </button>
        <div className="flex-1 relative">
           <input 
             type="text" 
             value={mainInput}
             onChange={(e) => setMainInput(e.target.value)}
             onKeyPress={(e) => e.key === 'Enter' && handleMainSendMessage()}
             placeholder="메시지를 입력하세요..." 
             className="w-full bg-slate-800/60 rounded-full py-2.5 px-5 text-[15px] border border-white/5 focus:outline-none focus:border-blue-500/50 transition-all placeholder:text-slate-500"
           />
           <button 
             onClick={handleMainSendMessage}
             disabled={!mainInput.trim()}
             className="absolute right-1 top-1 p-1.5 rounded-full bg-blue-600 text-white shadow-lg shadow-blue-900/40 disabled:opacity-50 disabled:cursor-not-allowed"
           >
              <Send className="w-5 h-5 fill-current" />
           </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="fixed bottom-0 left-0 w-full bg-[#0f1421] border-t border-white/5 px-6 py-3 flex justify-between items-center z-50 pb-safe">
        <div className="flex flex-col items-center space-y-1 text-slate-500 hover:text-white transition-colors cursor-pointer" onClick={() => navigate('/dashboard')}>
            <Home className="w-6 h-6" />
            <span className="text-[10px] font-medium">홈</span>
        </div>
        <div className="flex flex-col items-center space-y-1 text-blue-500 relative cursor-pointer" onClick={() => navigate('/chat')}>
            <div className="relative">
                <MessageSquare className="w-6 h-6" />
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-[#0f1421]"></span>
            </div>
            <span className="text-[10px] font-medium">War-Room</span>
        </div>

        <div className="flex flex-col items-center space-y-1 text-slate-500 hover:text-white transition-colors cursor-pointer">
            <BarChart2 className="w-6 h-6" />
            <span className="text-[10px] font-medium">통계</span>
        </div>
        
        {/* AI Assistant Nav Button */}
        <div 
          className={`flex flex-col items-center space-y-1 transition-colors cursor-pointer ${
            showAIAssistant ? 'text-purple-400' : 'text-slate-500 hover:text-purple-400'
          }`}
          onClick={() => setShowAIAssistant(!showAIAssistant)}
        >
            <div className="relative">
              <Bot className="w-6 h-6" />
              {!showAIAssistant && (
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-purple-500 rounded-full border-2 border-[#0f1421] animate-pulse"></span>
              )}
            </div>
            <span className="text-[10px] font-medium">AI</span>
        </div>
        
        <div className="flex flex-col items-center space-y-1 text-slate-500 hover:text-white transition-colors cursor-pointer">
            <Settings className="w-6 h-6" />
            <span className="text-[10px] font-medium">설정</span>
        </div>
      </nav>
    </div>
  );
}
