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
      <p class="text-ink-400 text-sm mb-6">Overview of your lead generation activity</p>

      @if (loading()) {
        <div class="flex items-center gap-3 text-ink-400 py-12">
          <svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8"/>
          </svg>
          Loading statistics...
        </div>
      } @else {
        <!-- Stat cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-8">
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
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <a routerLink="/find-leads" class="card hover:border-teal-500 transition-colors cursor-pointer group">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-lg bg-teal-500/15 flex items-center justify-center group-hover:bg-teal-500/25 transition-colors">
                <svg class="w-6 h-6 text-teal-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
              </div>
              <div>
                <h3 class="text-white font-semibold">Find New Leads</h3>
                <p class="text-ink-400 text-sm">Enter a natural-language prompt to discover businesses</p>
              </div>
            </div>
          </a>

          <a routerLink="/api-settings" class="card hover:border-teal-500 transition-colors cursor-pointer group">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-lg bg-blue-500/15 flex items-center justify-center group-hover:bg-blue-500/25 transition-colors">
                <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 7a4 4 0 11-8 0 4 4 0 018 0zM12 15a7 7 0 00-7 7m14 0a7 7 0 00-7-7"/>
                </svg>
              </div>
              <div>
                <h3 class="text-white font-semibold">API Settings</h3>
                <p class="text-ink-400 text-sm">Configure your Gemini API key</p>
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

  loading = signal(true);
  stats = signal<DashboardStats | null>(null);

  ngOnInit() {
    this.loadStats();
  }

  loadStats() {
    this.loading.set(true);
    this.dashboardService.getStats().subscribe({
      next: (data) => {
        this.stats.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load stats', err);
        this.loading.set(false);
      },
    });
  }
}
