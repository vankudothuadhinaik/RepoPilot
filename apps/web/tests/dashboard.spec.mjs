import { test, expect } from "@playwright/test";

test("shows the authentication prompt when the API requires a token", async ({ page }) => {
  await page.route("**/api/repos", async (route) => {
    const authorization = route.request().headers()["authorization"];
    if (authorization !== "Bearer test-token") {
      await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Missing or invalid bearer token" }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText("Authentication required");
  await page.getByPlaceholder("Bearer token from Doppler").fill("test-token");
  await page.getByRole("button", { name: "Connect / refresh" }).click();
  await expect(page.getByRole("status")).toContainText("No repositories indexed yet.");
});

test("searches and displays line-addressable repository evidence", async ({ page }) => {
  await page.route("**/api/repos", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "repo-1", name: "sample", root_path: "/sample", file_count: 3, symbol_count: 1, status: "ready" }]) }));
  await page.route("**/api/repos/repo-1/search", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ query: "greet", result_count: 1, results: [{ path: "app.py", language: "python", snippet: "def greet():", rank: 1 }] }) }));
  await page.route("**/api/repos/repo-1/ask", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ answer: "Function definition is shown in the evidence below.", abstained: false, mode: "retrieval_only", evidence: [{ path: "app.py", language: "python", start_line: 1, end_line: 2, snippet: "1: def greet():\n2:     return 'hello'", sha256: "0123456789abcdef0123456789abcdef", indexed_commit: "abc123" }] }) }));
  await page.goto("/");
  await expect(page.getByRole("button", { name: /sample/ })).toBeVisible();
  await page.getByPlaceholder("Try a function name, error message, or identifier").fill("greet");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.locator(".result code")).toContainText("app.py");
  await page.getByRole("button", { name: "Retrieve evidence citations" }).click();
  await expect(page.locator(".evidence-answer")).toContainText("Function definition");
  await expect(page.locator(".result pre")).toContainText("def greet()");
});
