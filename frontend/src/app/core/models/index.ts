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
