import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Bot,
  Check,
  Clock3,
  Copy,
  FileText,
  Handshake,
  Loader2,
  Mail,
  MessageCircle,
  Search,
  Send,
  ThumbsDown,
  ThumbsUp,
  Upload,
  User,
  Users,
  X,
} from "lucide-react";
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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8002";
const CHAT_SESSION_KEY = "external-affairs-chat-session";
const CHAT_HISTORY_KEY = "external-affairs-chat-history";
const RUN_HISTORY_KEY = "external-affairs-run-history";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
};

type RunHistoryItem = {
  id: string;
  capability: CapabilityKey;
  label: string;
  task: string;
  context: string;
  result: string;
  createdAt: string;
};

const quickQuestions = [
  "매뉴얼 검색",
  "담당자 찾기",
  "미팅 준비",
  "1차 컨택 문안",
];

function renderMarkdownLike(text: string) {
  const blocks = text.split(/\n{2,}/).filter((block) => block.trim().length > 0);

  function renderInline(line: string) {
    const parts = line.split(/(\*\*.+?\*\*)/g);
    return parts.map((part, index) =>
      part.startsWith("**") && part.endsWith("**") ? (
        <strong key={index}>{part.slice(2, -2)}</strong>
      ) : (
        <React.Fragment key={index}>{part}</React.Fragment>
      ),
    );
  }

  return blocks.map((block, blockIndex) => {
    const lines = block.split("\n").filter((line) => line.trim().length > 0);
    const firstLine = lines[0]?.trim() ?? "";

    if (/^#{2,3}\s+/.test(firstLine)) {
      return (
        <section className="result-block" key={blockIndex}>
          <h3>{firstLine.replace(/^#{2,3}\s+/, "")}</h3>
          {renderMarkdownLike(lines.slice(1).join("\n"))}
        </section>
      );
    }

    if (lines.every((line) => line.trim().startsWith("|"))) {
      const rows = lines
        .map((line) => line.split("|").map((cell) => cell.trim()).filter(Boolean))
        .filter((row) => !row.every((cell) => /^:?-{3,}:?$/.test(cell)));

      return (
        <div className="table-wrap" key={blockIndex}>
          <table>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {row.map((cell, cellIndex) =>
                    rowIndex === 0 ? (
                      <th key={cellIndex}>{cell}</th>
                    ) : (
                      <td key={cellIndex}>{cell}</td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    if (lines.every((line) => /^[-*]\s+/.test(line.trim()))) {
      return (
        <ul key={blockIndex}>
          {lines.map((line, lineIndex) => (
            <li key={lineIndex}>{renderInline(line.trim().replace(/^[-*]\s+/, ""))}</li>
          ))}
        </ul>
      );
    }

    if (lines.every((line) => /^\d+\.\s+/.test(line.trim()))) {
      return (
        <ol key={blockIndex}>
          {lines.map((line, lineIndex) => (
            <li key={lineIndex}>{renderInline(line.trim().replace(/^\d+\.\s+/, ""))}</li>
          ))}
        </ol>
      );
    }

    return (
      <p key={blockIndex}>
        {lines.map((line, lineIndex) => (
          <React.Fragment key={lineIndex}>
            {renderInline(line)}
            {lineIndex < lines.length - 1 && <br />}
          </React.Fragment>
        ))}
      </p>
    );
  });
}

function FloatingChatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(CHAT_SESSION_KEY) || "");
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const saved = localStorage.getItem(CHAT_HISTORY_KEY);
    if (!saved) {
      return [
        {
          role: "assistant",
          content: "안녕하세요. 대외업무 매뉴얼 검색, 담당자 확인 질문 정리, 미팅 준비를 도와드릴게요.",
        },
      ];
    }

    try {
      return JSON.parse(saved) as ChatMessage[];
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(messages.slice(-30)));
  }, [messages]);

  useEffect(() => {
    async function syncSession() {
      try {
        if (sessionId) {
          const response = await fetch(`${API_BASE_URL}/api/chat/${sessionId}/history`);
          if (response.ok) {
            const data = await response.json();
            if (data.messages?.length) {
              setMessages(data.messages);
            }
            return;
          }
        }

        const response = await fetch(`${API_BASE_URL}/api/chat/session`, { method: "POST" });
        const data = await response.json();
        setSessionId(data.session_id);
        localStorage.setItem(CHAT_SESSION_KEY, data.session_id);
      } catch {
        // 로컬 히스토리만으로도 UI는 동작합니다.
      }
    }

    syncSession();
  }, [sessionId]);

  async function sendChatMessage(nextMessage = input) {
    const trimmed = nextMessage.trim();
    if (!trimmed || isSending) {
      return;
    }

    setInput("");
    setIsSending(true);
    setMessages((current) => [...current, { role: "user", content: trimmed }]);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId || null, message: trimmed }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "챗봇 응답을 가져오지 못했습니다.");
      }

      setSessionId(data.session_id);
      localStorage.setItem(CHAT_SESSION_KEY, data.session_id);
      setMessages((current) => [...current, data.message]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "지금은 서버 응답을 가져오지 못했습니다. 백엔드 실행 상태를 확인해 주세요.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendChatMessage();
    }
  }

  return (
    <div className="chatbot">
      {isOpen && (
        <section className="chat-window" aria-label="AI 에이전트 채팅">
          <header className="chat-header">
            <div>
              <p className="eyebrow">VAN AI Desk</p>
              <h3>
                <Bot size={18} />
                대외업무 챗봇
              </h3>
            </div>
            <button className="icon-button" onClick={() => setIsOpen(false)} type="button" title="닫기">
              <X size={18} />
            </button>
          </header>

          <div className="quick-chip-list" aria-label="빠른 질문">
            {quickQuestions.map((question) => (
              <button
                className="quick-chip"
                key={question}
                onClick={() => sendChatMessage(question)}
                type="button"
              >
                {question}
              </button>
            ))}
          </div>

          <div className="chat-messages">
            {messages.map((message, index) => (
              <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
                <span className="avatar">{message.role === "assistant" ? <Bot size={15} /> : <User size={15} />}</span>
                <div className="bubble">{renderMarkdownLike(message.content)}</div>
              </article>
            ))}
            {isSending && (
              <article className="chat-message assistant">
                <span className="avatar">
                  <Bot size={15} />
                </span>
                <div className="typing" aria-label="답변 생성 중">
                  <span />
                  <span />
                  <span />
                </div>
              </article>
            )}
          </div>

          <form
            className="chat-form"
            onSubmit={(event) => {
              event.preventDefault();
              sendChatMessage();
            }}
          >
            <textarea
              aria-label="챗봇 메시지"
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="대외업무 질문을 입력하세요"
              rows={2}
              value={input}
            />
            <button className="icon-button send-button" disabled={!input.trim() || isSending} type="submit" title="전송">
              <Send size={18} />
            </button>
          </form>
        </section>
      )}

      <button className="chat-toggle" onClick={() => setIsOpen((value) => !value)} type="button" title="챗봇 열기">
        <MessageCircle size={24} />
      </button>
    </div>
  );
}

function App() {
  const [capability, setCapability] = useState<CapabilityKey>("meeting_prep");
  const [task, setTask] = useState(examples.meeting_prep);
  const [context, setContext] = useState("");
  const [contractFile, setContractFile] = useState<File | null>(null);
  const [result, setResult] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState("checking");
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"like" | "dislike" | "">("");
  const [runHistory, setRunHistory] = useState<RunHistoryItem[]>(() => {
    const saved = localStorage.getItem(RUN_HISTORY_KEY);
    if (!saved) {
      return [];
    }

    try {
      return JSON.parse(saved) as RunHistoryItem[];
    } catch {
      return [];
    }
  });

  const selected = useMemo(
    () => capabilities.find((item) => item.key === capability)!,
    [capability],
  );

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/health`)
      .then((response) => (response.ok ? setHealth("online") : setHealth("offline")))
      .catch(() => setHealth("offline"));
  }, []);

  useEffect(() => {
    localStorage.setItem(RUN_HISTORY_KEY, JSON.stringify(runHistory.slice(0, 8)));
  }, [runHistory]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError("");
    setResult("");

    try {
      const response =
        capability === "contract_review" && contractFile
          ? await analyzeContractDocument(contractFile, context)
          : await fetch(`${API_BASE_URL}/api/agent/run`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ task, context, capability }),
            });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "요청 처리 중 오류가 발생했습니다.");
      }

      setResult(data.result);
      setFeedback("");
      addRunHistory(data.result);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  }

  async function analyzeContractDocument(file: File, reviewFocus: string) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("review_focus", reviewFocus);

    return fetch(`${API_BASE_URL}/api/contracts/analyze`, {
      method: "POST",
      body: formData,
    });
  }

  function addRunHistory(nextResult: string) {
    const title =
      capability === "contract_review"
        ? contractFile?.name || "계약서 분석"
        : task.trim().slice(0, 80);
    const item: RunHistoryItem = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      capability,
      label: selected.label,
      task: title,
      context,
      result: nextResult,
      createdAt: new Date().toLocaleString("ko-KR", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }),
    };
    setRunHistory((current) => [item, ...current.filter((history) => history.result !== nextResult)].slice(0, 8));
  }

  async function copyResult() {
    if (!result) {
      return;
    }

    await navigator.clipboard.writeText(result);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  async function sendFeedback(nextFeedback: "like" | "dislike") {
    if (!result) {
      return;
    }

    setFeedback(nextFeedback);
    try {
      await fetch(`${API_BASE_URL}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: "main_result",
          rating: nextFeedback,
          capability,
          prompt: capability === "contract_review" ? contractFile?.name || "contract file" : task,
          result_preview: result.slice(0, 240),
        }),
      });
    } catch {
      // 피드백은 보조 기능이라 API 실패 시에도 선택 상태는 유지합니다.
    }
  }

  function restoreHistory(item: RunHistoryItem) {
    setCapability(item.capability);
    setTask(item.task || examples[item.capability]);
    setContext(item.context);
    setResult(item.result);
    setFeedback("");
    setContractFile(null);
  }

  const SelectedIcon = selected.icon;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <span className="brand-mark">V</span>
          <div>
            <p className="eyebrow">VAN Operations</p>
            <h1>External Affairs AI</h1>
          </div>
        </div>
        <div className="sidebar-brief">
          <span>VAN CONFERENCE 2026</span>
          <strong>Partnership Desk</strong>
          <small>Contract · Research · Meeting · Outreach</small>
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
                  setContractFile(null);
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
            <p className="eyebrow">Official Operations Console</p>
            <h2>
              <SelectedIcon size={22} />
              {selected.label}
            </h2>
          </div>
          <div className="topbar-meta">
            <span>PARTNERSHIP / CONTRACT / MEETING</span>
            <span className={`status ${health}`}>{health}</span>
          </div>
        </header>

        <form className="request-panel" onSubmit={submit}>
          {capability === "contract_review" ? (
            <label className="file-field">
              계약서 파일
              <span className="file-drop">
                <Upload size={20} />
                <span>{contractFile ? contractFile.name : "PDF, TXT, DOCX, PNG, JPG 파일을 선택하세요"}</span>
                <input
                  accept=".pdf,.txt,.md,.docx,.png,.jpg,.jpeg,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg"
                  onChange={(event) => setContractFile(event.target.files?.[0] ?? null)}
                  type="file"
                />
              </span>
            </label>
          ) : (
            <label>
              요청
              <textarea value={task} onChange={(event) => setTask(event.target.value)} rows={5} />
            </label>
          )}
          <label>
            {capability === "contract_review" ? "분석 기준" : "추가 맥락"}
            <textarea
              value={context}
              onChange={(event) => setContext(event.target.value)}
              placeholder={
                capability === "contract_review"
                  ? "특히 확인할 조항, 우리 회사 입장, 거래 배경 등"
                  : "상대 기관, 참석자, 계약서 일부, 미팅 목적 등"
              }
              rows={6}
            />
          </label>
          <button
            className="primary"
            disabled={
              isLoading ||
              (capability === "contract_review" ? !contractFile : task.trim().length === 0)
            }
            type="submit"
          >
            {isLoading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
            {capability === "contract_review" ? "분석" : "실행"}
          </button>
        </form>

        <section className="result-panel" aria-live="polite">
          <div className="result-toolbar">
            <span>{result ? "결과" : "대기 중"}</span>
            <div className="result-actions">
              <button className="tool-button" disabled={!result} onClick={copyResult} type="button" title="결과 복사">
                {copied ? <Check size={16} /> : <Copy size={16} />}
              </button>
              <button
                className={feedback === "like" ? "tool-button active" : "tool-button"}
                disabled={!result}
                onClick={() => sendFeedback("like")}
                type="button"
                title="좋아요"
              >
                <ThumbsUp size={16} />
              </button>
              <button
                className={feedback === "dislike" ? "tool-button active" : "tool-button"}
                disabled={!result}
                onClick={() => sendFeedback("dislike")}
                type="button"
                title="싫어요"
              >
                <ThumbsDown size={16} />
              </button>
            </div>
          </div>
          {error && <div className="error">{error}</div>}
          {result ? (
            <div className="rendered-result">{renderMarkdownLike(result)}</div>
          ) : (
            <p className="placeholder">분석 결과가 여기에 표시됩니다.</p>
          )}
        </section>

        <section className="history-panel" aria-label="최근 실행 기록">
          <div className="history-header">
            <h3>
              <Clock3 size={18} />
              최근 실행 기록
            </h3>
            {runHistory.length > 0 && (
              <button className="text-button" onClick={() => setRunHistory([])} type="button">
                비우기
              </button>
            )}
          </div>
          {runHistory.length > 0 ? (
            <div className="history-list">
              {runHistory.map((item) => (
                <button className="history-item" key={item.id} onClick={() => restoreHistory(item)} type="button">
                  <span>{item.label}</span>
                  <strong>{item.task}</strong>
                  <small>{item.createdAt}</small>
                </button>
              ))}
            </div>
          ) : (
            <p className="placeholder">실행한 결과가 최근 기록으로 저장됩니다.</p>
          )}
        </section>
      </section>
      <FloatingChatbot />
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
