import { Database } from "lucide-react";

export const status: Record<string, string> = {
  queued: "В очереди",
  running: "Выполняется",
  paused: "На паузе",
  stopped: "Остановлен",
  completed: "Завершён",
  failed: "Ошибка",
};
export const date = (s: string) =>
  new Date(s).toLocaleString("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
export function Button({
  children,
  onClick,
  primary = false,
  disabled = false,
  ...rest
}: any) {
  return (
    <button
      className={primary ? "button primary" : "button"}
      onClick={onClick}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  );
}
export function Empty({ title, text, children }: any) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Database size={27} />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
      {children}
    </div>
  );
}
