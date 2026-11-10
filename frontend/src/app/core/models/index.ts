/**
 * TypeScript interfaces matching the backend Pydantic schemas.
 */

export interface Lead {
  lead_id: string;
  company_name: string;
  owner_name: string;
  website: string;
  email: string;
  phone: string;
  city: string;
  country: string;
  business_type: string;
  description: string;
  source_url: string;
  search_query: string;
  generated_at: string;
  verification_status?: string; // VALID, INVALID, RISKY, UNKNOWN, or empty
  verification_reason?: string;
  verification_details?: string;
  verified_at?: string;
}

export interface VerificationStats {
  total: number;
  verified: number;
  unverified: number;
  valid: number;
  invalid: number;
  risky: number;
  unknown: number;
}

export interface VerificationCheckDetails {
  syntax_valid: boolean;
  domain_exists: boolean;
  has_mx: boolean;
  mx_records: string[];
  is_disposable: boolean;
  is_catch_all: boolean | null;
  mailbox_confirmed: boolean | null;
  provider: string;
  checked_at: string;
}

export interface SingleVerificationResponse {
  lead_id: string;
  email: string;
  status: 'VALID' | 'INVALID' | 'RISKY' | 'UNKNOWN';
  reason: string;
  details: VerificationCheckDetails;
  verified_at: string;
}

export interface BatchVerificationStatus {
  job_id: string;
  total_leads: number;
  processed_leads: number;
  valid_count: number;
  invalid_count: number;
  risky_count: number;
  unknown_count: number;
  progress: number;
  is_running: boolean;
  is_completed: boolean;
  is_cancelled: boolean;
  error: string;
  message: string;
}

export interface VerificationSettings {
  provider: string;
  available_providers: string[];
  has_api_key: boolean;
  api_url: string;
}

export interface LeadListResponse {
  leads: Lead[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DashboardStats {
  total_leads: number;
  leads_today: number;
  total_searches: number;
  successful_searches: number;
  failed_searches: number;
  recent_leads: Lead[];
  verification_stats?: VerificationStats;
}

export interface SearchConfig {
  business_type: string;
  location: string;
  limit: number;
  fields: string[];
  raw_prompt: string;
}

export interface GenerationStatus {
  job_id: string;
  stage: string;
  message: string;
  total_websites: number;
  websites_discovered: number;
  websites_processed: number;
  leads_extracted: number;
  duplicates_skipped: number;
  failed_websites: number;
  failed_urls: string[];
  progress: number;
  is_running: boolean;
  is_completed: boolean;
  is_cancelled: boolean;
  error: string;
  search_config: SearchConfig | null;
  new_lead_ids: string[];
}

export interface GenerationStartResponse {
  job_id: string;
  status: string;
}

export interface ApiKeyStatus {
  has_key: boolean;
  model: string;
  available_models: string[];
}

export interface ApiKeyTestResult {
  valid: boolean;
  model: string;
  message: string;
  detail: string;
}

export interface AvailableModels {
  models: string[];
  selected: string;
  default: string;
}

export interface ActivityLogEntry {
  timestamp: string;
  level: string;
  message: string;
}

export interface ActivityLogResponse {
  entries: ActivityLogEntry[];
  total: number;
}

export interface MessageResponse {
  message: string;
  detail: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
}
