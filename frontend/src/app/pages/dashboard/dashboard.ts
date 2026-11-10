import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { DashboardService } from '../../core/services/dashboard.service';
import { DashboardStats, Lead } from '../../core/models';

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6 lg:p-8 max-w-7xl mx-auto">
      <h1 class="text-2xl font-bold text-white mb-1">Dashboard</h1>
      <p class="text-ink-400 text-sm mb-6">Overview of your lead generation and verification activity</p>

      @if (loading()) {
        <div class="flex items-center gap-3 text-ink-400 py-12">
          <svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8"/>
          </svg>
          Loading statistics...
        </div>
      } @else {
        <!-- Primary Stat cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-6">
          <div class="stat-card">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-teal-500/15 flex items-center justify-center">
                <svg class="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-5.13a4 4 0 11-8 0 4 4 0 018 0zm6 0a4 4 0 11-8 0 4 4 0 018 0z"/>
                </svg>
              </div>
              <span class="stat-label">Total Leads</span>
            </div>
            <span class="stat-value">{{ stats()?.total_leads ?? 0 }}</span>
          </div>

          <div class="stat-card">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-blue-500/15 flex items-center justify-center">
                <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
              </div>
              <span class="stat-label">Today</span>
            </div>
            <span class="stat-value">{{ stats()?.leads_today ?? 0 }}</span>
          </div>

          <div class="stat-card">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-purple-500/15 flex items-center justify-center">
                <svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
              </div>
              <span class="stat-label">Total Searches</span>
            </div>
            <span class="stat-value">{{ stats()?.total_searches ?? 0 }}</span>
          </div>

          <div class="stat-card">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-teal-500/15 flex items-center justify-center">
                <svg class="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                </svg>
              </div>
              <span class="stat-label">Successful</span>
            </div>
            <span class="stat-value text-teal-400">{{ stats()?.successful_searches ?? 0 }}</span>
          </div>

          <div class="stat-card">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-red-500/15 flex items-center justify-center">
                <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </div>
              <span class="stat-label">Failed</span>
            </div>
            <span class="stat-value text-red-400">{{ stats()?.failed_searches ?? 0 }}</span>
          </div>
        </div>

        <!-- Verification Metrics Cards -->
        <div class="card mb-8">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-lg bg-teal-500/15 flex items-center justify-center">
                <svg class="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              </div>
              <h2 class="card-title">Lead Verification Overview</h2>
            </div>
            <a routerLink="/all-leads" class="btn-primary !py-1.5 !px-3 text-xs flex items-center gap-1">
              Verify Leads
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
              </svg>
            </a>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div class="bg-ink-800/60 p-3 rounded-lg border border-ink-700">
              <span class="text-xs text-ink-400 block mb-1">Total Verified</span>
              <span class="text-xl font-bold text-white">{{ stats()?.verification_stats?.verified ?? 0 }}</span>
            </div>
            <div class="bg-ink-800/60 p-3 rounded-lg border border-ink-700">
              <span class="text-xs text-ink-400 block mb-1">Unverified</span>
              <span class="text-xl font-bold text-ink-300">{{ stats()?.verification_stats?.unverified ?? 0 }}</span>
            </div>
            <div class="bg-ink-800/60 p-3 rounded-lg border border-emerald-500/20">
              <span class="text-xs text-emerald-400 block mb-1">Deliverable / Valid</span>
              <span class="text-xl font-bold text-emerald-400">{{ stats()?.verification_stats?.valid ?? 0 }}</span>
            </div>
            <div class="bg-ink-800/60 p-3 rounded-lg border border-amber-500/20">
              <span class="text-xs text-amber-400 block mb-1">Risky / Unconfirmed</span>
              <span class="text-xl font-bold text-amber-400">{{ stats()?.verification_stats?.risky ?? 0 }}</span>
            </div>
            <div class="bg-ink-800/60 p-3 rounded-lg border border-red-500/20">
              <span class="text-xs text-red-400 block mb-1">Invalid / Undeliverable</span>
              <span class="text-xl font-bold text-red-400">{{ stats()?.verification_stats?.invalid ?? 0 }}</span>
            </div>
            <div class="bg-ink-800/60 p-3 rounded-lg border border-purple-500/20">
              <span class="text-xs text-purple-400 block mb-1">Unknown / Timeout</span>
              <span class="text-xl font-bold text-purple-400">{{ stats()?.verification_stats?.unknown ?? 0 }}</span>
            </div>
          </div>
        </div>

        <!-- Recent Leads -->
        <div class="card mb-8">
          <div class="card-header">
            <h2 class="card-title">Recent Leads</h2>
            <a routerLink="/all-leads" class="btn-ghost text-sm">
              View all
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
              </svg>
            </a>
          </div>

          @if ((stats()?.recent_leads ?? []).length === 0) {
            <div class="text-center py-12 text-ink-400">
              <svg class="w-12 h-12 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 17H7A5 5 0 017 7h2m6 10h2a5 5 0 000-10h-2M8 12h8"/>
              </svg>
              <p>No leads yet. Start by finding leads!</p>
              <a routerLink="/find-leads" class="btn-primary mt-4">Find Leads</a>
            </div>
          } @else {
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>City</th>
                    <th>Type</th>
                    <th>Email</th>
                    <th>Verification</th>
                    <th>Website</th>
                    <th>Generated</th>
                  </tr>
                </thead>
                <tbody>
                  @for (lead of stats()?.recent_leads ?? []; track lead.lead_id) {
                    <tr>
                      <td class="font-medium text-white">{{ lead.company_name || '—' }}</td>
                      <td>{{ lead.city || '—' }}</td>
                      <td>{{ lead.business_type || '—' }}</td>
                      <td>
                        @if (lead.email) {
                          <span class="truncate inline-block max-w-[150px]" [title]="lead.email">{{ lead.email }}</span>
                        } @else { — }
                      </td>
                      <td>
                        @if (lead.verification_status === 'VALID') {
                          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            VALID
                          </span>
                        } @else if (lead.verification_status === 'RISKY') {
                          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                            RISKY
                          </span>
                        } @else if (lead.verification_status === 'INVALID') {
                          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-500/15 text-red-400 border border-red-500/30">
                            INVALID
                          </span>
                        } @else if (lead.verification_status === 'UNKNOWN') {
                          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-500/15 text-purple-400 border border-purple-500/30">
                            UNKNOWN
                          </span>
                        } @else {
                          <span class="text-xs text-ink-400">Unverified</span>
                        }
                      </td>
                      <td>
                        @if (lead.website) {
                          <a [href]="lead.website" target="_blank" rel="noopener" class="text-teal-400 hover:underline truncate inline-block max-w-[150px]">
                            {{ lead.website }}
                          </a>
                        } @else { — }
                      </td>
                      <td class="text-ink-400 text-xs whitespace-nowrap">{{ lead.generated_at || '—' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>

        <!-- Quick Actions -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a routerLink="/find-leads" class="card hover:border-teal-500 transition-colors cursor-pointer group">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-lg bg-teal-500/15 flex items-center justify-center group-hover:bg-teal-500/25 transition-colors">
                <svg class="w-6 h-6 text-teal-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
              </div>
              <div>
                <h3 class="text-white font-semibold">Find New Leads</h3>
                <p class="text-ink-400 text-sm">Discover and scrape business leads using AI</p>
              </div>
            </div>
          </a>

          <a routerLink="/all-leads" class="card hover:border-teal-500 transition-colors cursor-pointer group">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-lg bg-emerald-500/15 flex items-center justify-center group-hover:bg-emerald-500/25 transition-colors">
                <svg class="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              </div>
              <div>
                <h3 class="text-white font-semibold">Verify Leads</h3>
                <p class="text-ink-400 text-sm">Validate email syntax, DNS, MX & deliverability</p>
              </div>
            </div>
          </a>

          <a routerLink="/api-settings" class="card hover:border-teal-500 transition-colors cursor-pointer group">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-lg bg-blue-500/15 flex items-center justify-center group-hover:bg-blue-500/25 transition-colors">
                <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
              </div>
              <div>
                <h3 class="text-white font-semibold">Settings</h3>
                <p class="text-ink-400 text-sm">Configure Gemini and Verification API keys</p>
              </div>
            </div>
          </a>
        </div>
      }
    </div>
  `,
})
export class Dashboard implements OnInit {
  private dashboardService = inject(DashboardService);

  stats = signal<DashboardStats | null>(null);
  loading = signal(true);

  ngOnInit() {
    this.loadStats();
  }

  loadStats() {
    this.loading.set(true);
    this.dashboardService.getStats().subscribe({
      next: (res) => {
        this.stats.set(res);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load stats', err);
        this.loading.set(false);
      },
    });
  }
}
