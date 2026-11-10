import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SettingsService } from '../../core/services/settings.service';
import { VerificationService } from '../../core/services/verification.service';
import {
  ApiKeyStatus,
  ApiKeyTestResult,
  SingleVerificationResponse,
  VerificationSettings,
} from '../../core/models';

@Component({
  selector: 'app-api-settings',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 lg:p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 class="text-2xl font-bold text-white mb-1">API &amp; Service Settings</h1>
        <p class="text-ink-400 text-sm">
          Configure AI extraction credentials and email verification provider settings
        </p>
      </div>

      <!-- ============================================================== -->
      <!-- SECTION 1: GEMINI API KEY -->
      <!-- ============================================================== -->
      <section>
        <div class="flex items-center gap-2 mb-3">
          <span class="w-2 h-2 rounded-full bg-teal-400"></span>
          <h2 class="text-lg font-semibold text-white">Google Gemini AI Settings</h2>
        </div>

        <!-- Key status -->
        <div class="card mb-4">
          <div class="flex items-center justify-between mb-4">
            <h3 class="card-title">Gemini API Key Status</h3>
            @if (keyStatus()?.has_key) {
              <span class="badge-success">Configured</span>
            } @else {
              <span class="badge-error">Not Set</span>
            }
          </div>

          @if (keyStatus()?.has_key) {
            <div class="flex items-center gap-2 text-sm text-ink-300">
              <svg class="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
              A Gemini API key is securely stored on this machine in Windows Credential Manager.
            </div>
          } @else {
            <div class="flex items-center gap-2 text-sm text-ink-300">
              <svg class="w-4 h-4 text-ink-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
              No API key configured. Enter your key below to enable AI lead discovery.
            </div>
          }

          <!-- Get key link -->
          <div class="mt-4 pt-4 border-t border-ink-700">
            <p class="text-xs text-ink-400 mb-1">Need a key?</p>
            <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener" class="text-teal-400 text-sm hover:underline inline-flex items-center gap-1">
              Get a free key from Google AI Studio
              <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
              </svg>
            </a>
          </div>
        </div>

        <!-- Key input -->
        <div class="card mb-4">
          <h3 class="card-title mb-4">{{ keyStatus()?.has_key ? 'Update Gemini Key' : 'Enter Gemini Key' }}</h3>
          <label class="label" for="apiKey">Gemini API Key</label>
          <div class="relative">
            <input
              id="apiKey"
              [type]="showKey() ? 'text' : 'password'"
              class="input pr-10"
              placeholder="AIza..."
              [(ngModel)]="apiKey"
              autocomplete="off"/>
            <button
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-ink-400 hover:text-white p-1"
              (click)="showKey.set(!showKey())">
              @if (showKey()) {
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              } @else {
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
              }
            </button>
          </div>

          <div class="flex flex-wrap items-center gap-3 mt-4">
            @if (keyStatus()?.has_key) {
              <button class="btn-primary" (click)="updateKey()" [disabled]="!apiKey.trim() || saving()">
                {{ saving() ? 'Saving...' : 'Update Key' }}
              </button>
              <button class="btn-danger" (click)="removeKey()" [disabled]="removing()">
                {{ removing() ? 'Removing...' : 'Remove Key' }}
              </button>
            } @else {
              <button class="btn-primary" (click)="saveKey()" [disabled]="!apiKey.trim() || saving()">
                {{ saving() ? 'Saving...' : 'Save Key' }}
              </button>
            }
            <button class="btn-secondary" (click)="testKey()" [disabled]="testing()">
              {{ testing() ? 'Testing...' : 'Test Connection' }}
            </button>
          </div>
        </div>

        <!-- Gemini Test result -->
        @if (testResult()) {
          <div class="card mb-4 animate-fade-in" [class.border-teal-500]="testResult()!.valid" [class.border-red-500]="!testResult()!.valid">
            <div class="flex items-start gap-3">
              @if (testResult()!.valid) {
                <svg class="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              } @else {
                <svg class="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              }
              <div>
                <p class="font-medium" [class.text-teal-300]="testResult()!.valid" [class.text-red-300]="!testResult()!.valid">
                  {{ testResult()!.message }}
                </p>
                @if (testResult()!.detail) {
                  <p class="text-sm text-ink-400 mt-1">{{ testResult()!.detail }}</p>
                }
              </div>
            </div>
          </div>
        }

        <!-- Model selection -->
        <div class="card">
          <h3 class="card-title mb-2">Gemini Model</h3>
          <select id="model" class="input" [(ngModel)]="selectedModel" (ngModelChange)="onModelChange()">
            @for (model of keyStatus()?.available_models ?? []; track model) {
              <option [value]="model">{{ model }}</option>
            }
          </select>
        </div>
      </section>

      <!-- ============================================================== -->
      <!-- SECTION 2: LEAD VERIFICATION MODULE SETTINGS -->
      <!-- ============================================================== -->
      <section>
        <div class="flex items-center gap-2 mb-3">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
          <h2 class="text-lg font-semibold text-white">Lead Verification Provider Settings</h2>
        </div>

        <div class="card mb-4">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="card-title">Verification Engine</h3>
              <p class="text-xs text-ink-400 mt-0.5">
                Choose between built-in local DNS/MX verification (free) or third-party paid providers
              </p>
            </div>
            @if (vSettings()?.has_api_key) {
              <span class="badge-success">Provider Key Configured</span>
            } @else if (vSettings()?.provider === 'technical') {
              <span class="badge-success">Technical (No Key Needed)</span>
            } @else {
              <span class="badge-error">API Key Missing</span>
            }
          </div>

          <div class="space-y-4">
            <div>
              <label class="label">Provider Mode</label>
              <select class="input" [(ngModel)]="vProvider">
                <option value="technical">Technical Verification (Local DNS, MX &amp; Disposable list — Free)</option>
                <option value="hunter">Hunter.io Email Verifier API</option>
                <option value="zerobounce">ZeroBounce Email Validation API</option>
                <option value="generic">Custom HTTP Verification Endpoint / Webhook</option>
              </select>
            </div>

            <!-- Provider Mode Descriptions -->
            <div class="p-3 rounded-lg bg-ink-800/70 border border-ink-700 text-xs text-ink-300">
              @if (vProvider === 'technical') {
                <p><strong class="text-teal-400">Technical Mode:</strong> Validates email format, resolves A/AAAA records, queries DNS MX exchange hosts, and detects 500+ disposable email domains. Since an MX record proves mail host presence but not individual mailbox existence without sending mail, deliverable technical leads are flagged with transparent diagnostic reasons.</p>
              } @else if (vProvider === 'hunter') {
                <p><strong class="text-teal-400">Hunter.io:</strong> Uses Hunter's Email Verifier endpoint to determine mailbox status (deliverable, undeliverable, risky, accept_all). Requires an API key.</p>
              } @else if (vProvider === 'zerobounce') {
                <p><strong class="text-teal-400">ZeroBounce:</strong> Uses ZeroBounce's v2 Validation API to confirm mailbox existence, spam traps, and catch-all servers. Requires an API key.</p>
              } @else {
                <p><strong class="text-teal-400">Custom API:</strong> Forwards email validation requests via HTTP POST to your own custom webhook or verification microservice.</p>
              }
            </div>

            @if (vProvider === 'generic') {
              <div>
                <label class="label">Custom API Endpoint URL</label>
                <input class="input" placeholder="https://api.my-verifier.com/validate" [(ngModel)]="vApiUrl"/>
              </div>
            }

            @if (vProvider !== 'technical') {
              <div>
                <label class="label">{{ vProvider | titlecase }} API Key</label>
                <div class="relative">
                  <input
                    [type]="showVKey() ? 'text' : 'password'"
                    class="input pr-10"
                    placeholder="Enter provider API key..."
                    [(ngModel)]="vApiKey"
                    autocomplete="off"/>
                  <button
                    type="button"
                    class="absolute right-2 top-1/2 -translate-y-1/2 text-ink-400 hover:text-white p-1"
                    (click)="showVKey.set(!showVKey())">
                    @if (showVKey()) {
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                      </svg>
                    } @else {
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                      </svg>
                    }
                  </button>
                </div>
              </div>
            }

            <div class="flex items-center gap-3 pt-2">
              <button class="btn-primary" (click)="saveVerificationSettings()" [disabled]="savingV()">
                {{ savingV() ? 'Saving...' : 'Save Verification Settings' }}
              </button>
              @if (vSettings()?.has_api_key) {
                <button class="btn-danger" (click)="deleteVerificationKey()">
                  Remove Provider Key
                </button>
              }
            </div>
          </div>
        </div>

        <!-- Live Email Verification Sandbox -->
        <div class="card">
          <h3 class="card-title mb-2">Live Email Verification Sandbox</h3>
          <p class="text-xs text-ink-400 mb-4">
            Test any email address against the active verification pipeline in real-time
          </p>

          <div class="flex flex-col sm:flex-row gap-3 mb-4">
            <input
              class="input flex-1"
              placeholder="e.g. contact@stripe.com or user@tempmail.com"
              [(ngModel)]="sandboxEmail"
              (keydown.enter)="runSandboxCheck()"/>
            <button class="btn-primary flex items-center justify-center gap-1.5" (click)="runSandboxCheck()" [disabled]="sandboxChecking() || !sandboxEmail.trim()">
              @if (sandboxChecking()) {
                <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8"/>
                </svg>
                Checking...
              } @else {
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                Verify Email
              }
            </button>
          </div>

          @if (sandboxResult()) {
            <div class="p-4 rounded-lg border bg-ink-900 animate-fade-in"
              [class.border-emerald-500]="sandboxResult()?.status === 'VALID'"
              [class.border-amber-500]="sandboxResult()?.status === 'RISKY'"
              [class.border-red-500]="sandboxResult()?.status === 'INVALID'"
              [class.border-purple-500]="sandboxResult()?.status === 'UNKNOWN'">

              <div class="flex items-center justify-between mb-3">
                <span class="text-xs text-ink-400">Result for: <code class="text-white">{{ sandboxResult()?.email }}</code></span>
                <span
                  class="px-2.5 py-0.5 rounded-full text-xs font-bold"
                  [class.bg-emerald-500-20]="sandboxResult()?.status === 'VALID'"
                  [class.text-emerald-400]="sandboxResult()?.status === 'VALID'"
                  [class.bg-amber-500-20]="sandboxResult()?.status === 'RISKY'"
                  [class.text-amber-400]="sandboxResult()?.status === 'RISKY'"
                  [class.bg-red-500-20]="sandboxResult()?.status === 'INVALID'"
                  [class.text-red-400]="sandboxResult()?.status === 'INVALID'"
                  [class.bg-purple-500-20]="sandboxResult()?.status === 'UNKNOWN'"
                  [class.text-purple-400]="sandboxResult()?.status === 'UNKNOWN'">
                  {{ sandboxResult()?.status }}
                </span>
              </div>

              <p class="text-sm text-ink-200 mb-3 font-medium">
                {{ sandboxResult()?.reason }}
              </p>

              <!-- Diagnostic Grid -->
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div class="bg-ink-800 p-2 rounded">
                  <span class="text-ink-400 block">Syntax Format</span>
                  <span [class.text-emerald-400]="sandboxResult()?.details?.syntax_valid" [class.text-red-400]="!sandboxResult()?.details?.syntax_valid">
                    {{ sandboxResult()?.details?.syntax_valid ? 'Valid (RFC 5322)' : 'Invalid Format' }}
                  </span>
                </div>
                <div class="bg-ink-800 p-2 rounded">
                  <span class="text-ink-400 block">Domain DNS</span>
                  <span [class.text-emerald-400]="sandboxResult()?.details?.domain_exists" [class.text-red-400]="!sandboxResult()?.details?.domain_exists">
                    {{ sandboxResult()?.details?.domain_exists ? 'Host Exists' : 'NXDOMAIN' }}
                  </span>
                </div>
                <div class="bg-ink-800 p-2 rounded">
                  <span class="text-ink-400 block">MX Records</span>
                  <span [class.text-emerald-400]="sandboxResult()?.details?.has_mx" [class.text-red-400]="!sandboxResult()?.details?.has_mx">
                    {{ sandboxResult()?.details?.has_mx ? ((sandboxResult()?.details?.mx_records?.length ?? 0) + ' record(s)') : 'None' }}
                  </span>
                </div>
                <div class="bg-ink-800 p-2 rounded">
                  <span class="text-ink-400 block">Disposable Service</span>
                  <span [class.text-red-400]="sandboxResult()?.details?.is_disposable" [class.text-emerald-400]="!sandboxResult()?.details?.is_disposable">
                    {{ sandboxResult()?.details?.is_disposable ? 'Yes (Temporary)' : 'No (Clean)' }}
                  </span>
                </div>
              </div>

              @if ((sandboxResult()?.details?.mx_records ?? []).length > 0) {
                <div class="mt-2 text-xs text-ink-400">
                  <span>MX Hosts: </span>
                  <code class="text-teal-400">{{ sandboxResult()?.details?.mx_records?.join(', ') }}</code>
                </div>
              }
            </div>
          }
        </div>
      </section>
    </div>
  `,
})
export class ApiSettings implements OnInit {
  private settingsService = inject(SettingsService);
  private verificationService = inject(VerificationService);

  // Gemini state
  apiKey = '';
  showKey = signal(false);
  saving = signal(false);
  removing = signal(false);
  testing = signal(false);
  keyStatus = signal<ApiKeyStatus | null>(null);
  testResult = signal<ApiKeyTestResult | null>(null);
  selectedModel = 'gemini-3.5-flash';

  // Verification state
  vSettings = signal<VerificationSettings | null>(null);
  vProvider = 'technical';
  vApiKey = '';
  vApiUrl = '';
  showVKey = signal(false);
  savingV = signal(false);

  // Sandbox state
  sandboxEmail = '';
  sandboxChecking = signal(false);
  sandboxResult = signal<SingleVerificationResponse | null>(null);

  ngOnInit() {
    this.loadKeyStatus();
    this.loadVerificationSettings();
  }

  loadKeyStatus() {
    this.settingsService.getKeyStatus().subscribe({
      next: (res) => {
        this.keyStatus.set(res);
        this.selectedModel = res.model;
      },
      error: (err) => console.error('Failed to load key status', err),
    });
  }

  loadVerificationSettings() {
    this.verificationService.getSettings().subscribe({
      next: (res) => {
        this.vSettings.set(res);
        this.vProvider = res.provider;
        this.vApiUrl = res.api_url || '';
      },
      error: (err) => console.error('Failed to load verification settings', err),
    });
  }

  saveKey() {
    if (!this.apiKey.trim()) return;
    this.saving.set(true);
    this.settingsService.saveKey(this.apiKey.trim()).subscribe({
      next: () => {
        this.saving.set(false);
        this.apiKey = '';
        this.loadKeyStatus();
      },
      error: (err) => {
        this.saving.set(false);
        console.error('Save failed', err);
      },
    });
  }

  updateKey() {
    if (!this.apiKey.trim()) return;
    this.saving.set(true);
    this.settingsService.updateKey(this.apiKey.trim()).subscribe({
      next: () => {
        this.saving.set(false);
        this.apiKey = '';
        this.loadKeyStatus();
      },
      error: (err) => {
        this.saving.set(false);
        console.error('Update failed', err);
      },
    });
  }

  removeKey() {
    if (!confirm('Remove the stored API key? You will need to re-enter it to use lead generation.')) return;
    this.removing.set(true);
    this.settingsService.removeKey().subscribe({
      next: () => {
        this.removing.set(false);
        this.testResult.set(null);
        this.loadKeyStatus();
      },
      error: (err) => {
        this.removing.set(false);
        console.error('Remove failed', err);
      },
    });
  }

  testKey() {
    this.testing.set(true);
    this.testResult.set(null);
    const key = this.apiKey.trim() || undefined;
    this.settingsService.testKey(key).subscribe({
      next: (res) => {
        this.testing.set(false);
        this.testResult.set(res);
      },
      error: (err) => {
        this.testing.set(false);
        this.testResult.set({
          valid: false,
          model: this.selectedModel,
          message: 'Connection test failed',
          detail: err.error?.detail || err.message || 'Unknown error',
        });
      },
    });
  }

  onModelChange() {
    this.settingsService.setModel(this.selectedModel).subscribe({
      error: (err) => console.error('Model change failed', err),
    });
  }

  saveVerificationSettings() {
    this.savingV.set(true);
    this.verificationService
      .updateSettings({
        provider: this.vProvider,
        api_key: this.vApiKey.trim() || undefined,
        api_url: this.vApiUrl.trim() || undefined,
      })
      .subscribe({
        next: () => {
          this.savingV.set(false);
          this.vApiKey = '';
          this.loadVerificationSettings();
          alert('Verification settings saved successfully!');
        },
        error: (err) => {
          this.savingV.set(false);
          alert(`Failed to save settings: ${err.error?.detail || err.message}`);
        },
      });
  }

  deleteVerificationKey() {
    if (!confirm('Remove the stored verification provider API key?')) return;
    this.verificationService.deleteApiKey().subscribe({
      next: () => {
        this.loadVerificationSettings();
        alert('Verification API key removed.');
      },
      error: (err) => console.error('Failed to remove key', err),
    });
  }

  runSandboxCheck() {
    if (!this.sandboxEmail.trim()) return;
    this.sandboxChecking.set(true);
    this.sandboxResult.set(null);

    this.verificationService.verifyEmail(this.sandboxEmail.trim()).subscribe({
      next: (res) => {
        this.sandboxChecking.set(false);
        this.sandboxResult.set(res);
      },
      error: (err) => {
        this.sandboxChecking.set(false);
        alert(`Verification sandbox error: ${err.error?.detail || err.message}`);
      },
    });
  }
}
