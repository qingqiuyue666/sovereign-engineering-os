#!/usr/bin/env node
"use strict";

const fs = require("fs");

const RUNNER_TYPE = "playwright_local_fixture_smoke_runner_v1";
const MARKER_TEXT = "SOVEREIGN_PLAYWRIGHT_LOCAL_FIXTURE_SMOKE_MARKER";

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key || !key.startsWith("--") || value === undefined) {
      throw new Error("invalid_args");
    }
    parsed[key.slice(2)] = value;
  }
  return parsed;
}

function writeJson(path, payload) {
  fs.writeFileSync(path, `${JSON.stringify(payload, null, 2)}\n`, {
    encoding: "utf8",
    flag: "wx",
  });
}

function basePayload(fixtureUrl, screenshotPath) {
  return {
    runner_type: RUNNER_TYPE,
    fixture_url: fixtureUrl,
    marker_found: false,
    click_completed: false,
    status_text: "",
    non_local_request_count: 0,
    non_local_requests: [],
    screenshot_path: screenshotPath,
    success: false,
  };
}

function fail(outputJson, payload, errorCode, exitCode = 1) {
  const failed = { ...payload, error_code: errorCode, success: false };
  if (outputJson && !fs.existsSync(outputJson)) {
    writeJson(outputJson, failed);
  }
  console.error(errorCode);
  process.exit(exitCode);
}

function isLocalRequest(url) {
  return (
    url.startsWith("file://") ||
    url.startsWith("data:") ||
    url.startsWith("blob:") ||
    url === "about:blank"
  );
}

async function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (_error) {
    console.error("invalid_args");
    process.exit(2);
  }

  const fixtureUrl = args["fixture-url"];
  const outputJson = args["output-json"];
  const screenshotPath = args["screenshot-path"];
  const payload = basePayload(fixtureUrl, screenshotPath);

  if (!fixtureUrl || !outputJson || !screenshotPath) {
    fail(outputJson, payload, "missing_required_args", 2);
  }
  if (!fixtureUrl.startsWith("file://")) {
    fail(outputJson, payload, "non_file_fixture_url", 2);
  }

  let chromium;
  try {
    ({ chromium } = require("playwright"));
  } catch (_error) {
    fail(outputJson, payload, "playwright_dependency_missing", 1);
  }

  let browser;
  let context;
  const nonLocalRequests = [];
  const recordNonLocal = (url) => {
    if (!isLocalRequest(url) && !nonLocalRequests.includes(url)) {
      nonLocalRequests.push(url);
    }
  };

  try {
    browser = await chromium.launch({ headless: true });
    context = await browser.newContext({
      storageState: { cookies: [], origins: [] },
      ignoreHTTPSErrors: false,
    });
    await context.route("**/*", async (route) => {
      const requestUrl = route.request().url();
      if (isLocalRequest(requestUrl)) {
        await route.continue();
        return;
      }
      recordNonLocal(requestUrl);
      await route.abort("blockedbyclient");
    });

    const page = await context.newPage();
    page.on("request", (request) => {
      recordNonLocal(request.url());
    });

    await page.goto(fixtureUrl, { waitUntil: "load" });
    payload.marker_found = await page.locator(`text=${MARKER_TEXT}`).count() > 0;
    await page.click("#smoke-button");
    await page.waitForFunction(() => {
      const status = document.getElementById("smoke-status");
      return status && status.textContent === "clicked";
    });
    payload.click_completed = true;
    payload.status_text = await page.textContent("#smoke-status");
    await page.screenshot({ path: screenshotPath });
    payload.non_local_requests = nonLocalRequests;
    payload.non_local_request_count = nonLocalRequests.length;
    payload.success = (
      payload.marker_found &&
      payload.click_completed &&
      payload.status_text === "clicked" &&
      payload.non_local_request_count === 0
    );
    writeJson(outputJson, payload);
    process.exitCode = payload.success ? 0 : 1;
    return;
  } catch (error) {
    payload.non_local_requests = nonLocalRequests;
    payload.non_local_request_count = nonLocalRequests.length;
    const errorCode = `runner_error:${String(error.message || error)}`;
    const failed = { ...payload, error_code: errorCode, success: false };
    if (!fs.existsSync(outputJson)) {
      writeJson(outputJson, failed);
    }
    console.error(errorCode);
    process.exitCode = 1;
    return;
  } finally {
    if (context) {
      await context.close().catch(() => {});
    }
    if (browser) {
      await browser.close().catch(() => {});
    }
  }
}

main().catch((error) => {
  console.error(`runner_unhandled:${String(error.message || error)}`);
  process.exit(1);
});
