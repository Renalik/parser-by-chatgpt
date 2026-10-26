import { useState } from "react";

import {
  Check,
  Play,
  ExternalLink,
  Save,
  KeyRound,
  Info,
  RefreshCw,
} from "lucide-react";

import { send } from "../api";

import { Button } from "./ui";
export default function SettingsPage({ meta, run, busy }: any) {
  const [key, setKey] = useState(""),
    [license, setLicense] = useState(meta.license);
  return (
    <>
      <div className="page-heading">
        <div className="eyebrow">ВАША РАБОЧАЯ СРЕДА</div>
        <h1>Настройки</h1>
        <p>Подключение источника и управление доступом к данным.</p>
      </div>
      <div className="settings-layout">
        <div>
          <div className="panel">
            <div className="section-heading">
              <div>
                <h2>
                  <KeyRound size={19} />
                  Подключение 2ГИС
                </h2>
                <p>Ключ передаётся только серверу приложения и API 2ГИС.</p>
              </div>
              <span className="tag">
                {meta.has_key ? "Ключ задан" : "Не подключено"}
              </span>
            </div>
            <label>
              API-ключ
              <input
                type="password"
                autoComplete="off"
                value={key}
                placeholder={
                  meta.has_key
                    ? "Оставьте пустым, чтобы использовать текущий"
                    : "Введите ваш ключ 2ГИС"
                }
                onChange={(e) => setKey(e.target.value)}
              />
            </label>
            <p className="muted">
              Ключ из формы хранится в памяти до перезапуска. Для постоянного
              подключения задайте DGIS_API_KEY в .env на сервере.
            </p>
            <div className="inline">
              <Button
                primary
                disabled={busy || (!key && !meta.has_key)}
                onClick={() =>
                  run(async () => {
                    await send("/connection", {
                      mode: "live",
                      ...(key ? { api_key: key } : {}),
                    });
                    setKey("");
                  })
                }
              >
                <RefreshCw size={15} />
                Проверить подключение
              </Button>
              <Button
                disabled={busy}
                onClick={() => run(() => send("/connection", { mode: "demo" }))}
              >
                <Play size={15} />
                Открыть деморежим
              </Button>
            </div>
            {busy && <p role="status">Проверка доступа к полям API…</p>}
            {meta.capabilities.messages?.map((m: string) => (
              <p className="diagnostic" key={m}>
                <Info size={14} />
                {m}
              </p>
            ))}
          </div>
          <div className="panel mt">
            <h2>Хранение и экспорт</h2>
            <p>
              Отметьте только права, предусмотренные вашим договором с
              поставщиком. Эта настройка не выдаёт лицензию.
            </p>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={license.storage_allowed}
                onChange={(e) =>
                  setLicense({ ...license, storage_allowed: e.target.checked })
                }
              />
              Лицензия разрешает сохранять результаты поиска
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={license.export_allowed}
                onChange={(e) =>
                  setLicense({ ...license, export_allowed: e.target.checked })
                }
              />
              Лицензия разрешает выгружать данные
            </label>
            <label>
              Примечание о разрешении
              <input
                value={license.license_note}
                onChange={(e) =>
                  setLicense({ ...license, license_note: e.target.value })
                }
                placeholder="Например, номер договора"
              />
            </label>
            <Button onClick={() => run(() => send("/license", license, "PUT"))}>
              <Save size={15} />
              Сохранить разрешения
            </Button>
            <p className="muted">
              Результаты реальных поисков удаляются при запуске сервера по сроку
              RETENTION_DAYS (по умолчанию 7 дней). Выгрузки скачиваются в
              папку, выбранную браузером.
            </p>
          </div>
          <div className="panel mt">
            <h2>Возможности и ограничения</h2>
            {meta.limitations.map((x: string) => (
              <p className="diagnostic" key={x}>
                <Info size={15} />
                {x}
              </p>
            ))}
            <p>
              <a
                href="https://docs.2gis.com/ru/api/search/places/overview"
                target="_blank"
                rel="noreferrer"
              >
                Документация 2ГИС <ExternalLink size={13} />
              </a>{" "}
              ·{" "}
              <a href="https://dev.2gis.com/" target="_blank" rel="noreferrer">
                Кабинет разработчика
              </a>
            </p>
          </div>
        </div>
        <div className="panel capabilities">
          <h3>Доступность полей</h3>
          <p className="muted">По последней диагностике источника</p>
          {Object.entries(meta.fields).map(([k, v]: any) => (
            <div key={k}>
              <span>{v}</span>
              {meta.capabilities.fields?.[k] ? (
                <Check size={15} />
              ) : (
                <span className="muted" title="Доступ не подтверждён">
                  —
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
