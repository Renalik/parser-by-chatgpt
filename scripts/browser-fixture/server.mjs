import { chromium } from "../../frontend/node_modules/playwright-core/index.mjs";
import { mkdtempSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const executable =
  process.env.CHROMIUM_PATH ||
  (process.platform === "win32"
    ? [process.env["PROGRAMFILES(X86)"], process.env.PROGRAMFILES]
        .filter(Boolean)
        .map((p) => join(p, "Microsoft", "Edge", "Application", "msedge.exe"))
        .find(existsSync)
    : "/usr/bin/chromium");
const context = await chromium.launchPersistentContext(
  mkdtempSync(join(tmpdir(), "parser-cdp-")),
  {
    executablePath: executable,
    headless: true,
    args: ["--no-sandbox", "--remote-debugging-port=9334"],
  },
);
await context.route("**/*", async (route) => {
  const u = new URL(route.request().url());
  let html = "";
  if (u.pathname.includes("/search/"))
    html = `<html><body><div id="list" style="height:200px;overflow:auto;width:400px"><a style="display:block;height:180px" href="/moscow/firm/101">Первая</a><div style="height:200px"></div></div><script>let added=false;document.querySelector('#list').onscroll=()=>{if(!added){added=true;for(const id of [102,103]){let a=document.createElement('a');a.href='/moscow/firm/'+id;a.textContent='Следующая '+id;a.style='display:block;height:180px';document.querySelector('#list').append(a)}}};</script></body></html>`;
  else if (u.pathname.includes("/firm/")) {
    const id = u.pathname.split("/").pop();
    html = `<html><body><h1>Компания ${id}</h1><div><a href="/geo/1">Тестовая улица 1</a></div><a href="tel:+70000000000" id="phone">+7 000...</a><button onclick="document.querySelector('#phone').textContent='+7 000 000-00-00';this.remove()">Показать телефон</button><a href="https://example.org">example.org</a><a href="https://t.me/example">Telegram</a><a href="/moscow/firm/${id}/tab/reviews">Отзывы 12</a></body></html>`;
  } else html = "<html><body>Fixture</body></html>";
  await route.fulfill({
    status: 200,
    contentType: "text/html; charset=utf-8",
    body: html,
  });
});
console.log("CDP fixture ready");
process.stdin.resume();
await new Promise((resolve) => {
  process.on("SIGTERM", resolve);
  process.on("SIGINT", resolve);
  process.stdin.once("data", resolve);
});
await context.close();
