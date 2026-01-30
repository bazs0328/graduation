import { expect, test } from '@playwright/test';

test('topbar and nav render', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('学习助理', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: '问答' })).toBeVisible();
  await expect(page.getByText('会话 ID')).toBeVisible();
});

test('chat page renders form', async ({ page }) => {
  await page.goto('/chat');
  await expect(page.getByRole('heading', { name: '提问' })).toBeVisible();
  await expect(page.getByPlaceholder('请输入与资料相关的问题')).toBeVisible();
  await expect(page.getByRole('button', { name: '发送' })).toBeVisible();
});
