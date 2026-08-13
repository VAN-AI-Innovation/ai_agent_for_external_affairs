import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { FileText, Handshake, Loader2, Mail, Search, Send, Users } from "lucide-react";
import "./styles.css";

type CapabilityKey =
  | "contract_review"
  | "meeting_prep"
  | "partner_research"
  | "lead_scoring"
  | "outreach"
  | "meeting_follow_up";

const capabilities: Array<{
  key: CapabilityKey;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}> = [
  { key: "contract_review", label: "계약 검토", icon: FileText },
  { key: "partner_research", label: "기관 리서치", icon: Search },
  { key: "meeting_prep", label: "미팅 준비", icon: Users },
  { key: "lead_scoring", label: "협력 평가", icon: Handshake },
  { key: "outreach", label: "1차 컨택", icon: Mail },
  { key: "meeting_follow_up", label: "후속 정리", icon: Send },
];

const examples: Record<CapabilityKey, string> = {
  contract_review: "NDA 계약서에서 우리 회사가 확인해야 할 핵심 조항과 위험 요소를 정리해줘.",
  partner_research: "AI 교육 플랫폼을 운영하는 대학 산학협력단과 미팅 전 사전 리서치 체크리스트를 만들어줘.",
  meeting_prep: "공동 마케팅 제휴 미팅에서 사용할 안건, 질문, 협상 포인트를 준비해줘.",
  lead_scoring: "B2B SaaS 파트너 후보 5곳을 평가하기 위한 적합도 기준을 만들어줘.",
  outreach: "처음 연락하는 기관 담당자에게 보낼 협업 제안 이메일 초안을 작성해줘.",
  meeting_follow_up: "미팅 메모를 바탕으로 회의록, 후속 업무, 담당자를 정리하는 템플릿을 만들어줘.",
};

function App() {
  const [capability, setCapability] = useState<CapabilityKey>("meeting_prep");
  const [task, setTask] = useState(examples.meeting_prep);
  const [context, setContext] = useState("");
  const [result, setResult] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState("checking");

  const selected = useMemo(
    () => capabilities.find((item) => item.key === capability)!,
    [capability],
  );

  useEffect(() => {
    fetch("http://localhost:8000/api/health")
      .then((response) => (response.ok ? setHealth("online") : setHealth("offline")))
      .catch(() => setHealth("offline"));
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError("");
    setResult("");

    try {
      const response = await fetch("http://localhost:8000/api/agent/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task, context, capability }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "요청 처리 중 오류가 발생했습니다.");
      }

      setResult(data.result);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  }

  const SelectedIcon = selected.icon;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">External Affairs AI</p>
          <h1>대외업무 통합 에이전트</h1>
        </div>
        <nav className="capability-list" aria-label="업무 유형">
          {capabilities.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={item.key === capability ? "capability active" : "capability"}
                key={item.key}
                onClick={() => {
                  setCapability(item.key);
                  setTask(examples[item.key]);
                }}
                type="button"
                title={item.label}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Day 1 Prototype</p>
            <h2>
              <SelectedIcon size={22} />
              {selected.label}
            </h2>
          </div>
          <span className={`status ${health}`}>{health}</span>
        </header>

        <form className="request-panel" onSubmit={submit}>
          <label>
            요청
            <textarea value={task} onChange={(event) => setTask(event.target.value)} rows={5} />
          </label>
          <label>
            추가 맥락
            <textarea
              value={context}
              onChange={(event) => setContext(event.target.value)}
              placeholder="상대 기관, 참석자, 계약서 일부, 미팅 목적 등"
              rows={6}
            />
          </label>
          <button className="primary" disabled={isLoading || task.trim().length === 0} type="submit">
            {isLoading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
            실행
          </button>
        </form>

        <section className="result-panel" aria-live="polite">
          {error && <div className="error">{error}</div>}
          {result ? <pre>{result}</pre> : <p className="placeholder">LLM 응답이 여기에 표시됩니다.</p>}
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
