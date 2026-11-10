import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LeadsService, LeadQuery } from '../../core/services/leads.service';
import { VerificationService } from '../../core/services/verification.service';
import {
  BatchVerificationStatus,
  Lead,
  LeadListResponse,
  SingleVerificationResponse,
  VerificationStats,
} from '../../core/models';

@Component({
  selector: 'app-all-leads',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 lg:p-8 max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 class="text-2xl font-bold text-white mb-1">All Leads</h1>
          <p class="text-ink-400 text-sm">
            {{ total() }} total leads &bull; Manage, verify email deliverability, and export leads
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <!-- Refresh -->
          <button class="btn-secondary" (click)="loadLeads()" [disabled]="loading()">
            <svg class="w-4 h-4" [class.animate-spin]="loading()" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            Refresh
          </button>

          <!-- Verify Selected -->
          @if (selectedLeadIds.size > 0) {
            <button
              class="btn-primary flex items-center gap-1.5"
              (click)="verifySelected()"
              [disabled]="activeJob()?.is_running">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              Verify Selected ({{ selectedLeadIds.size }})
            </button>
          }

          <!-- Verify All Unverified -->
          <button
            class="btn-secondary text-teal-400 border-teal-500/30 hover:border-teal-400 flex items-center gap-1.5"
            (click)="verifyAllUnverified()"
            [disabled]="activeJob()?.is_running">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
            Verify Unverified
          </button>

          <!-- Export Dropdown -->
          <div class="relative group">
            <button class="btn-secondary">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              Export
              <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            <div class="absolute right-0 mt-2 w-56 bg-ink-800 border border-ink-600 rounded-lg shadow-xl py-1 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <a [href]="exportUrl('csv', '')" class="block px-4 py-2 text-sm text-ink-200 hover:bg-ink-700" download>Export All (CSV)</a>
              <a [href]="exportUrl('csv', 'VERIFIED')" class="block px-4 py-2 text-sm text-ink-200 hover:bg-ink-700 text-teal-400" download>Export Verified Only (CSV)</a>
              <a [href]="exportUrl('csv', 'VALID')" class="block px-4 py-2 text-sm text-ink-200 hover:bg-ink-700 text-emerald-400" download>Export Valid Only (CSV)</a>
              <a [href]="exportUrl('csv', 'RISKY')" class="block px-4 py-2 text-sm text-ink-200 hover:bg-ink-700 text-amber-400" download>Export Risky Only (CSV)</a>
              <div class="border-t border-ink-700 my-1"></div>
              <a [href]="exportUrl('json', '')" class="block px-4 py-2 text-sm text-ink-200 hover:bg-ink-700" download>Export All (JSON)</a>
              <a [href]="exportUrl('json', 'VERIFIED')" class="block px-4 py-2 text-sm text-ink-200 hover:bg-ink-700" download>Export Verified (JSON)</a>
            </div>
          </div>
        </div>
      </div>

      <!-- Verification Active Job Banner -->
      @if (activeJob() && activeJob()?.is_running) {
        <div class="card mb-6 border-teal-500/40 bg-teal-950/20">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <svg class="w-5 h-5 text-teal-400 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8"/>
              </svg>
              <span class="text-sm font-semibold text-white">Batch Lead Verification in Progress</span>
            </div>
            <button class="btn-danger !py-1 !px-3 text-xs" (click)="cancelBatchJob()">Cancel</button>
          </div>
          <div class="w-full bg-ink-800 rounded-full h-2.5 mb-2 overflow-hidden">
            <div
              class="bg-teal-500 h-2.5 rounded-full transition-all duration-300"
              [style.width.%]="activeJob()?.progress || 0"></div>
          </div>
          <div class="flex flex-wrap items-center justify-between text-xs text-ink-300 gap-2">
            <span>{{ activeJob()?.message }} ({{ activeJob()?.processed_leads }} / {{ activeJob()?.total_leads }})</span>
            <div class="flex items-center gap-3">
              <span class="text-emerald-400 font-medium">Valid: {{ activeJob()?.valid_count }}</span>
              <span class="text-amber-400 font-medium">Risky: {{ activeJob()?.risky_count }}</span>
              <span class="text-red-400 font-medium">Invalid: {{ activeJob()?.invalid_count }}</span>
              <span class="text-ink-400">Unknown: {{ activeJob()?.unknown_count }}</span>
            </div>
          </div>
        </div>
      }

      <!-- Verification Summary Statistics Pills -->
      <div class="flex flex-wrap items-center gap-2 mb-6">
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors flex items-center gap-1.5"
          [class.bg-ink-800]="filters.verification_status !== ''"
          [class.border-ink-700]="filters.verification_status !== ''"
          [class.text-ink-300]="filters.verification_status !== ''"
          [class.bg-teal-500]="filters.verification_status === ''"
          [class.text-white]="filters.verification_status === ''"
          [class.border-teal-500]="filters.verification_status === ''"
          (click)="setStatusFilter('')">
          All Leads ({{ vStats()?.total ?? total() }})
        </button>
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors flex items-center gap-1.5"
          [class.bg-ink-800]="filters.verification_status !== 'VALID'"
          [class.border-ink-700]="filters.verification_status !== 'VALID'"
          [class.text-emerald-400]="filters.verification_status !== 'VALID'"
          [class.bg-emerald-500]="filters.verification_status === 'VALID'"
          [class.text-white]="filters.verification_status === 'VALID'"
          [class.border-emerald-500]="filters.verification_status === 'VALID'"
          (click)="setStatusFilter('VALID')">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
          Valid ({{ vStats()?.valid ?? 0 }})
        </button>
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors flex items-center gap-1.5"
          [class.bg-ink-800]="filters.verification_status !== 'RISKY'"
          [class.border-ink-700]="filters.verification_status !== 'RISKY'"
          [class.text-amber-400]="filters.verification_status !== 'RISKY'"
          [class.bg-amber-500]="filters.verification_status === 'RISKY'"
          [class.text-white]="filters.verification_status === 'RISKY'"
          [class.border-amber-500]="filters.verification_status === 'RISKY'"
          (click)="setStatusFilter('RISKY')">
          <span class="w-2 h-2 rounded-full bg-amber-400"></span>
          Risky ({{ vStats()?.risky ?? 0 }})
        </button>
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors flex items-center gap-1.5"
          [class.bg-ink-800]="filters.verification_status !== 'INVALID'"
          [class.border-ink-700]="filters.verification_status !== 'INVALID'"
          [class.text-red-400]="filters.verification_status !== 'INVALID'"
          [class.bg-red-500]="filters.verification_status === 'INVALID'"
          [class.text-white]="filters.verification_status === 'INVALID'"
          [class.border-red-500]="filters.verification_status === 'INVALID'"
          (click)="setStatusFilter('INVALID')">
          <span class="w-2 h-2 rounded-full bg-red-400"></span>
          Invalid ({{ vStats()?.invalid ?? 0 }})
        </button>
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors flex items-center gap-1.5"
          [class.bg-ink-800]="filters.verification_status !== 'UNKNOWN'"
          [class.border-ink-700]="filters.verification_status !== 'UNKNOWN'"
          [class.text-purple-400]="filters.verification_status !== 'UNKNOWN'"
          [class.bg-purple-500]="filters.verification_status === 'UNKNOWN'"
          [class.text-white]="filters.verification_status === 'UNKNOWN'"
          [class.border-purple-500]="filters.verification_status === 'UNKNOWN'"
          (click)="setStatusFilter('UNKNOWN')">
          <span class="w-2 h-2 rounded-full bg-purple-400"></span>
          Unknown ({{ vStats()?.unknown ?? 0 }})
        </button>
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors flex items-center gap-1.5"
          [class.bg-ink-800]="filters.verification_status !== 'UNVERIFIED'"
          [class.border-ink-700]="filters.verification_status !== 'UNVERIFIED'"
          [class.text-ink-400]="filters.verification_status !== 'UNVERIFIED'"
          [class.bg-ink-600]="filters.verification_status === 'UNVERIFIED'"
          [class.text-white]="filters.verification_status === 'UNVERIFIED'"
          [class.border-ink-500]="filters.verification_status === 'UNVERIFIED'"
          (click)="setStatusFilter('UNVERIFIED')">
          <span class="w-2 h-2 rounded-full bg-ink-400"></span>
          Unverified ({{ vStats()?.unverified ?? 0 }})
        </button>
      </div>

      <!-- Filters -->
      <div class="card mb-6">
        <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <div>
            <label class="label">Search</label>
            <input class="input" placeholder="Company name..." [(ngModel)]="filters.search" (ngModelChange)="onFilterChange()"/>
          </div>
          <div>
            <label class="label">City</label>
            <input class="input" placeholder="Filter by city..." [(ngModel)]="filters.city" (ngModelChange)="onFilterChange()"/>
          </div>
          <div>
            <label class="label">Business Type</label>
            <input class="input" placeholder="Filter by type..." [(ngModel)]="filters.business_type" (ngModelChange)="onFilterChange()"/>
          </div>
          <div>
            <label class="label">Verification Status</label>
            <select class="input" [(ngModel)]="filters.verification_status" (ngModelChange)="onFilterChange()">
              <option value="">All Statuses</option>
              <option value="VALID">Valid</option>
              <option value="RISKY">Risky</option>
              <option value="INVALID">Invalid</option>
              <option value="UNKNOWN">Unknown</option>
              <option value="UNVERIFIED">Unverified</option>
            </select>
          </div>
          <div>
            <label class="label">Sort By</label>
            <select class="input" [(ngModel)]="filters.sort_by" (ngModelChange)="onFilterChange()">
              <option value="generated_at">Generated Date</option>
              <option value="company_name">Company Name</option>
              <option value="city">City</option>
              <option value="business_type">Business Type</option>
              <option value="verification_status">Verification Status</option>
            </select>
          </div>
          <div>
            <label class="label">Sort Order</label>
            <select class="input" [(ngModel)]="filters.sort_order" (ngModelChange)="onFilterChange()">
              <option value="desc">Newest First</option>
              <option value="asc">Oldest First</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Table -->
      @if (loading()) {
        <div class="flex items-center gap-3 text-ink-400 py-12">
          <svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8"/>
          </svg>
          Loading leads...
        </div>
      } @else if (leads().length === 0) {
        <div class="text-center py-16 text-ink-400">
          <svg class="w-12 h-12 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 17H7A5 5 0 017 7h2m6 10h2a5 5 0 000-10h-2M8 12h8"/>
          </svg>
          <p class="mb-2">No leads found.</p>
          <p class="text-sm">Try adjusting your filters or generate new leads.</p>
        </div>
      } @else {
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th class="w-10">
                  <input
                    type="checkbox"
                    class="rounded border-ink-600 bg-ink-800 text-teal-500 focus:ring-teal-500"
                    [checked]="isAllSelected()"
                    (change)="toggleSelectAll()"
                    title="Select all on this page"
                  />
                </th>
                <th>Company</th>
                <th>Owner</th>
                <th>City</th>
                <th>Email</th>
                <th>Verification</th>
                <th>Phone</th>
                <th>Website</th>
                <th>Type</th>
                <th>Generated</th>
                <th class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (lead of leads(); track lead.lead_id) {
                <tr class="animate-fade-in" [class.bg-ink-800-40]="selectedLeadIds.has(lead.lead_id)">
                  <td>
                    <input
                      type="checkbox"
                      class="rounded border-ink-600 bg-ink-800 text-teal-500 focus:ring-teal-500"
                      [checked]="selectedLeadIds.has(lead.lead_id)"
                      (change)="toggleSelectLead(lead.lead_id)"
                    />
                  </td>
                  <td class="font-medium text-white">{{ lead.company_name || '—' }}</td>
                  <td>{{ lead.owner_name || '—' }}</td>
                  <td>{{ lead.city || '—' }}</td>
                  <td>
                    @if (lead.email) {
                      <div class="flex items-center gap-1">
                        <span class="truncate inline-block max-w-[130px]" [title]="lead.email">{{ lead.email }}</span>
                        <button class="text-ink-400 hover:text-teal-400" (click)="copyEmail(lead.email)" title="Copy email">
                          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                          </svg>
                        </button>
                      </div>
                    } @else { — }
                  </td>

                  <!-- Verification Status Badge with Tooltip -->
                  <td>
                    @if (verifyingIds.has(lead.lead_id)) {
                      <span class="inline-flex items-center gap-1 text-xs text-teal-400 font-medium">
                        <svg class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8"/>
                        </svg>
                        Checking...
                      </span>
                    } @else if (lead.verification_status === 'VALID') {
                      <span
                        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 cursor-help"
                        [title]="getTooltipText(lead)">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                        </svg>
                        VALID
                      </span>
                    } @else if (lead.verification_status === 'RISKY') {
                      <span
                        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30 cursor-help"
                        [title]="getTooltipText(lead)">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                        </svg>
                        RISKY
                      </span>
                    } @else if (lead.verification_status === 'INVALID') {
                      <span
                        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-500/15 text-red-400 border border-red-500/30 cursor-help"
                        [title]="getTooltipText(lead)">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                        INVALID
                      </span>
                    } @else if (lead.verification_status === 'UNKNOWN') {
                      <span
                        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-500/15 text-purple-400 border border-purple-500/30 cursor-help"
                        [title]="getTooltipText(lead)">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01"/>
                        </svg>
                        UNKNOWN
                      </span>
                    } @else {
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-ink-800 text-ink-400 border border-ink-700">
                        Unverified
                      </span>
                    }
                  </td>

                  <td class="whitespace-nowrap">{{ lead.phone || '—' }}</td>
                  <td>
                    @if (lead.website) {
                      <a [href]="lead.website" target="_blank" rel="noopener" class="text-teal-400 hover:underline truncate inline-block max-w-[120px]" [title]="lead.website">
                        {{ lead.website }}
                      </a>
                    } @else { — }
                  </td>
                  <td>{{ lead.business_type || '—' }}</td>
                  <td class="text-ink-400 text-xs whitespace-nowrap">{{ lead.generated_at || '—' }}</td>

                  <!-- Row Actions -->
                  <td class="text-right">
                    <div class="flex items-center justify-end gap-1.5">
                      <!-- Single verify button -->
                      <button
                        class="btn-secondary !px-2 !py-1 text-xs hover:text-teal-400 hover:border-teal-400"
                        (click)="verifySingleLead(lead)"
                        [disabled]="verifyingIds.has(lead.lead_id) || !lead.email"
                        [title]="lead.verification_status ? 'Re-verify lead' : 'Verify lead'">
                        @if (verifyingIds.has(lead.lead_id)) {
                          <svg class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8"/>
                          </svg>
                        } @else {
                          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                          </svg>
                        }
                        <span>{{ lead.verification_status ? 'Re-verify' : 'Verify' }}</span>
                      </button>

                      <!-- Delete button -->
                      <button class="btn-danger !px-2 !py-1 text-xs" (click)="deleteLead(lead.lead_id)" title="Delete lead">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="flex items-center justify-between mt-4">
          <p class="text-sm text-ink-400">
            Page {{ currentPage() }} of {{ totalPages() }} ({{ total() }} leads)
          </p>
          <div class="flex items-center gap-2">
            <button class="btn-secondary" [disabled]="currentPage() <= 1" (click)="prevPage()">Previous</button>
            <button class="btn-secondary" [disabled]="currentPage() >= totalPages()" (click)="nextPage()">Next</button>
          </div>
        </div>
      }
    </div>
  `,
})
export class AllLeads implements OnInit, OnDestroy {
  private leadsService = inject(LeadsService);
  private verificationService = inject(VerificationService);

  leads = signal<Lead[]>([]);
  total = signal(0);
  currentPage = signal(1);
  totalPages = signal(0);
  pageSize = 50;
  loading = signal(true);

  // Verification statistics and active batch job
  vStats = signal<VerificationStats | null>(null);
  activeJob = signal<BatchVerificationStatus | null>(null);
  selectedLeadIds = new Set<string>();
  verifyingIds = new Set<string>();

  private pollInterval: any = null;
  private filterTimeout: any = null;

  filters: LeadQuery = {
    search: '',
    city: '',
    business_type: '',
    verification_status: '',
    sort_by: 'generated_at',
    sort_order: 'desc',
    page: 1,
    page_size: 50,
  };

  ngOnInit() {
    this.loadLeads();
    this.loadStats();
    this.checkActiveBatchJob();
  }

  ngOnDestroy() {
    this.stopPolling();
    if (this.filterTimeout) clearTimeout(this.filterTimeout);
  }

  loadLeads() {
    this.loading.set(true);
    this.leadsService.listLeads(this.filters).subscribe({
      next: (res: LeadListResponse) => {
        this.leads.set(res.leads);
        this.total.set(res.total);
        this.totalPages.set(res.total_pages);
        this.currentPage.set(res.page);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load leads', err);
        this.loading.set(false);
      },
    });
  }

  loadStats() {
    this.verificationService.getVerificationStats().subscribe({
      next: (stats) => this.vStats.set(stats),
      error: (err) => console.error('Failed to load verification stats', err),
    });
  }

  setStatusFilter(status: string) {
    this.filters.verification_status = status;
    this.filters.page = 1;
    this.loadLeads();
  }

  onFilterChange() {
    if (this.filterTimeout) clearTimeout(this.filterTimeout);
    this.filterTimeout = setTimeout(() => {
      this.filters.page = 1;
      this.loadLeads();
    }, 400);
  }

  // --- Selection handling ---
  isAllSelected(): boolean {
    const list = this.leads();
    return list.length > 0 && list.every((l) => this.selectedLeadIds.has(l.lead_id));
  }

  toggleSelectAll() {
    if (this.isAllSelected()) {
      for (const lead of this.leads()) {
        this.selectedLeadIds.delete(lead.lead_id);
      }
    } else {
      for (const lead of this.leads()) {
        this.selectedLeadIds.add(lead.lead_id);
      }
    }
  }

  toggleSelectLead(leadId: string) {
    if (this.selectedLeadIds.has(leadId)) {
      this.selectedLeadIds.delete(leadId);
    } else {
      this.selectedLeadIds.add(leadId);
    }
  }

  // --- Single Lead Verification ---
  verifySingleLead(lead: Lead) {
    if (!lead.email) {
      alert('This lead record has no email address to verify.');
      return;
    }
    this.verifyingIds.add(lead.lead_id);

    this.verificationService.verifyLead(lead.lead_id).subscribe({
      next: (res: SingleVerificationResponse) => {
        this.verifyingIds.delete(lead.lead_id);
        // Update local record
        lead.verification_status = res.status;
        lead.verification_reason = res.reason;
        lead.verified_at = res.verified_at;
        this.loadStats();
      },
      error: (err) => {
        this.verifyingIds.delete(lead.lead_id);
        console.error('Verification failed', err);
        alert(`Verification failed: ${err.error?.detail || err.message}`);
      },
    });
  }

  // --- Batch Verification ---
  verifySelected() {
    const ids = Array.from(this.selectedLeadIds);
    if (!ids.length) return;

    this.verificationService.startBatchVerification({ lead_ids: ids }).subscribe({
      next: (res) => {
        this.selectedLeadIds.clear();
        this.startJobPolling(res.job_id);
      },
      error: (err) => {
        alert(`Failed to start verification: ${err.error?.detail || err.message}`);
      },
    });
  }

  verifyAllUnverified() {
    if (!confirm('Start batch verification for all unverified leads?')) return;
    this.verificationService.startBatchVerification({ verify_all_unverified: true }).subscribe({
      next: (res) => {
        this.startJobPolling(res.job_id);
      },
      error: (err) => {
        alert(`Failed to start verification: ${err.error?.detail || err.message}`);
      },
    });
  }

  checkActiveBatchJob() {
    this.verificationService.getActiveBatchJob().subscribe({
      next: (job) => {
        if (job && job.is_running) {
          this.activeJob.set(job);
          this.startJobPolling(job.job_id);
        }
      },
      error: () => {},
    });
  }

  startJobPolling(jobId: string) {
    this.stopPolling();
    this.pollInterval = setInterval(() => {
      this.verificationService.getBatchStatus(jobId).subscribe({
        next: (status) => {
          this.activeJob.set(status);
          if (status.is_completed || status.is_cancelled || !status.is_running) {
            this.stopPolling();
            this.loadLeads();
            this.loadStats();
          }
        },
        error: () => this.stopPolling(),
      });
    }, 1000);
  }

  cancelBatchJob() {
    const job = this.activeJob();
    if (!job) return;
    this.verificationService.cancelBatchJob(job.job_id).subscribe({
      next: () => {
        this.stopPolling();
        this.activeJob.set(null);
        this.loadLeads();
        this.loadStats();
      },
    });
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  getTooltipText(lead: Lead): string {
    const parts: string[] = [];
    if (lead.verification_reason) parts.push(`Reason: ${lead.verification_reason}`);
    if (lead.verified_at) parts.push(`Checked: ${lead.verified_at}`);
    return parts.join('\n') || 'Verification check completed';
  }

  prevPage() {
    if (this.filters.page! > 1) {
      this.filters.page!--;
      this.loadLeads();
    }
  }

  nextPage() {
    if (this.filters.page! < this.totalPages()) {
      this.filters.page!++;
      this.loadLeads();
    }
  }

  deleteLead(id: string) {
    if (!confirm('Delete this lead? This cannot be undone.')) return;
    this.leadsService.deleteLead(id).subscribe({
      next: () => {
        this.loadLeads();
        this.loadStats();
      },
      error: (err) => console.error('Delete failed', err),
    });
  }

  copyEmail(email: string) {
    navigator.clipboard.writeText(email).catch(() => {});
  }

  exportUrl(format: 'csv' | 'json', statusOverride?: string): string {
    const query = { ...this.filters };
    if (statusOverride !== undefined && statusOverride !== '') {
      query.verification_status = statusOverride;
    }
    return format === 'csv'
      ? this.leadsService.exportCsvUrl(query)
      : this.leadsService.exportJsonUrl(query);
  }
}
