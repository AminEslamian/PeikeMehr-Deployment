import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  clearAuth,
  getAccessToken,
  getRefreshToken,
  refreshAccessToken,
  resolveMediaUrl,
  setTokens,
} from './api';

describe('resolveMediaUrl', () => {
  it('returns an empty string for missing values', () => {
    expect(resolveMediaUrl(null)).toBe('');
    expect(resolveMediaUrl(undefined)).toBe('');
  });

  it('keeps same-origin media paths', () => {
    expect(resolveMediaUrl('/media/reports/images/a.png')).toBe(
      '/media/reports/images/a.png',
    );
  });

  it('preserves absolute S3-compatible URLs', () => {
    const url = 'https://storage.example.com/bucket/reports/a.png?X-Amz-Signature=abc';
    expect(resolveMediaUrl(url)).toBe(url);
  });

  it('normalizes the local Django dev host to a path', () => {
    expect(resolveMediaUrl('http://127.0.0.1:8000/media/a.png')).toBe(
      '/media/a.png',
    );
  });

  it('adds the media prefix to a bare file name', () => {
    expect(resolveMediaUrl('reports/a.png')).toBe('/media/reports/a.png');
  });
});

describe('token storage', () => {
  beforeEach(() => localStorage.clear());

  it('stores and clears tokens', () => {
    setTokens('access-1', 'refresh-1');
    expect(getAccessToken()).toBe('access-1');
    expect(getRefreshToken()).toBe('refresh-1');

    clearAuth();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});

describe('refreshAccessToken', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it('stores rotated access and refresh tokens', async () => {
    setTokens('old-access', 'old-refresh');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ access: 'new-access', refresh: 'new-refresh' }),
      }),
    );

    await expect(refreshAccessToken()).resolves.toBe('new-access');
    expect(getAccessToken()).toBe('new-access');
    expect(getRefreshToken()).toBe('new-refresh');
  });

  it('returns null when no refresh token exists', async () => {
    await expect(refreshAccessToken()).resolves.toBeNull();
  });

  it('returns null when the refresh endpoint rejects the token', async () => {
    setTokens('old-access', 'expired-refresh');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({}),
      }),
    );

    await expect(refreshAccessToken()).resolves.toBeNull();
    expect(getAccessToken()).toBe('old-access');
  });
});
