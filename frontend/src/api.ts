export async function api(path: string, options: RequestInit = {}) {
  const r = await fetch("/api" + path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Сервер недоступен" }));
    throw new Error(
      typeof e.detail === "string"
        ? e.detail
        : "Проверьте заполнение полей: " + JSON.stringify(e.detail),
    );
  }
  return r.json();
}
export const send = (path: string, body: unknown, method = "POST") =>
  api(path, { method, body: JSON.stringify(body) });
