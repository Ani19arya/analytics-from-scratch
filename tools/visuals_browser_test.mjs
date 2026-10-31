// Browser tests for the offline pages in visuals/, run in headless Chromium with Playwright.
//
//     node tools/visuals_browser_test.mjs [visuals_dir]
//
// For every page (opened from a file:// URL) it checks: no console errors, no page errors,
// zero requests that are not file://, the page's own "Self check: N of N" footer, the main
// interactions against the values in the page's fixtures block, at least one control driven
// by the keyboard, no horizontal scroll at 375x740, a different body background in dark
// mode, accessible names on every control and meaningful image, and exactly one h1.
// Prints one line per failure and exits 1 if there is any. Needs only the playwright module
// (from ./node_modules, NODE_PATH or the global npm root) and a Chromium it can launch.

import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const VIS = path.resolve(process.argv[2] || path.join(ROOT, "visuals"));

function loadPlaywright() {
  const bases = [path.join(HERE, "x.js"), path.join(process.cwd(), "x.js")];
  for (const p of (process.env.NODE_PATH || "").split(path.delimiter)) if (p) bases.push(path.join(p, "x.js"));
  try { bases.push(path.join(execSync("npm root -g", { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim(), "x.js")); } catch (e) { /* no npm */ }
  for (const b of bases) {
    try { return createRequire(b)("playwright"); } catch (e) { /* try the next place */ }
  }
  console.error("FAIL [setup] cannot find the playwright module (npm install --no-save playwright)");
  process.exit(1);
}

const { chromium } = loadPlaywright();
const failures = [];
let checks = 0;

function check(page, ok, msg) {
  checks++;
  if (!ok) failures.push("[" + page + "] " + msg);
}

function fixturesOf(name) {
  const html = fs.readFileSync(path.join(VIS, name + ".html"), "utf8");
  const m = html.match(/<script type="application\/json" id="fixtures">([\s\S]*?)<\/script>/);
  if (!m) throw new Error("no fixtures block");
  return JSON.parse(m[1]);
}

const text = async (page, sel) => ((await page.locator(sel).first().textContent()) || "").trim();

// Press Tab until the focused element matches sel, so the control is reachable by keyboard.
async function tabTo(page, sel, max = 120) {
  for (let i = 0; i < max; i++) {
    await page.keyboard.press("Tab");
    if (await page.evaluate((s) => !!document.activeElement && document.activeElement.matches(s), sel)) return true;
  }
  return false;
}

// Checks shared by every page: self check, h1, accessible names, layout, dark mode.
async function commonChecks(page, name) {
  const sc = await page.evaluate(() => {
    const el = document.getElementById("selfcheck");
    return el ? { text: el.textContent, ok: el.dataset.ok } : null;
  });
  if (name !== "index") {
    if (!sc) check(name, false, "no #selfcheck footer");
    else {
      const m = sc.text.match(/Self check: (\d+) of (\d+)/);
      check(name, !!m && +m[1] === +m[2] && +m[2] > 0 && sc.ok === "true", "self check does not pass: " + sc.text.slice(0, 160));
    }
  }
  const a11y = await page.evaluate(() => {
    const txt = (el) => (el ? el.textContent.replace(/\s+/g, " ").trim() : "");
    function nameOf(el) {
      const by = el.getAttribute("aria-labelledby");
      if (by) { const t = by.split(/\s+/).map((id) => txt(document.getElementById(id))).join(" ").trim(); if (t) return t; }
      const al = (el.getAttribute("aria-label") || "").trim();
      if (al) return al;
      if (el.labels && el.labels.length) { const t = Array.from(el.labels).map(txt).join(" ").trim(); if (t) return t; }
      if (el.tagName === "BUTTON" && txt(el)) return txt(el);
      if (el.tagName === "INPUT" && /^(button|submit|reset)$/.test(el.type) && el.value) return el.value;
      if (el.tagName === "svg") { const t = el.querySelector(":scope > title"); if (t && txt(t)) return txt(t); }
      if (el.tagName === "IMG" && el.hasAttribute("alt")) return el.getAttribute("alt") || "(decorative)";
      return (el.getAttribute("title") || "").trim();
    }
    const bad = [];
    const desc = (el) => el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + (el.className && typeof el.className === "string" ? "." + el.className.split(" ")[0] : "");
    document.querySelectorAll("input, select, button, textarea").forEach((el) => { if (el.type !== "hidden" && !nameOf(el)) bad.push(desc(el)); });
    document.querySelectorAll("img, svg, [role=img]").forEach((el) => {
      if (el.tagName === "svg" && el.parentElement && el.parentElement.closest("svg")) return;
      if (el.getAttribute("aria-hidden") === "true") return;
      if (!nameOf(el)) bad.push(desc(el));
    });
    return { bad, h1: document.querySelectorAll("h1").length };
  });
  check(name, a11y.h1 === 1, "expected exactly one h1, found " + a11y.h1);
  check(name, a11y.bad.length === 0, "no accessible name: " + a11y.bad.join(", "));
  await layoutCheck(page, name, "light");
  const light = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  await page.emulateMedia({ colorScheme: "dark" });
  const dark = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  check(name, light !== dark, "body background is the same in light and dark mode (" + light + ")");
  await layoutCheck(page, name, "dark");
  await page.emulateMedia({ colorScheme: "light" });
}

async function layoutCheck(page, name, when) {
  const w = await page.evaluate(() => ({ s: document.documentElement.scrollWidth, c: document.documentElement.clientWidth }));
  check(name, w.s <= w.c, "horizontal scroll at 375px (" + when + "): scrollWidth " + w.s + " > clientWidth " + w.c);
}

/* ---------- page tests ---------- */

async function testJoin(page, P) {
  const FX = fixturesOf(P);
  const caseOf = (mode, second) => FX.cases.find((c) => c.mode === mode && c.second.slice().sort().join() === second.slice().sort().join());
  const expectJoin = async (mode, second, why) => {
    const c = caseOf(mode, second);
    const rows = await text(page, "#jRows"), sum = await text(page, "#jSum");
    check(P, rows === String(c.rows) && sum === c.sum.toFixed(2), why + ": expected " + c.rows + " rows and SUM " + c.sum.toFixed(2) + ", got " + rows + " and " + sum);
  };
  const both = FX.explorer.second_addresses;
  await expectJoin("all", both, "on load (both second addresses, no fix)");
  await page.locator("#keep_" + both[1]).click();
  await expectJoin("all", [both[0]], "after unticking " + both[1]);
  await page.locator("#keep_" + both[0]).click();
  await expectJoin("all", [], "after unticking both");
  check(P, (await page.locator("#jGap").textContent()).trim() === "0.00", "gap should be 0.00 with no second addresses");
  await page.locator("#keep_" + both[0]).click();
  await page.locator("#keep_" + both[1]).click();
  await expectJoin("all", both, "after ticking both again");
  for (const m of ["primary", "preagg", "distinct", "all"]) {
    await page.locator('#modes button[data-mode="' + m + '"]').click();
    await expectJoin(m, both, "mode " + m);
    check(P, (await page.locator('#modes button[data-mode="' + m + '"]').getAttribute("aria-checked")) === "true", "mode " + m + " button not aria-checked after click");
  }
  // all 360 orders
  for (const f of FX.full) {
    await page.locator('#modes button[data-mode="' + f.mode + '"]').click();
    await page.locator("#runFull").click();
    const out = await text(page, "#fullOut");
    check(P, out.includes(f.rows + " joined rows, SUM(amount) " + f.sum.toFixed(2)), "full data, mode " + f.mode + ": expected " + f.rows + " rows and " + f.sum.toFixed(2) + ", got: " + out.slice(0, 120));
  }
  // spot the mistake
  const wrongPick = FX.spot.customers.find((c) => c !== FX.spot.answer);
  await page.locator('#spotTable button[data-c="' + wrongPick + '"]').click();
  check(P, (await page.locator("#spotFeedback").getAttribute("class")) === "badbox", "picking " + wrongPick + " should be rejected");
  await page.locator('#spotTable button[data-c="' + FX.spot.answer + '"]').click();
  check(P, (await page.locator("#spotFeedback").getAttribute("class")) === "okbox", "picking " + FX.spot.answer + " should be accepted");
  for (const [c, v] of FX.spot.result) {
    const shown = await text(page, "#spot_" + c + " td.num");
    check(P, shown === v.toFixed(2), "spot table " + c + ": expected " + v.toFixed(2) + ", got " + shown);
  }
  // keyboard: arrow keys move the radio group, Space toggles a checkbox
  await page.locator('#modes button[data-mode="all"]').click();
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  check(P, await tabTo(page, '#modes button[aria-checked="true"]'), "cannot Tab to the join mode radio group");
  await page.keyboard.press("ArrowRight");
  check(P, await page.evaluate(() => document.activeElement.dataset.mode === "primary" && document.activeElement.getAttribute("aria-checked") === "true"), "ArrowRight in the radio group did not select and focus the next mode");
  await expectJoin("primary", both, "after ArrowRight to primary");
  await page.keyboard.press("ArrowLeft");
  await expectJoin("all", both, "after ArrowLeft back to no fix");
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  check(P, await tabTo(page, "#keep_" + both[0]), "cannot Tab to the " + both[0] + " checkbox");
  await page.keyboard.press("Space");
  await expectJoin("all", [both[1]], "after Space on the " + both[0] + " checkbox");
}

async function readWindow(page) {
  return page.evaluate(() => {
    const out = {};
    document.querySelectorAll("#out tr[data-i]").forEach((tr) => {
      const td = tr.querySelectorAll("td");
      const v = td[3].textContent.trim();
      out[td[0].textContent.trim() + "|" + td[1].textContent.trim()] = v === "NULL" ? null : Number(v);
    });
    return out;
  });
}

async function testWindow(page, P) {
  const FX = fixturesOf(P);
  const caseOf = (s) => FX.cases.find((c) => c.dataset === s.dataset && c.partition === s.partition && c.order === s.order && c.frame === s.frame && c.fn === s.fn);
  const expectWindow = async (spec, why) => {
    const want = caseOf(spec).values, got = await readWindow(page);
    const diff = Object.keys(want).filter((k) => got[k] !== want[k]);
    check(P, Object.keys(got).length === Object.keys(want).length && diff.length === 0,
      why + ": " + (diff.length ? diff.slice(0, 3).map((k) => k + " expected " + want[k] + " got " + got[k]).join("; ") : "row count " + Object.keys(got).length));
  };
  await expectWindow({ dataset: "monthly", partition: "region", order: "month", frame: "rows", fn: "sum" }, "on load (fiscal year to date)");
  await page.getByRole("button", { name: "RANK with ties" }).click();
  const tie = { dataset: "reps", partition: "region", order: "sales_desc", frame: "rows", fn: "rank" };
  await expectWindow(tie, "RANK with ties preset");
  let got = await readWindow(page);
  check(P, got["North|R04"] === 1 && got["North|R05"] === 1, "RANK: R04 and R05 should both be 1, got " + got["North|R04"] + " and " + got["North|R05"]);
  await page.locator("#fn").selectOption("row_number");
  await expectWindow({ ...tie, fn: "row_number" }, "ROW_NUMBER on the tie preset");
  got = await readWindow(page);
  check(P, got["North|R04"] === 1 && got["North|R05"] === 2, "ROW_NUMBER: R04 and R05 should be 1 and 2, got " + got["North|R04"] + " and " + got["North|R05"]);
  await page.locator("#fn").selectOption("lag");
  await expectWindow({ ...tie, fn: "lag" }, "LAG on the tie preset");
  await page.getByRole("button", { name: "Tie trap: default frame" }).click();
  await expectWindow({ ...tie, fn: "sum", frame: "range" }, "Tie trap preset (RANGE)");
  got = await readWindow(page);
  check(P, got["North|R02"] === 230000 && got["North|R03"] === 230000, "RANGE frame should give both North peers 230000");
  await page.locator("#frame").selectOption("rows");
  await expectWindow({ ...tie, fn: "sum", frame: "rows" }, "same order with a ROWS frame");
  await page.locator("#partition").selectOption("none");
  await expectWindow({ ...tie, fn: "sum", frame: "rows", partition: "none" }, "no partition");
  // the tie table in section 3
  const ties = await page.evaluate(() => Array.from(document.querySelectorAll("#ties tr")).slice(1).map((tr) => Array.from(tr.cells).map((c) => c.textContent.trim())));
  const r04 = ties.find((r) => r[0] === "R04"), r05 = ties.find((r) => r[0] === "R05");
  check(P, !!r04 && !!r05 && r04[2] === "1" && r05[2] === "1" && r04[3] === "1" && r05[3] === "2", "tie table: expected RANK 1,1 and ROW_NUMBER 1,2 for R04,R05, got " + JSON.stringify([r04, r05]));
  const note = await text(page, "#tieNote");
  check(P, note.includes("RANK() = 1: R04, R05") && note.includes("ROW_NUMBER() = 1: R04") && note.includes("R05 is left off") && note.includes("120000"), "tie note text is wrong: " + note.slice(0, 160));
  // keyboard: Tab to the result table, ArrowDown moves the current row
  await page.getByRole("button", { name: "Fiscal year to date" }).click();
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  const before = await page.evaluate(() => Array.from(document.querySelectorAll("#out tr[data-i]")).findIndex((tr) => tr.classList.contains("cur")));
  check(P, await tabTo(page, "#out"), "cannot Tab to the result table");
  await page.keyboard.press("ArrowDown");
  const after = await page.evaluate(() => Array.from(document.querySelectorAll("#out tr[data-i]")).findIndex((tr) => tr.classList.contains("cur")));
  check(P, after === before + 1, "ArrowDown on the table should move the current row from " + before + " to " + (before + 1) + ", got " + after);
  const explain = await text(page, "#explain");
  check(P, explain.startsWith("North 2025-12: SUM over 3 rows = 36518 + 34453 + 40584 = 111555"), "explanation after ArrowDown is wrong: " + explain);
  // keyboard on a select: ArrowDown changes the function
  check(P, await tabTo(page, "#fn"), "cannot Tab to the Function select");
  await page.keyboard.press("ArrowDown");
  check(P, (await page.locator("#fn").inputValue()) === "rank", "ArrowDown on the Function select did not change it to RANK");
  await expectWindow({ dataset: "monthly", partition: "region", order: "month", frame: "rows", fn: "rank" }, "after keyboard change to RANK");
}

async function readTriangle(page) {
  return page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("#tri tr")).slice(1);
    const tri = {}, avg = [];
    const val = (td) => { const t = td.textContent.trim(); return t === "" || t === "not observed" ? null : Number(t); };
    rows.forEach((tr) => {
      const td = Array.from(tr.cells);
      if (tr.classList.contains("avg")) td.slice(1).forEach((c) => avg.push(val(c)));
      else tri[td[0].textContent.trim()] = td.slice(2).map(val);
    });
    return { tri, avg };
  });
}

async function testCohort(page, P) {
  const FX = fixturesOf(P);
  const expectTri = async (count, denom, unobs, why) => {
    const c = FX.cases.find((k) => k.count === count && k.denom === denom && k.unobserved === unobs);
    const got = await readTriangle(page);
    check(P, JSON.stringify(got.avg) === JSON.stringify(c.averages), why + ": averages expected " + JSON.stringify(c.averages) + ", got " + JSON.stringify(got.avg));
    check(P, JSON.stringify(got.tri) === JSON.stringify(c.triangle), why + ": triangle cells differ from the fixtures");
  };
  await expectTri("users", "size", "blank", "on load");
  const blank = FX.cases.find((k) => k.count === "users" && k.denom === "size" && k.unobserved === "blank").averages;
  const zero = FX.cases.find((k) => k.count === "users" && k.denom === "size" && k.unobserved === "zero").averages;
  check(P, (await text(page, "#avgNote")).includes(blank[3].toFixed(1) + "%") && (await text(page, "#avgNote")).includes(zero[3].toFixed(1) + "%"), "average note should quote month 3 " + blank[3] + " and " + zero[3]);
  await page.locator("#unobs").selectOption("zero");
  await expectTri("users", "size", "zero", "unobserved months as 0");
  check(P, (await page.locator("#tri td.fake").count()) > 0, "0 for unobserved months should mark cells as fake");
  check(P, (await page.locator("#avgNote").getAttribute("class")) === "badbox", "the 0 option should show a warning");
  for (const count of ["users", "events"]) for (const denom of ["size", "prev"]) for (const unobs of ["blank", "zero"]) {
    await page.locator("#count").selectOption(count);
    await page.locator("#denom").selectOption(denom);
    await page.locator("#unobs").selectOption(unobs);
    await expectTri(count, denom, unobs, count + "/" + denom + "/" + unobs);
  }
  await page.locator("#count").selectOption("users");
  await page.locator("#denom").selectOption("size");
  await page.locator("#unobs").selectOption("blank");
  // cohort grid: one cohort's month 1 count
  await page.locator("#cohortPick").selectOption("2026-01");
  check(P, (await text(page, "#gridSum")).includes("has " + FX.sizes["2026-01"] + " users"), "grid summary should give the January cohort size " + FX.sizes["2026-01"]);
  // spot the mistake
  const [ac, am] = FX.spot.answer;
  await page.locator('#spot button[data-c="2026-01"][data-m="1"]').click();
  check(P, (await page.locator("#spotFeedback").getAttribute("class")) === "badbox", "a correct cell should be rejected");
  await page.locator('#spot button[data-c="' + ac + '"][data-m="' + am + '"]').click();
  check(P, (await page.locator("#spotFeedback").getAttribute("class")) === "okbox", "the planted cell should be accepted");
  // keyboard: Tab to the "Months not observed yet" select, ArrowDown switches to 0
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  check(P, await tabTo(page, "#unobs"), "cannot Tab to the unobserved months select");
  await page.keyboard.press("ArrowDown");
  check(P, (await page.locator("#unobs").inputValue()) === "zero", "ArrowDown on the select did not switch to 0");
  await expectTri("users", "size", "zero", "after keyboard switch to 0");
  // keyboard on the planted cell: Enter
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  await page.locator("#spotFeedback").evaluate((el) => { el.textContent = ""; el.className = ""; });
  check(P, await tabTo(page, '#spot button[data-c="' + ac + '"][data-m="' + am + '"]'), "cannot Tab to the planted cell");
  await page.keyboard.press("Enter");
  check(P, (await page.locator("#spotFeedback").getAttribute("class")) === "okbox", "Enter on the planted cell should accept it");
}

async function testAb(page, P) {
  const FX = fixturesOf(P);
  const pts = (x) => (Math.round(x * 1e4) / 100).toFixed(2);
  const expectCase = async (c, why) => {
    const got = {
      z: await text(page, "#o_z"), p: await text(page, "#o_p"), ci: await text(page, "#o_ci"), se: await text(page, "#o_se"),
      chi: await text(page, "#o_chi"), srm: await text(page, "#o_srm"), dec: await text(page, "#decision")
    };
    const want = { z: c.z.toFixed(4), p: c.p_value.toFixed(4), ci: pts(c.ci_low) + " to " + pts(c.ci_high) + " pts", se: c.se.toFixed(4), chi: c.srm_chi2.toFixed(4), srm: c.srm_p.toFixed(4) };
    for (const k of Object.keys(want)) check(P, got[k] === want[k], why + ": " + k + " expected " + want[k] + ", got " + got[k]);
    check(P, c.decision === "ship" ? got.dec.startsWith("Ship B") : got.dec.startsWith("Do not ship"), why + ": decision should be " + c.decision + ", got: " + got.dec.slice(0, 60));
  };
  await expectCase(FX.cases[0], "on load (lesson data)");
  const setN = async (id, v) => { await page.locator("#" + id).fill(String(v)); await page.locator("#" + id).press("Tab"); };
  for (const c of FX.cases) {
    await setN("na", c.n_a); await setN("nb", c.n_b); await setN("ca", c.conv_a); await setN("cb", c.conv_b);
    await expectCase(c, "typed " + c.conv_a + "/" + c.n_a + " vs " + c.conv_b + "/" + c.n_b);
  }
  // an impossible input shows the error and keeps the old numbers
  await setN("ca", 99999);
  check(P, !(await page.locator("#inputErr").isHidden()), "conversions above visitors should show the input error");
  await page.getByRole("button", { name: "Logging bug (SRM)" }).click();
  check(P, !(await page.locator("#inputErr").isVisible()), "a preset should clear the input error");
  check(P, (await text(page, "#decision")).startsWith("Stop: the sample ratio check fails"), "the SRM preset should stop the test");
  check(P, (await page.locator("#o_srm").getAttribute("class")) === "bad", "the SRM p should be marked bad");
  await page.getByRole("button", { name: "Lesson data" }).click();
  await expectCase(FX.cases[0], "Lesson data preset");
  // peeking simulation
  const sims = [FX.lesson_peeking, ...FX.peeking];
  for (const s of sims) {
    await page.locator("#sims").fill(String(s.sims));
    await page.locator("#seed").fill(String(s.seed));
    await page.locator("#runSim").click();
    const any = await text(page, "#s_any"), last = await text(page, "#s_last");
    check(P, any === s.any_day.toFixed(4) && last === s.last_day.toFixed(4), "peeking seed " + s.seed + " x " + s.sims + ": expected any " + s.any_day.toFixed(4) + " last " + s.last_day.toFixed(4) + ", got " + any + " and " + last);
  }
  check(P, (await page.locator("#paths polyline").count()) === 20, "the peeking chart should draw 20 paths");
  // keyboard: Tab to the A visitors slider, ArrowRight adds a visitor
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  const na0 = +(await page.locator("#na").inputValue());
  const pa0 = await text(page, "#o_pa");
  check(P, await tabTo(page, "#naR"), "cannot Tab to the A visitors slider");
  await page.keyboard.press("ArrowRight");
  const na1 = +(await page.locator("#na").inputValue());
  check(P, na1 === na0 + 1, "ArrowRight on the slider should make A visitors " + (na0 + 1) + ", got " + na1);
  check(P, (await text(page, "#o_pa")) === (100 * 107 / (na0 + 1)).toFixed(2) + "%" && (await text(page, "#o_pa")) !== pa0, "rate A did not update after the keyboard change");
  // keyboard: Enter on the simulate button
  await page.locator("#sims").fill("200");
  await page.locator("#seed").fill("0");
  await page.locator("#s_any").evaluate((el) => { el.textContent = "-"; });
  check(P, await tabTo(page, "#runSim"), "cannot Tab to the simulation button");
  await page.keyboard.press("Enter");
  const p200 = FX.peeking.find((s) => s.sims === 200 && s.seed === 0);
  check(P, (await text(page, "#s_any")) === p200.any_day.toFixed(4), "Enter on the simulation button should give " + p200.any_day.toFixed(4));
}

async function testAgent(page, P) {
  const FX = fixturesOf(P);
  for (let i = 0; i < FX.runs.length; i++) {
    const run = FX.runs[i];
    await page.locator("#runPick").selectOption(String(i));
    const total = run.cost.calls + 1;
    check(P, (await text(page, "#progress")).endsWith("Showing step 1 of " + total + "."), run.id + ": should start at step 1 of " + total);
    check(P, (await text(page, "#c_calls")) === "0", run.id + ": no model calls before the first step");
    let clicks = 0;
    while (await page.locator("#next").isEnabled() && clicks < 20) { await page.locator("#next").click(); clicks++; }
    check(P, clicks === run.cost.calls, run.id + ": expected " + run.cost.calls + " Next presses to reach the end, took " + clicks);
    const got = [await text(page, "#c_calls"), await text(page, "#c_in"), await text(page, "#c_out"), await text(page, "#c_cr")];
    const want = [String(run.cost.calls), String(run.cost.input_tokens), String(run.cost.output_tokens), run.cost.credits.toFixed(2)];
    check(P, JSON.stringify(got) === JSON.stringify(want), run.id + ": cost at the end expected " + want.join("/") + ", got " + got.join("/"));
    const status = await page.locator("#steps .step").last().locator("p", { hasText: "Status:" }).textContent().catch(() => "");
    check(P, status.includes("Status: " + run.status), run.id + ": last step should say Status: " + run.status + ", got: " + status);
    const flagged = await page.evaluate(() => Array.from(document.querySelectorAll("#steps tr.dup td:first-child")).map((td) => td.textContent.trim()));
    check(P, JSON.stringify(flagged) === JSON.stringify(run.ungrounded), run.id + ": grounding table flags " + JSON.stringify(flagged) + ", expected " + JSON.stringify(run.ungrounded));
    const kinds = await page.evaluate(() => Array.from(document.querySelectorAll("#steps .step")).slice(1).map((s) => (s.className.match(/k-(\w+)/) || [])[1]));
    check(P, JSON.stringify(kinds) === JSON.stringify(run.kinds), run.id + ": step kinds " + JSON.stringify(kinds) + ", expected " + JSON.stringify(run.kinds));
    await page.locator("#prev").click();
    check(P, (await text(page, "#c_calls")) === String(run.cost.calls - 1), run.id + ": Previous should go back one call");
  }
  const guard = FX.runs.find((r) => r.id === "Q07");
  await page.locator("#runPick").selectOption(String(FX.runs.indexOf(guard)));
  await page.locator("#all").click();
  check(P, (await text(page, "#steps")).includes("Guard: blocked: only SELECT or WITH is allowed"), "Q07: the guard should block the DELETE");
  // spot the ungrounded number
  const planted = FX.runs.flatMap((r) => r.ungrounded.map((n) => [r.id, n]));
  check(P, planted.length === 1, "expected one planted ungrounded number in the fixtures, found " + planted.length);
  const [pid, pnum] = planted[0];
  const plantedBtn = page.locator('#review button[data-key^="' + pid + '|"][data-num="' + pnum + '"]');
  const wrongBtn = page.locator('#review button[data-key^="Q03|"][data-num="84"]');
  await page.locator("#checkFlags").click();
  check(P, (await text(page, "#flagFeedback")).includes("You missed 1"), "checking with no flags should say one was missed");
  await wrongBtn.click();
  await page.locator("#checkFlags").click();
  check(P, (await page.locator("#flagFeedback").getAttribute("class")) === "badbox" && (await text(page, "#flagFeedback")).includes("look again: 84"), "flagging 84 should be rejected");
  await wrongBtn.click();
  check(P, (await wrongBtn.getAttribute("aria-pressed")) === "false", "a second click should unflag 84");
  await plantedBtn.click();
  await page.locator("#checkFlags").click();
  check(P, (await page.locator("#flagFeedback").getAttribute("class")) === "okbox" && (await text(page, "#flagFeedback")).includes("Only " + pnum), "flagging only " + pnum + " should be accepted, got: " + (await text(page, "#flagFeedback")));
  await page.locator("#revealFlags").click();
  check(P, (await page.locator("#flagAnswer").isVisible()) && (await page.locator("#revealFlags").getAttribute("aria-expanded")) === "true", "Show the answer should open the answer");
  // keyboard: Space on a number toggles it, Enter on Next steps forward
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  check(P, await tabTo(page, '#review button[data-key^="Q03|"][data-num="84"]'), "cannot Tab to a number button");
  await page.keyboard.press("Space");
  check(P, (await wrongBtn.getAttribute("aria-pressed")) === "true", "Space on a number should flag it");
  await page.keyboard.press("Space");
  check(P, (await wrongBtn.getAttribute("aria-pressed")) === "false", "Space again should unflag it");
  await page.locator("#runPick").selectOption("0");
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  check(P, await tabTo(page, "#next"), "cannot Tab to Next step");
  await page.keyboard.press("Enter");
  await page.keyboard.press("Enter");
  check(P, (await text(page, "#progress")).includes("Showing step 3 of"), "Enter twice on Next should show step 3, got: " + (await text(page, "#progress")));
}

async function testIndex(page, P) {
  const hrefs = await page.evaluate(() => Array.from(document.querySelectorAll("a[href]")).map((a) => a.getAttribute("href")).filter((h) => !h.startsWith("..")));
  const pages = ["join-fanout.html", "window-functions.html", "cohort-triangle.html", "ab-test.html", "agent-loop.html"];
  for (const p of pages) check(P, hrefs.includes(p), "no link to " + p);
  // keyboard: Tab to the first page link and follow it with Enter
  check(P, await tabTo(page, 'a[href="join-fanout.html"]'), "cannot Tab to the first page link");
  await Promise.all([page.waitForURL(/join-fanout\.html$/), page.keyboard.press("Enter")]);
  check(P, (await text(page, "h1")) === "Join fan-out explorer", "Enter on the link did not open the join page");
  await page.goBack();
}

const PAGES = [
  ["index", testIndex],
  ["join-fanout", testJoin],
  ["window-functions", testWindow],
  ["cohort-triangle", testCohort],
  ["ab-test", testAb],
  ["agent-loop", testAgent]
];

const t0 = Date.now();
const browser = await chromium.launch();
try {
  for (const [name, fn] of PAGES) {
    const file = path.join(VIS, name + ".html");
    if (!fs.existsSync(file)) { check(name, false, "missing file " + file); continue; }
    const context = await browser.newContext({ viewport: { width: 375, height: 740 }, colorScheme: "light" });
    const outside = [];
    await context.route((url) => url.protocol !== "file:", (route) => route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on("console", (m) => { if (m.type() === "error") errors.push("console error: " + m.text()); });
    page.on("pageerror", (e) => errors.push("page error: " + e.message));
    page.on("request", (r) => { if (!r.url().startsWith("file:")) outside.push(r.url()); });
    page.on("dialog", (d) => { errors.push("unexpected dialog: " + d.message()); d.dismiss(); });
    try {
      await page.goto(pathToFileURL(file).href, { waitUntil: "load" });
      await commonChecks(page, name);
      await fn(page, name);
      await layoutCheck(page, name, "after the interactions");
    } catch (e) {
      check(name, false, "test crashed: " + String(e.message || e).split("\n")[0]);
    }
    for (const e of errors) check(name, false, e);
    check(name, outside.length === 0, "made " + outside.length + " request(s) that are not file://: " + [...new Set(outside)].slice(0, 3).join(", "));
    await context.close();
  }
} finally {
  await browser.close();
}

const secs = ((Date.now() - t0) / 1000).toFixed(1);
if (failures.length) {
  for (const f of failures) console.log("FAIL " + f);
  console.log(failures.length + " of " + checks + " browser checks failed (" + secs + " s).");
  process.exit(1);
}
console.log("OK: " + checks + " browser checks passed on " + PAGES.length + " pages (" + secs + " s).");
