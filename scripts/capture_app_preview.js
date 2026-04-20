const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = process.env.KNOWLEDGE_ASSISTANT_PREVIEW_URL || "http://127.0.0.1:8080";
const outputPath =
  process.env.KNOWLEDGE_ASSISTANT_PREVIEW_PATH ||
  path.resolve(__dirname, "..", "docs", "assets", "app-preview.png");

async function main() {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1560, height: 1880 },
    deviceScaleFactor: 1.5,
    colorScheme: "light",
  });

  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.locator("#hero-ask-button").click();

    await page.waitForFunction(() => {
      const answer = document.getElementById("answer");
      return answer && answer.textContent.includes("The strongest grounded match");
    });

    await page.waitForFunction(() => {
      return document.querySelectorAll("#citations .card").length >= 1;
    });

    await page.waitForFunction(() => {
      return document.querySelectorAll("#search-results .card").length >= 1;
    });

    await page.evaluate(() => {
      if (document.activeElement instanceof HTMLElement) {
        document.activeElement.blur();
      }
      window.scrollTo({ top: 0, behavior: "instant" });
    });

    await page.screenshot({
      path: outputPath,
      fullPage: true,
      animations: "disabled",
    });

    console.log(`Saved app preview to ${outputPath}`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
