import React, { useState, useEffect, useRef } from 'react';
import { Brain, Activity, MessageSquare, Zap, Users, AlertTriangle } from 'lucide-react';

const API_BASE_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://api.chokerslab.store';

export default function AiInsightPanel({ onLogReceived, onShowDetail, selectedSms, onOpenWarRoom }) {
  const [insightData, setInsightData] = useState({
    status: 'active',
    current_log: { type: 'info', text: 'AI 엔진 연결 중...' }
  });
  const [displayedText, setDisplayedText] = useState('');
  const [isAnalyzingSms, setIsAnalyzingSms] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [isCritical, setIsCritical] = useState(false);
  const [smsAnalysisTitle, setSmsAnalysisTitle] = useState('');

  // 타이핑 애니메이션 함수
  const typeText = (text, onDone) => {
    setDisplayedText('');
    let charIndex = 0;
    const interval = setInterval(() => {
      if (charIndex <= text.length) {
        setDisplayedText(text.slice(0, charIndex));
        charIndex++;
      } else {
        clearInterval(interval);
        if (onDone) onDone();
      }
    }, 30);
    return interval;
  };

  // SMS 선택 시 분석 모드로 전환
  useEffect(() => {
    if (!selectedSms) {
      setIsAnalyzingSms(false);
      setAnalysisComplete(false);
      setIsCritical(false);
      return;
    }

    setIsAnalyzingSms(true);
    setAnalysisComplete(false);
    setIsCritical(false);
    setSmsAnalysisTitle(`분석 중: "${selectedSms.sender}" 발신 SMS`);
    setDisplayedText('');

    const analyze = async () => {
      typeText(`📡 SMS 수신 분석 시작... 발신: ${selectedSms.sender}`);
      await new Promise(r => setTimeout(r, 1500));

      setDisplayedText('🔍 RAG 지식베이스에서 유사 장애 사례 검색 중...');
      try {
        const res = await fetch(`${API_BASE_URL}/ai/analyze-sms`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sender: selectedSms.sender, message: selectedSms.message }),
        });

        let analysisText;
        if (res.ok) {
          const data = await res.json();
          analysisText = data.analysis || data.answer || data.text || '분석 완료.';
        } else {
          analysisText = buildLocalAnalysis(selectedSms.message);
        }

        await new Promise(r => setTimeout(r, 500));

        const critical = isCriticalAnalysis(analysisText, selectedSms.message);
        setIsCritical(critical);

        typeText(`✅ ${analysisText}`, () => {
          setAnalysisComplete(true);
        });

        if (onLogReceived) {
          onLogReceived({
            title: `SMS 장애 분석: ${selectedSms.sender}`,
            text: analysisText,
            message: analysisText,
            severity: critical ? 'CRITICAL' : 'INFO',
            category: getCategoryFromAnalysis(analysisText, selectedSms.message)
          });
        }
      } catch {
        const localAnalysis = buildLocalAnalysis(selectedSms.message);
        const critical = isCriticalAnalysis(localAnalysis, selectedSms.message);
        setIsCritical(critical);
        typeText(`⚡ ${localAnalysis}`, () => {
          setAnalysisComplete(true);
        });
      }
    };

    analyze();
  }, [selectedSms]);

  const isCriticalAnalysis = (analysisText, message) => {
    const combined = ((analysisText || '') + (message || '')).toLowerCase();
    return combined.includes('critical') || combined.includes('escalation') ||
           combined.includes('에스컬레이션') || combined.includes('war-room') ||
           combined.includes('워룸') || combined.includes('db') ||
           combined.includes('데이터베이스') || combined.includes('서버 다운') ||
           combined.includes('down');
  };

  const getCategoryFromAnalysis = (analysisText, message) => {
    const combined = ((analysisText || '') + (message || '')).toLowerCase();
    if (combined.includes('security') || combined.includes('보안') || combined.includes('접속 시도') || combined.includes('로그인')) {
      return 'security';
    }
    if (combined.includes('critical') || combined.includes('긴급') || combined.includes('장애')) {
      return 'critical';
    }
    if (combined.includes('server') || combined.includes('서버') || combined.includes('cpu') || combined.includes('memory')) {
      return 'server';
    }
    return 'report';
  };

  const buildLocalAnalysis = (message) => {
    const msg = (message || '').toLowerCase();
    if (msg.includes('critical') || msg.includes('db') || msg.includes('데이터베이스')) {
      return 'CRITICAL 등급 감지. 데이터베이스 관련 장애 패턴과 일치합니다. 즉시 DBA 팀 에스컬레이션 및 War-Room 개설을 권장합니다.';
    } else if (msg.includes('cpu') || msg.includes('메모리') || msg.includes('memory')) {
      return '리소스 과부하 패턴 감지. 해당 서버의 프로세스 목록 및 배치 잡 스케줄을 즉시 확인하세요. War-Room 개설을 권장합니다.';
    } else if (msg.includes('down') || msg.includes('접속') || msg.includes('서버')) {
      return '서버 다운 패턴 감지. 헬스체크 엔드포인트 및 로드밸런서 상태 확인을 권장합니다. War-Room 개설을 권장합니다.';
    } else if (msg.includes('복구') || msg.includes('정상')) {
      return '복구 완료 신호 수신. 서비스 정상화 여부를 모니터링하고 사후 Post-Mortem을 준비하세요.';
    }
    return '수신 메시지 분석 완료. 특이 키워드가 감지되지 않았습니다. 상황을 계속 모니터링합니다.';
  };

  // 기본 폴링 루프 (SMS 미선택 시)
  useEffect(() => {
    if (isAnalyzingSms) return;

    let isCancelled = false;
    const startTypingCycle = async () => {
      setDisplayedText('');
      try {
        const res = await fetch(`${API_BASE_URL}/ai/insight`);
        let logText = '분석 데이터 대기 중...';
        if (res.ok) {
          const data = await res.json();
          setInsightData(data);
          if (onLogReceived && data.current_log) onLogReceived(data.current_log, data.prediction_counts);
          logText = data.current_log?.text || logText;
        }
        if (isCancelled) return;
        let charIndex = 0;
        const interval = setInterval(() => {
          if (isCancelled) { clearInterval(interval); return; }
          if (charIndex <= logText.length) {
            setDisplayedText(logText.slice(0, charIndex));
            charIndex++;
          } else {
            clearInterval(interval);
            if (!isCancelled) setTimeout(startTypingCycle, 5000);
          }
        }, 50);
      } catch {
        if (!isCancelled) setTimeout(startTypingCycle, 7000);
      }
    };

    startTypingCycle();
    return () => { isCancelled = true; };
  }, [isAnalyzingSms]);

  const handleOpenWarRoom = () => {
    if (onOpenWarRoom && selectedSms) {
      onOpenWarRoom(selectedSms, displayedText);
    }
  };

  const currentLog = insightData.current_log || { type: 'info' };
  const textColor = isAnalyzingSms
    ? (isCritical ? 'text-red-300' : 'text-yellow-300')
    : currentLog.type === 'insight' ? 'text-yellow-300 font-bold'
    : currentLog.type === 'warning' ? 'text-orange-400'
    : currentLog.type === 'success' ? 'text-emerald-400'
    : 'text-blue-200';

  return (
    <div className={`bg-gradient-to-br from-[#1a1f2e] to-[#11141d] rounded-3xl p-6 border shadow-xl relative overflow-hidden group transition-all duration-500
      ${isAnalyzingSms && isCritical ? 'border-red-500/30' : isAnalyzingSms ? 'border-yellow-500/20' : 'border-blue-500/20'}`}>
      <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none" />

      {/* 헤더 */}
      <div className="flex items-start justify-between mb-4 relative z-10">
        <div className="flex items-center space-x-3">
          <div className={`p-2.5 rounded-xl border ${isAnalyzingSms && isCritical ? 'bg-red-500/20 border-red-500/30' : isAnalyzingSms ? 'bg-yellow-500/20 border-yellow-500/30' : 'bg-blue-600/20 border-blue-500/30'}`}>
            {isAnalyzingSms && isCritical
              ? <AlertTriangle className="w-6 h-6 text-red-400 animate-pulse" />
              : isAnalyzingSms
              ? <MessageSquare className="w-6 h-6 text-yellow-400 animate-pulse" />
              : <Brain className="w-6 h-6 text-blue-400 animate-pulse" />
            }
          </div>
          <div>
            <h2 className="font-bold text-lg text-white flex items-center gap-2">
              S-Autopilot Insight
              <span className="flex h-2 w-2 relative">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isAnalyzingSms && isCritical ? 'bg-red-400' : isAnalyzingSms ? 'bg-yellow-400' : 'bg-blue-400'}`}></span>
                <span className={`relative inline-flex rounded-full h-2 w-2 ${isAnalyzingSms && isCritical ? 'bg-red-500' : isAnalyzingSms ? 'bg-yellow-500' : 'bg-blue-500'}`}></span>
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              {isAnalyzingSms ? smsAnalysisTitle : '실시간 인공지능 분석 스트림'}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {isAnalyzingSms && (
            <div className={`px-3 py-1.5 rounded-lg flex items-center space-x-2 border ${isCritical ? 'bg-red-500/10 border-red-500/30' : 'bg-yellow-500/10 border-yellow-500/30'}`}>
              <Zap className={`w-3 h-3 animate-pulse ${isCritical ? 'text-red-400' : 'text-yellow-400'}`} />
              <span className={`text-xs font-mono ${isCritical ? 'text-red-300' : 'text-yellow-300'}`}>
                {isCritical ? 'CRITICAL' : 'SMS 분석'}
              </span>
            </div>
          )}
          <div className="bg-[#0f111a] px-3 py-1.5 rounded-lg border border-white/5 flex items-center space-x-2">
            <Activity className="w-3 h-3 text-emerald-500" />
            <span className="text-xs text-slate-300 font-mono">LIVE</span>
          </div>
        </div>
      </div>

      {/* 터미널 뷰 */}
      <div className={`rounded-xl p-4 border font-mono text-sm flex items-start relative shadow-inner transition-all duration-300
        ${isAnalyzingSms && isCritical ? 'bg-[#100505] border-red-500/20 min-h-[7rem]' : isAnalyzingSms ? 'bg-[#0f0a00] border-yellow-500/20 min-h-[7rem]' : 'bg-[#0a0c10] border-white/5 h-28'}`}>
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-500/5 to-transparent h-full w-full pointer-events-none animate-scanline" />
        <div className="w-full">
          <div className="flex items-start space-x-2">
            <span className={`mt-0.5 shrink-0 ${isAnalyzingSms && isCritical ? 'text-red-500' : isAnalyzingSms ? 'text-yellow-500' : 'text-blue-500'}`}>❯</span>
            <p className={`leading-relaxed ${textColor}`}>
              {displayedText}
              <span className={`animate-blink inline-block w-2 h-4 align-middle ml-1 ${isAnalyzingSms && isCritical ? 'bg-red-500/50' : isAnalyzingSms ? 'bg-yellow-500/50' : 'bg-blue-500/50'}`}></span>
            </p>
          </div>
        </div>
      </div>

      {/* War-Room 개설 버튼 (분석 완료 + Critical 등급일 때 표시) */}
      {analysisComplete && isAnalyzingSms && (
        <div className={`mt-4 flex items-center gap-3 p-4 rounded-2xl border animate-in fade-in slide-in-from-bottom-2 duration-500
          ${isCritical ? 'bg-red-500/5 border-red-500/20' : 'bg-yellow-500/5 border-yellow-500/20'}`}>
          <div className={`flex-1 text-xs ${isCritical ? 'text-red-300' : 'text-yellow-300'}`}>
            {isCritical
              ? '⚠️ CRITICAL 장애가 감지되었습니다. 즉시 팀 전체가 참여하는 War-Room을 개설하세요.'
              : '💡 분석이 완료되었습니다. 필요 시 War-Room을 개설하여 팀과 상황을 공유하세요.'}
          </div>
          <button
            onClick={handleOpenWarRoom}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm whitespace-nowrap transition-all active:scale-95 shadow-lg
              ${isCritical
                ? 'bg-red-500 hover:bg-red-400 text-white shadow-red-500/30'
                : 'bg-yellow-500 hover:bg-yellow-400 text-black shadow-yellow-500/30'}`}
          >
            <Users className="w-4 h-4" />
            War-Room 개설
          </button>
        </div>
      )}
    </div>
  );
}
