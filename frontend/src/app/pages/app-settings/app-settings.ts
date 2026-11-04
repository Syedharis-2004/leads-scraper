import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
import { SettingsService } from '../../core/services/settings.service';

@Component({
  selector: 'app-app-settings',
  imports: [CommonModule],
  template: `
    <div class="p-6 lg:p-8 max-w-3xl mx-auto">
      <h1 class="text-2xl font-bold text-white mb-1">Application Settings</h1>
      <p class="text-ink-400 text-sm mb-6">System information and configuration</p>

      <!-- Backend status -->
      <div class="card mb-6">
        <h2 class="card-title mb-4">Backend Status</h2>
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm text-ink-300">Service</span>
            <span class="text-sm text-white">{{ health()?.service || '—' }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-ink-300">Version</span>
            <span class="text-sm text-white">{{ health()?.version || '—' }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-ink-300">Status</span>
            @if (health()?.status === 'ok') {
              <span class="badge-success">Online</span>
            } @else {
              <span class="badge-error">Offline</span>
            }
          </div>
        </div>
      </div>

      <!-- Storage info -->
      <div class="card mb-6">
        <h2 class="card-title mb-4">Data Storage</h2>
        <div class="space-y-3 text-sm">
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <div>
              <p class="text-ink-300 font-medium">CSV Lead Storage</p>
              <p class="text-ink-400 text-xs">All leads are stored in <code class="text-teal-400">data/leads.csv</code> on this machine. No cloud database is used.</p>
            </div>
          </div>
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
            </svg>
            <div>
              <p class="text-ink-300 font-medium">API Key Storage</p>
              <p class="text-ink-400 text-xs">API keys are stored securely using Windows Credential Manager with DPAPI encryption fallback.</p>
            </div>
          </div>
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
            </svg>
            <div>
              <p class="text-ink-300 font-medium">Application Logs</p>
              <p class="text-ink-400 text-xs">Logs are written to <code class="text-teal-400">logs/app.log</code> with automatic rotation. Secrets are automatically redacted.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Technology stack -->
      <div class="card mb-6">
        <h2 class="card-title mb-4">Technology Stack</h2>
        <div class="grid grid-cols-2 gap-3">
          <div class="bg-ink-800 rounded-lg p-3">
            <p class="text-xs text-ink-400">Backend</p>
            <p class="text-sm text-white font-medium">FastAPI + Python 3.12</p>
          </div>
          <div class="bg-ink-800 rounded-lg p-3">
            <p class="text-xs text-ink-400">Frontend</p>
            <p class="text-sm text-white font-medium">Angular 20 + Tailwind CSS</p>
          </div>
          <div class="bg-ink-800 rounded-lg p-3">
            <p class="text-xs text-ink-400">Scraping Engine</p>
            <p class="text-sm text-white font-medium">ScrapeGraphAI</p>
          </div>
          <div class="bg-ink-800 rounded-lg p-3">
            <p class="text-xs text-ink-400">AI Model</p>
            <p class="text-sm text-white font-medium">Google Gemini</p>
          </div>
          <div class="bg-ink-800 rounded-lg p-3">
            <p class="text-xs text-ink-400">Search</p>
            <p class="text-sm text-white font-medium">DuckDuckGo</p>
          </div>
          <div class="bg-ink-800 rounded-lg p-3">
            <p class="text-xs text-ink-400">Storage</p>
            <p class="text-sm text-white font-medium">CSV (local file)</p>
          </div>
        </div>
      </div>

      <!-- Security note -->
      <div class="card border-teal-500/20">
        <div class="flex items-start gap-3">
          <svg class="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
          </svg>
          <div>
            <p class="text-sm text-ink-200 font-medium mb-1">Privacy & Security</p>
            <p class="text-xs text-ink-400 leading-relaxed">
              This application runs entirely on your local machine. No data is sent to any cloud server except
              the Google Gemini API (for prompt understanding and data extraction) and DuckDuckGo (for business
              discovery). Your API key never appears in logs, frontend responses, or error messages.
            </p>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class AppSettings {
  private dashboardService = inject(DashboardService);
  private settingsService = inject(SettingsService);

  health = signal<{ status: string; service: string; version: string } | null>(null);

  constructor() {
    this.dashboardService.getHealth().subscribe({
      next: (res) => this.health.set(res),
      error: () => this.health.set(null),
    });
  }
}
