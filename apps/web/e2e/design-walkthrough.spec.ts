import { expect, test } from "@playwright/test";

test.describe("CamCat design walkthrough", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("project layout, fixed product chrome and scrollable editor remain stable", async ({ page }) => {
    await page.goto("/");

    const projectLayout = page.getByTestId("project-layout");
    const projectRail = page.getByTestId("product-navigation");
    const projectContent = page.getByTestId("project-content");
    await expect(projectLayout).toBeVisible();
    await expect(projectRail).toBeVisible();
    await expect(projectContent).toBeVisible();

    const [railBox, contentBox] = await Promise.all([
      projectRail.boundingBox(),
      projectContent.boundingBox(),
    ]);
    expect(railBox).not.toBeNull();
    expect(contentBox).not.toBeNull();
    expect(railBox!.width).toBeCloseTo(96, 0);
    expect(contentBox!.x).toBeGreaterThanOrEqual(railBox!.x + railBox!.width);
    expect(contentBox!.y).toBeCloseTo(railBox!.y, 0);

    const firstCard = page.locator("article").first();
    const thumbnailBox = await firstCard.locator('button[aria-label^="打开项目 "]').boundingBox();
    const summaryBox = await firstCard.locator("button").nth(1).boundingBox();
    expect(thumbnailBox).not.toBeNull();
    expect(summaryBox).not.toBeNull();
    expect(thumbnailBox!.width).toBeGreaterThanOrEqual(150);
    expect(summaryBox!.x).toBeGreaterThanOrEqual(thumbnailBox!.x + thumbnailBox!.width);

    const openProject = page.locator('button[aria-label^="打开项目 "]').first();
    if (await openProject.count()) {
      await openProject.click();
    } else {
      await page.getByRole("button", { name: "新建项目" }).click();
      await page.getByLabel("项目名称").fill(`布局走查 ${Date.now()}`);
      await page.getByRole("button", { name: "创建并打开" }).click();
    }

    const editorHeader = page.getByTestId("app-header");
    const editorRail = page.getByTestId("product-navigation");
    const scrollRegion = page.getByTestId("editor-scroll-region");
    await expect(editorHeader).toBeVisible();
    await expect(editorRail).toBeVisible();
    await expect(scrollRegion).toBeVisible();
    await expect(scrollRegion).toHaveCSS("overflow-y", "auto");

    const initialScroll = await scrollRegion.evaluate((element) => ({
      top: element.scrollTop,
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
    }));
    expect(initialScroll.scrollHeight).toBeGreaterThan(initialScroll.clientHeight);
    await scrollRegion.hover();
    await page.mouse.wheel(0, 600);
    await expect.poll(() => scrollRegion.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);

    const headerBefore = await editorHeader.boundingBox();
    const railBefore = await editorRail.boundingBox();
    await page.getByRole("button", { name: "媒体处理", exact: true }).click();
    await expect(page.getByText("媒体处理状态", { exact: true }).last()).toBeVisible();
    expect(await editorHeader.boundingBox()).toEqual(headerBefore);
    expect(await editorRail.boundingBox()).toEqual(railBefore);

    await page.getByRole("button", { name: "导出渲染", exact: true }).click();
    await expect(page.getByText("导出 / 渲染状态", { exact: true }).last()).toBeVisible();
    expect(await editorHeader.boundingBox()).toEqual(headerBefore);
    expect(await editorRail.boundingBox()).toEqual(railBefore);
  });
});
